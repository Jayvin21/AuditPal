from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher


def _norm(value):
    if value is None:
        return ""
    return str(value).strip()


def _lower(value):
    return _norm(value).lower()


def _clean_doc(value):
    return (
        _norm(value)
        .replace(" ", "")
        .replace("-", "")
        .replace("/", "")
        .replace("\\", "")
        .lower()
    )


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


def _raw(record, *keys):
    raw = getattr(record, "raw_data", None) or {}
    source_values = raw.get("source_row_values", {}) if isinstance(raw, dict) else {}

    lowered = {}

    for data in [raw, source_values]:
        if isinstance(data, dict):
            lowered.update({str(k).strip().lower(): v for k, v in data.items()})

    for key in keys:
        if isinstance(raw, dict) and key in raw and raw[key] not in [None, ""]:
            return raw[key]

        if isinstance(source_values, dict) and key in source_values and source_values[key] not in [None, ""]:
            return source_values[key]

        lowered_key = key.strip().lower()
        if lowered_key in lowered and lowered[lowered_key] not in [None, ""]:
            return lowered[lowered_key]

    return None


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "party_name", "Trade/Legal name", "Legal Name", "Vendor Name", "Supplier Name", "Party Name")
        or ""
    )


def _gstin(record):
    return (
        getattr(record, "gstin", None)
        or _raw(record, "supplier_gstin", "gstin", "GSTIN of supplier", "Supplier GSTIN", "Vendor GSTIN", "Party GSTIN", "GSTIN/UIN")
        or ""
    )


def _taxable_value(record):
    return _amount(
        _raw(
            record,
            "taxable_value",
            "Taxable Value",
            "Taxable Amount",
            "Assessable Value",
            "Tax Base",
        )
    )


def _invoice_value(record):
    return _amount(
        _raw(
            record,
            "invoice_value",
            "Invoice Value",
            "Gross Total",
            "Gross Amount",
            "Invoice Amount",
            "Bill Amount",
            "Total Invoice Value",
        )
    )


def _tax_amount(record):
    igst = _amount(_raw(record, "igst", "IGST", "IGST Amount", "Integrated Tax"))
    cgst = _amount(_raw(record, "cgst", "CGST", "CGST Amount", "Central Tax"))
    sgst = _amount(_raw(record, "sgst", "SGST", "SGST Amount", "State Tax"))

    total = 0
    found = False

    for value in [igst, cgst, sgst]:
        if value is not None:
            total += value
            found = True

    return total if found else None


def _amount_for_match(record):
    taxable = _taxable_value(record)
    if taxable is not None:
        return taxable

    invoice = _invoice_value(record)
    if invoice is not None:
        return invoice

    return _amount(getattr(record, "amount", None))


def _description(record):
    return (
        _raw(record, "description", "supply_type", "Supply Type", "Description", "Narration", "Particulars")
        or getattr(record, "description", None)
        or ""
    )


def _similarity(a, b):
    a = _lower(a)
    b = _lower(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def _money(value):
    amount = _amount(value)
    if amount is None:
        return ""
    return f"₹{amount:,.0f}"


def _title(base, record):
    bits = []

    doc = _norm(getattr(record, "document_id", None))
    party = _norm(_party(record))
    amount = _money(_amount_for_match(record))

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if amount:
        bits.append(amount)

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _record_display(record):
    return {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": _party(record),
        "gstin": _gstin(record),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "taxable_value": _taxable_value(record),
        "invoice_value": _invoice_value(record),
        "tax_amount": _tax_amount(record),
        "description": _description(record),
        "record_type": getattr(record, "record_type", None),
    }


def _finding(record, finding_type, risk_level, title, description, matched_record=None, extra=None):
    evidence = _record_display(record)

    if matched_record is not None:
        evidence["matched_record"] = _record_display(matched_record)

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(record, "id", None),
        "matched_record_id": getattr(matched_record, "id", None) if matched_record is not None else None,
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _title(title, record),
        "description": description,
        "evidence": evidence,
    }


def _index_by_document(records):
    index = defaultdict(list)

    for record in records:
        doc = _clean_doc(getattr(record, "document_id", None))
        if doc:
            index[doc].append(record)

    return index


