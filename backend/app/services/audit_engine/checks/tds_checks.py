from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


TDS_SENSITIVE_KEYWORDS = {
    "professional": ["professional", "consultancy", "consultant", "technical fees", "legal fees", "audit fees", "ca fees"],
    "contractor": ["contractor", "contract", "labour", "job work", "works contract"],
    "rent": ["rent", "lease", "premises"],
    "commission": ["commission", "brokerage"],
    "interest": ["interest"],
    "royalty": ["royalty"],
}


def _norm(value):
    if value is None:
        return ""
    return str(value).strip()


def _lower(value):
    return _norm(value).lower()


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


def _is_year_end(value):
    text = _date_string(value)
    return any(marker in text for marker in ["03-31", "31-03", "31/03", "2025-03-31", "2026-03-31"])


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


def _description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text", "Nature")
        or getattr(record, "description", None)
        or ""
    )


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Party Name", "Vendor Name", "Supplier Name", "Name 1", "Particulars")
        or ""
    )


def _pan(record):
    return _raw(record, "PAN", "Vendor PAN", "Supplier PAN", "Permanent Account Number", "PAN No", "PAN Number") or ""


def _tds_amount(record):
    return _amount(
        _raw(
            record,
            "TDS Deducted",
            "TDS Amount",
            "Tax Deducted",
            "TDS",
            "Withholding Tax",
            "WHT Amount",
            "TDS Payable",
        )
    )


def _tds_section(record):
    return _raw(record, "TDS Section", "Section", "TDS Nature", "194C/194J", "Withholding Tax Code", "WHT Code") or ""


def _nature(record):
    return (
        _raw(record, "Nature", "Expense Nature", "Payment Nature", "Ledger Name", "G/L Account", "GL Account")
        or _description(record)
        or _party(record)
    )


def _tds_category(text):
    text = text.lower()
    for category, keywords in TDS_SENSITIVE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return ""


def _money(value):
    amount = _amount(value)
    if amount is None:
        return ""
    return f"₹{amount:,.0f}"


def _title(base, record):
    bits = []

    doc = _norm(getattr(record, "document_id", None))
    party = _norm(_party(record))
    amount = _money(getattr(record, "amount", None))

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if amount:
        bits.append(amount)

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": _party(record),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "pan": _pan(record),
        "tds_amount": _tds_amount(record),
        "tds_section": _tds_section(record),
        "nature": _nature(record),
        "description": _description(record),
        "record_type": getattr(record, "record_type", None),
    }

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


def run_tds_checks(records):
    findings = []
    voucher_index = defaultdict(list)
    party_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party = _party(record)
        amount = _amount(getattr(record, "amount", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)
        description = _description(record)
        nature = _nature(record)
        combined_text = " ".join([_lower(party), _lower(description), _lower(nature)])

        pan = _norm(_pan(record)).upper()
        tds_amount = _tds_amount(record)
        tds_section = _norm(_tds_section(record))
        category = _tds_category(combined_text)

        if document_id:
            voucher_index[document_id.lower()].append(record)

        if party and amount is not None and txn_date_text:
            party_amount_date_index[(party.lower(), round(abs(amount), 2), txn_date_text)].append(record)

        if amount is None:
            findings.append(_finding(
                record,
                "tds_review_missing_payment_amount",
                "medium",
                "Missing payment amount for TDS review",
                "Entry does not contain a usable payment/expense amount, so TDS applicability cannot be assessed reliably.",
            ))
            continue

        if category:
            if amount >= 30000 and (tds_amount is None or tds_amount <= 0):
                findings.append(_finding(
                    record,
                    "possible_tds_not_deducted",
                    "high",
                    "Possible TDS not deducted",
                    "Payment appears TDS-sensitive and exceeds review threshold, but no TDS deducted amount is visible.",
                    {
                        "tds_category": category,
                        "amount": amount,
                        "tds_amount": tds_amount,
                    },
                ))

            if not pan:
                findings.append(_finding(
                    record,
                    "missing_vendor_pan_for_tds",
                    "high",
                    "Missing vendor PAN for TDS-sensitive payment",
                    "Payment appears TDS-sensitive but vendor PAN is missing. This affects TDS compliance and reporting.",
                    {
                        "tds_category": category,
                        "amount": amount,
                    },
                ))

            if tds_amount is not None and tds_amount > 0 and not tds_section:
                findings.append(_finding(
                    record,
                    "tds_deducted_section_missing",
                    "medium",
                    "TDS deducted but section/code missing",
                    "TDS amount is present but TDS section or withholding tax code is missing.",
                    {
                        "tds_amount": tds_amount,
                    },
                ))

            if amount >= 100000:
                findings.append(_finding(
                    record,
                    "high_value_tds_sensitive_payment",
                    "medium",
                    "High-value TDS-sensitive payment",
                    "High-value payment appears to fall under a TDS-sensitive category. Verify PAN, section, rate, deduction, and challan trail.",
                    {
                        "tds_category": category,
                        "amount": amount,
                    },
                ))

            if amount >= 1000 and amount % 1000 == 0:
                findings.append(_finding(
                    record,
                    "round_number_tds_sensitive_payment",
                    "low",
                    "Round-number TDS-sensitive payment",
                    "TDS-sensitive payment has a round amount. This can be normal but should be reviewed for estimate/manual booking.",
                    {
                        "tds_category": category,
                        "amount": amount,
                    },
                ))

            if _is_year_end(txn_date):
                findings.append(_finding(
                    record,
                    "year_end_tds_sensitive_payment",
                    "medium",
                    "Year-end TDS-sensitive payment",
                    "TDS-sensitive payment was booked near financial year end. Verify deduction timing, provision, and payment compliance.",
                    {
                        "tds_category": category,
                        "transaction_date": txn_date_text,
                    },
                ))

        elif tds_amount is not None and tds_amount > 0:
            findings.append(_finding(
                record,
                "tds_deducted_on_uncategorized_payment",
                "low",
                "TDS deducted on uncategorized payment",
                "TDS amount is present, but payment nature was not clearly classified by the rule engine.",
                {
                    "tds_amount": tds_amount,
                    "nature": nature,
                },
            ))

    for voucher, duplicate_records in voucher_index.items():
        if len(duplicate_records) > 1:
            first = duplicate_records[0]
            findings.append(_finding(
                first,
                "duplicate_tds_payment_voucher",
                "medium",
                "Duplicate TDS/payment voucher reference",
                "Same voucher/reference appears more than once in TDS-review data. Review whether this is valid multi-line accounting or duplicate booking.",
                {
                    "voucher": voucher,
                    "duplicate_count": len(duplicate_records),
                    "source_rows": [getattr(record, "source_row", None) for record in duplicate_records],
                    "record_ids": [getattr(record, "id", None) for record in duplicate_records],
                },
            ))

    for key, repeated_records in party_amount_date_index.items():
        if len(repeated_records) > 1:
            first = repeated_records[0]
            party, amount, txn_date = key
            findings.append(_finding(
                first,
                "repeated_tds_payment_pattern",
                "medium",
                "Repeated party/date/amount payment pattern",
                "Same party, same amount, and same date appears multiple times. Review for duplicate payment or split booking.",
                {
                    "party_name": party,
                    "amount": amount,
                    "transaction_date": txn_date,
                    "duplicate_count": len(repeated_records),
                    "source_rows": [getattr(record, "source_row", None) for record in repeated_records],
                },
            ))

    return findings
