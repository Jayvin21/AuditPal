from collections import defaultdict
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
    lowered = {str(k).strip().lower(): v for k, v in raw.items()}

    for key in keys:
        if key in raw and raw[key] not in [None, ""]:
            return raw[key]

        lowered_key = key.strip().lower()
        if lowered_key in lowered and lowered[lowered_key] not in [None, ""]:
            return lowered[lowered_key]

    return None


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Vendor Name", "Supplier Name", "Party Name", "Customer Name", "Name")
        or ""
    )


def _description(record):
    return (
        _raw(record, "Description", "Narration", "Particulars", "OCR Text", "Extracted Text", "Text")
        or getattr(record, "description", None)
        or ""
    )


def _confidence(record):
    value = _raw(record, "OCR Confidence", "Confidence", "confidence_score", "Extraction Confidence")
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


def _display(record):
    return {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": _party(record),
        "transaction_date": str(getattr(record, "transaction_date", "") or ""),
        "amount": getattr(record, "amount", None),
        "confidence": _confidence(record),
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