def run_gst_reconciliation_checks(book_records, gstr_2b_records, amount_tolerance=10.0):
    findings = []

    books_by_doc = _index_by_document(book_records)
    gstr_by_doc = _index_by_document(gstr_2b_records)

    for record in book_records:
        doc = _clean_doc(getattr(record, "document_id", None))
        gstin = _gstin(record)
        amount = _amount_for_match(record)

        if not doc:
            findings.append(_finding(
                record,
                "books_missing_invoice_number_for_gst",
                "high",
                "Books entry missing invoice number",
                "Books purchase/ITC entry has no invoice number, so it cannot be matched reliably with GSTR-2B.",
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "books_missing_supplier_gstin",
                "high",
                "Books entry missing supplier GSTIN",
                "Books purchase/ITC entry has no supplier GSTIN. This weakens GST reconciliation and ITC validation.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "books_missing_taxable_or_invoice_value",
                "medium",
                "Books entry missing GST amount base",
                "Books entry has no usable taxable value, invoice value, or amount for GST reconciliation.",
            ))

    for record in gstr_2b_records:
        doc = _clean_doc(getattr(record, "document_id", None))
        gstin = _gstin(record)
        amount = _amount_for_match(record)

        if not doc:
            findings.append(_finding(
                record,
                "gstr_2b_missing_invoice_number",
                "medium",
                "GSTR-2B entry missing invoice number",
                "GSTR-2B entry has no invoice number, so it cannot be matched reliably with books.",
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "gstr_2b_missing_supplier_gstin",
                "medium",
                "GSTR-2B entry missing supplier GSTIN",
                "GSTR-2B entry has no supplier GSTIN.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "gstr_2b_missing_taxable_or_invoice_value",
                "medium",
                "GSTR-2B entry missing GST amount base",
                "GSTR-2B entry has no usable taxable value, invoice value, or amount.",
            ))

    for doc, group in books_by_doc.items():
        if len(group) > 1:
            first = group[0]
            findings.append(_finding(
                first,
                "duplicate_itc_invoice_in_books",
                "high",
                "Duplicate ITC invoice in books",
                "Same invoice/reference appears multiple times in books purchase/ITC data. Review duplicate ITC claim risk.",
                extra={
                    "document_key": doc,
                    "duplicate_count": len(group),
                    "book_records": [_record_display(record) for record in group],
                },
            ))

    for doc, group in gstr_by_doc.items():
        if len(group) > 1:
            first = group[0]
            findings.append(_finding(
                first,
                "duplicate_invoice_in_gstr_2b",
                "medium",
                "Duplicate invoice in GSTR-2B",
                "Same invoice/reference appears multiple times in GSTR-2B data. Verify supplier filing and duplicate rows.",
                extra={
                    "document_key": doc,
                    "duplicate_count": len(group),
                    "gstr_2b_records": [_record_display(record) for record in group],
                },
            ))

    for doc, book_group in books_by_doc.items():
        if doc not in gstr_by_doc:
            for book_record in book_group:
                findings.append(_finding(
                    book_record,
                    "itc_in_books_not_found_in_gstr_2b",
                    "high",
                    "ITC in books not found in GSTR-2B",
                    "Books purchase/ITC entry exists, but matching invoice was not found in GSTR-2B.",
                    extra={"document_key": doc},
                ))
            continue

        gstr_group = gstr_by_doc[doc]

        for book_record in book_group:
            book_amount = _amount_for_match(book_record)
            book_gstin = _gstin(book_record)
            book_party = _party(book_record)

            closest = None
            closest_diff = None

            for gstr_record in gstr_group:
                gstr_amount = _amount_for_match(gstr_record)

                if book_amount is None or gstr_amount is None:
                    continue

                diff = abs(abs(book_amount) - abs(gstr_amount))

                if closest is None or diff < closest_diff:
                    closest = gstr_record
                    closest_diff = diff

            if closest is None:
                continue

            gstr_amount = _amount_for_match(closest)
            gstr_gstin = _gstin(closest)
            gstr_party = _party(closest)

            if closest_diff is not None and closest_diff > amount_tolerance:
                findings.append(_finding(
                    book_record,
                    "books_vs_gstr_2b_amount_mismatch",
                    "high",
                    "Books amount does not match GSTR-2B",
                    "Invoice exists in both books and GSTR-2B, but taxable/invoice value differs beyond tolerance.",
                    matched_record=closest,
                    extra={
                        "document_key": doc,
                        "books_amount": book_amount,
                        "gstr_2b_amount": gstr_amount,
                        "difference": round(closest_diff, 2),
                    },
                ))

            if book_gstin and gstr_gstin and book_gstin.upper() != gstr_gstin.upper():
                findings.append(_finding(
                    book_record,
                    "books_vs_gstr_2b_gstin_mismatch",
                    "high",
                    "Supplier GSTIN mismatch",
                    "Invoice exists in both books and GSTR-2B, but supplier GSTIN differs.",
                    matched_record=closest,
                    extra={
                        "document_key": doc,
                        "books_gstin": book_gstin,
                        "gstr_2b_gstin": gstr_gstin,
                    },
                ))

            party_score = _similarity(book_party, gstr_party)

            if book_party and gstr_party and party_score < 0.55:
                findings.append(_finding(
                    book_record,
                    "books_vs_gstr_2b_supplier_name_mismatch",
                    "medium",
                    "Supplier name mismatch",
                    "Invoice exists in both books and GSTR-2B, but supplier name appears different.",
                    matched_record=closest,
                    extra={
                        "document_key": doc,
                        "books_party": book_party,
                        "gstr_2b_party": gstr_party,
                        "similarity": round(party_score, 2),
                    },
                ))

    for doc, gstr_group in gstr_by_doc.items():
        if doc not in books_by_doc:
            for gstr_record in gstr_group:
                findings.append(_finding(
                    gstr_record,
                    "gstr_2b_invoice_not_found_in_books",
                    "medium",
                    "GSTR-2B invoice not found in books",
                    "Invoice exists in GSTR-2B, but no matching books purchase/ITC entry was found.",
                    extra={"document_key": doc},
                ))

    return findings
