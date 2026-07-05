from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def _norm(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_id(value):
    return _norm(value).replace(" ", "").replace("-", "").replace("/", "").lower()


def _clean_gstin(value):
    return _norm(value).upper().replace(" ", "")


def _amount(value):
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return float(value)
        cleaned = str(value).replace(",", "").replace("₹", "").strip()
        if cleaned == "":
            return None
        return float(cleaned)
    except (ValueError, InvalidOperation):
        return None


def _date_string(value):
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _key(record):
    doc = _clean_id(getattr(record, "document_id", None))
    gstin = _clean_gstin(getattr(record, "gstin", None))
    return (doc, gstin)


def _display(record):
    return {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "gstin": getattr(record, "gstin", None),
        "record_type": getattr(record, "record_type", None),
    }


def _title(base, record):
    bits = []
    doc = _norm(getattr(record, "document_id", None))
    party = _norm(getattr(record, "party_name", None))
    gstin = _norm(getattr(record, "gstin", None))

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if gstin:
        bits.append(gstin)

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = _display(record)
    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(record, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _title(title, record),
        "description": description,
        "evidence": evidence,
    }


def _group_finding(records, finding_type, risk_level, title, description, extra=None):
    first = records[0]
    evidence = {
        "duplicate_count": len(records),
        "records": [_display(record) for record in records],
        "document_id": getattr(first, "document_id", None),
        "party_name": getattr(first, "party_name", None),
        "gstin": getattr(first, "gstin", None),
        "source_rows": [getattr(record, "source_row", None) for record in records],
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(first, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _title(title, first),
        "description": description,
        "evidence": evidence,
    }


def run_gst_reconciliation_checks(book_records, gstr_2b_records, amount_tolerance=5.0):
    findings = []

    book_index = defaultdict(list)
    portal_index = defaultdict(list)

    for record in book_records:
        document_id = _norm(getattr(record, "document_id", None))
        gstin = _norm(getattr(record, "gstin", None))
        amount = _amount(getattr(record, "amount", None))

        if not document_id:
            findings.append(_finding(
                record,
                "books_missing_invoice_number",
                "high",
                "Books invoice missing invoice number",
                "Books purchase/ITC entry does not have a usable invoice number, so it cannot be reliably matched with GSTR-2B.",
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "books_missing_supplier_gstin",
                "high",
                "Books invoice missing supplier GSTIN",
                "Books purchase/ITC entry does not have supplier GSTIN, so GST reconciliation is weak.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "books_missing_taxable_or_invoice_amount",
                "medium",
                "Books invoice missing amount",
                "Books purchase/ITC entry does not have a usable amount for GST reconciliation.",
            ))

        key = _key(record)
        if key != ("", ""):
            book_index[key].append(record)

    for record in gstr_2b_records:
        document_id = _norm(getattr(record, "document_id", None))
        gstin = _norm(getattr(record, "gstin", None))
        amount = _amount(getattr(record, "amount", None))

        if not document_id:
            findings.append(_finding(
                record,
                "gstr_2b_missing_invoice_number",
                "medium",
                "GSTR-2B row missing invoice number",
                "GSTR-2B row does not have a usable invoice number.",
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "gstr_2b_missing_supplier_gstin",
                "medium",
                "GSTR-2B row missing supplier GSTIN",
                "GSTR-2B row does not have a usable supplier GSTIN.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "gstr_2b_missing_taxable_or_invoice_amount",
                "medium",
                "GSTR-2B row missing amount",
                "GSTR-2B row does not have a usable taxable/invoice amount.",
            ))

        key = _key(record)
        if key != ("", ""):
            portal_index[key].append(record)

    for key, records in book_index.items():
        if len(records) > 1:
            findings.append(_group_finding(
                records,
                "duplicate_invoice_in_books",
                "high",
                "Duplicate GST invoice in books",
                "Same invoice number and supplier GSTIN appears multiple times in books. Check duplicate ITC booking.",
                {"match_key": key},
            ))

    for key, records in portal_index.items():
        if len(records) > 1:
            findings.append(_group_finding(
                records,
                "duplicate_invoice_in_gstr_2b",
                "medium",
                "Duplicate GST invoice in GSTR-2B",
                "Same invoice number and supplier GSTIN appears multiple times in GSTR-2B export.",
                {"match_key": key},
            ))

    for key, books in book_index.items():
        if key not in portal_index:
            for record in books:
                findings.append(_finding(
                    record,
                    "itc_in_books_not_in_gstr_2b",
                    "high",
                    "ITC in books not found in GSTR-2B",
                    "Purchase/ITC entry exists in books but matching supplier GSTIN and invoice number was not found in GSTR-2B.",
                    {"match_key": key},
                ))
            continue

        portal_records = portal_index[key]

        for book_record in books:
            book_amount = _amount(getattr(book_record, "amount", None))
            if book_amount is None:
                continue

            closest_portal = None
            closest_diff = None

            for portal_record in portal_records:
                portal_amount = _amount(getattr(portal_record, "amount", None))
                if portal_amount is None:
                    continue

                diff = abs(abs(book_amount) - abs(portal_amount))

                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_portal = portal_record

            if closest_portal is not None and closest_diff is not None and closest_diff > amount_tolerance:
                findings.append(_finding(
                    book_record,
                    "gst_amount_mismatch_books_vs_2b",
                    "medium",
                    "GST reconciliation amount mismatch",
                    "Invoice exists in both books and GSTR-2B, but amount differs beyond tolerance.",
                    {
                        "match_key": key,
                        "books_amount": book_amount,
                        "gstr_2b_amount": _amount(getattr(closest_portal, "amount", None)),
                        "difference": round(closest_diff, 2),
                        "gstr_2b_record": _display(closest_portal),
                    },
                ))

    for key, portal_records in portal_index.items():
        if key not in book_index:
            for record in portal_records:
                findings.append(_finding(
                    record,
                    "gstr_2b_invoice_not_booked",
                    "medium",
                    "GSTR-2B invoice not found in books",
                    "Invoice exists in GSTR-2B but matching books entry was not found. Check if purchase/ITC was missed or intentionally not booked.",
                    {"match_key": key},
                ))

    return findings
