from pathlib import Path

ROOT = Path(r"D:\1Workspace\AuditPal")
CHECKS = ROOT / "backend" / "app" / "services" / "audit_engine" / "checks"

GST = CHECKS / "gst_reco_checks.py"
DOCUMENT = CHECKS / "document_match_checks.py"

# ----------------------------------------------------
# 1. GST Reconciliation: canonical mapped field reliability
# ----------------------------------------------------

GST.write_text(
r'''from collections import defaultdict
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
''',
encoding="utf-8",
)

# ----------------------------------------------------
# 2. Document Matching: canonical OCR/support fields
# ----------------------------------------------------

DOCUMENT.write_text(
r'''from collections import defaultdict
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
        or _raw(record, "party_name", "Vendor Name", "Supplier Name", "Party Name", "Customer Name", "Name")
        or ""
    )


def _description(record):
    return (
        _raw(record, "extracted_text", "description", "OCR Text", "Extracted Text", "Text", "Description", "Narration", "Particulars")
        or getattr(record, "description", None)
        or ""
    )


def _confidence(record):
    value = _raw(record, "ocr_confidence", "OCR Confidence", "Confidence", "confidence_score", "Extraction Confidence")

    parsed = _amount(value)

    if parsed is None:
        parsed = getattr(record, "confidence", None)

    try:
        if parsed is None:
            return None

        parsed = float(parsed)

        if parsed > 1:
            parsed = parsed / 100

        return parsed
    except Exception:
        return None


def _document_type(record):
    return _raw(record, "document_type", "Document Type", "Doc Type", "Invoice Type", "Bill Type") or ""


def _support_file_name(record):
    return _raw(record, "support_file_name", "Support File Name", "File Name", "Filename", "Source File") or ""


def _display(record):
    return {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": _party(record),
        "transaction_date": str(getattr(record, "transaction_date", "") or ""),
        "amount": getattr(record, "amount", None),
        "confidence": _confidence(record),
        "document_type": _document_type(record),
        "support_file_name": _support_file_name(record),
        "description": _description(record),
        "record_type": getattr(record, "record_type", None),
    }


def _similarity(a, b):
    a = _lower(a)
    b = _lower(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def _title(base, record):
    bits = []

    doc = _norm(getattr(record, "document_id", None))
    party = _norm(_party(record))
    amount = _amount(getattr(record, "amount", None))

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if amount is not None:
        bits.append(f"₹{amount:,.0f}")

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


def run_document_match_checks(book_records, support_records, amount_tolerance=10.0):
    findings = []

    books_by_doc = defaultdict(list)
    support_by_doc = defaultdict(list)

    for record in book_records:
        doc = _clean_doc(getattr(record, "document_id", None))

        if doc:
            books_by_doc[doc].append(record)

    for record in support_records:
        doc = _clean_doc(getattr(record, "document_id", None))
        confidence = _confidence(record)
        amount = _amount(getattr(record, "amount", None))
        extracted_text = _description(record)

        if not doc:
            findings.append(_finding(
                record,
                "support_document_missing_number",
                "high",
                "Support document missing invoice/reference number",
                "Extracted/OCR support document does not have a usable invoice, bill, voucher, or reference number.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "support_document_missing_amount",
                "high",
                "Support document missing amount",
                "Extracted/OCR support document does not contain a usable amount.",
            ))

        if confidence is not None and confidence < 0.75:
            findings.append(_finding(
                record,
                "low_ocr_confidence_support_document",
                "medium",
                "Low OCR confidence support document",
                "Supporting document extraction confidence is low. Manual verification is recommended.",
                {"ocr_confidence": confidence},
            ))

        if not extracted_text:
            findings.append(_finding(
                record,
                "support_document_missing_extracted_text",
                "low",
                "Support document missing extracted text",
                "Support/OCR record has no extracted text field. Manual traceability is weaker.",
            ))

        if doc:
            support_by_doc[doc].append(record)

    for doc, support_group in support_by_doc.items():
        if len(support_group) > 1:
            first = support_group[0]
            findings.append(_finding(
                first,
                "duplicate_support_document",
                "medium",
                "Duplicate support document extracted",
                "Same support document number appears more than once in extracted/OCR support data.",
                {
                    "document_key": doc,
                    "duplicate_count": len(support_group),
                    "support_records": [_display(record) for record in support_group],
                },
            ))

    for doc, book_group in books_by_doc.items():
        if doc not in support_by_doc:
            for book_record in book_group:
                findings.append(_finding(
                    book_record,
                    "books_entry_missing_support_document",
                    "high",
                    "Books entry missing support document",
                    "Books entry exists but no matching extracted/OCR support document was found by invoice/reference number.",
                    {"document_key": doc},
                ))
            continue

        support_group = support_by_doc[doc]

        for book_record in book_group:
            book_amount = _amount(getattr(book_record, "amount", None))
            book_party = _party(book_record)

            closest_support = None
            closest_diff = None

            for support_record in support_group:
                support_amount = _amount(getattr(support_record, "amount", None))

                if book_amount is None or support_amount is None:
                    continue

                diff = abs(abs(book_amount) - abs(support_amount))

                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_support = support_record

            if closest_support is not None and closest_diff is not None:
                if closest_diff > amount_tolerance:
                    findings.append(_finding(
                        book_record,
                        "books_vs_support_amount_mismatch",
                        "high",
                        "Books amount does not match support document",
                        "Invoice/reference exists in both books and support document extract, but amount differs beyond tolerance.",
                        {
                            "document_key": doc,
                            "books_amount": book_amount,
                            "support_amount": _amount(getattr(closest_support, "amount", None)),
                            "difference": round(closest_diff, 2),
                            "support_record": _display(closest_support),
                        },
                    ))

                support_party = _party(closest_support)
                party_score = _similarity(book_party, support_party)

                if book_party and support_party and party_score < 0.55:
                    findings.append(_finding(
                        book_record,
                        "books_vs_support_party_mismatch",
                        "medium",
                        "Books party does not match support document",
                        "Invoice/reference exists in both books and support document extract, but vendor/party name appears different.",
                        {
                            "document_key": doc,
                            "books_party": book_party,
                            "support_party": support_party,
                            "similarity": round(party_score, 2),
                            "support_record": _display(closest_support),
                        },
                    ))

    for doc, support_group in support_by_doc.items():
        if doc not in books_by_doc:
            for support_record in support_group:
                findings.append(_finding(
                    support_record,
                    "support_document_not_booked",
                    "medium",
                    "Support document not found in books",
                    "Extracted/OCR support document exists but no matching books entry was found by invoice/reference number.",
                    {"document_key": doc},
                ))

    return findings
''',
encoding="utf-8",
)

print("Pass 2 Task 3 applied.")
print("Updated:")
print(f"- {GST}")
print(f"- {DOCUMENT}")