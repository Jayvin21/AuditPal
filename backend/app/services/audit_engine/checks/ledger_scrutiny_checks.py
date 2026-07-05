from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


SUSPENSE_KEYWORDS = ["suspense", "temporary", "dummy", "unclassified", "unknown"]
CASH_KEYWORDS = ["cash", "petty cash"]
LOAN_ADVANCE_KEYWORDS = ["loan", "advance", "deposit", "unsecured loan", "director loan"]
MANUAL_ENTRY_KEYWORDS = ["journal", "manual", "jv", "adjustment", "provision", "rectification"]


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
    for key in keys:
        if key in raw and raw[key] not in [None, ""]:
            return raw[key]
    return None


def _description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text")
        or getattr(record, "description", None)
        or ""
    )


def _voucher_type(record):
    return _raw(record, "Voucher Type", "voucher_type", "Document Type", "document_type", "Entry Type") or ""


def _ledger_name(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Ledger Name", "G/L Account", "GL Account", "Account", "Particulars", "Cost Center")
        or ""
    )


def _money(value):
    amount = _amount(value)
    if amount is None:
        return ""
    return f"₹{amount:,.0f}"


def _title(base, record):
    bits = []
    doc = _norm(getattr(record, "document_id", None))
    ledger = _norm(_ledger_name(record))
    amount = _money(getattr(record, "amount", None))

    if doc:
        bits.append(doc)
    if ledger:
        bits.append(ledger)
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
        "ledger_name": _ledger_name(record),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "description": _description(record),
        "voucher_type": _voucher_type(record),
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


def run_ledger_scrutiny_checks(records):
    findings = []
    voucher_index = defaultdict(list)
    ledger_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        ledger_name = _norm(_ledger_name(record))
        ledger_lower = ledger_name.lower()
        description = _description(record)
        description_lower = description.lower()
        voucher_type = _voucher_type(record)
        voucher_type_lower = voucher_type.lower()
        amount = _amount(getattr(record, "amount", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)

        combined_text = " ".join([ledger_lower, description_lower, voucher_type_lower])

        if document_id:
            voucher_index[document_id.lower()].append(record)

        if ledger_name and amount is not None and txn_date_text:
            ledger_amount_date_index[(ledger_lower, round(abs(amount), 2), txn_date_text)].append(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_ledger_voucher_number",
                "medium",
                "Missing ledger voucher/reference number",
                "Ledger entry has no voucher, document, reference, or journal number.",
            ))

        if not ledger_name:
            findings.append(_finding(
                record,
                "missing_ledger_name",
                "medium",
                "Missing ledger/account name",
                "Ledger entry does not identify the ledger, account, party, cost center, or G/L account.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "missing_ledger_amount",
                "high",
                "Missing ledger amount",
                "Ledger entry does not contain a usable amount.",
            ))
            continue

        if abs(amount) >= 100000:
            findings.append(_finding(
                record,
                "high_value_ledger_entry",
                "high",
                "High-value ledger entry",
                "Ledger entry is above ₹1,00,000 and should be verified with supporting documents and approval trail.",
                {"amount": amount},
            ))

        if abs(amount) >= 1000 and abs(amount) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_ledger_entry",
                "low",
                "Round-number ledger entry",
                "Ledger entry has a round amount. This can be normal, but should be reviewed for manual or estimated postings.",
                {"amount": amount},
            ))

        if _is_year_end(txn_date):
            findings.append(_finding(
                record,
                "year_end_ledger_entry",
                "medium",
                "Year-end ledger entry",
                "Ledger entry was posted near financial year end. Review cut-off, provisioning, reversal, and supporting documents.",
                {"transaction_date": txn_date_text},
            ))

        if any(keyword in combined_text for keyword in SUSPENSE_KEYWORDS):
            findings.append(_finding(
                record,
                "suspense_or_temporary_account_activity",
                "high",
                "Suspense/temporary account activity",
                "Ledger entry appears to involve suspense, temporary, dummy, unknown, or unclassified accounts.",
                {"matched_text": combined_text},
            ))

        if any(keyword in combined_text for keyword in MANUAL_ENTRY_KEYWORDS):
            findings.append(_finding(
                record,
                "manual_or_journal_entry",
                "medium",
                "Manual/journal entry indicator",
                "Ledger entry appears to be a manual, journal, adjustment, provision, or rectification posting.",
                {"voucher_type": voucher_type, "description": description},
            ))

        if any(keyword in combined_text for keyword in CASH_KEYWORDS) and abs(amount) >= 10000:
            findings.append(_finding(
                record,
                "high_value_cash_ledger_activity",
                "high",
                "High-value cash ledger activity",
                "Cash or petty-cash ledger activity above ₹10,000 should be reviewed for tax/audit sensitivity and supporting documents.",
                {"amount": amount},
            ))

        if any(keyword in combined_text for keyword in LOAN_ADVANCE_KEYWORDS) and abs(amount) >= 50000:
            findings.append(_finding(
                record,
                "loan_or_advance_movement",
                "medium",
                "Loan/advance/deposit ledger movement",
                "Ledger entry appears to involve loans, advances, deposits, or unsecured loan movement. Verify agreement, confirmation, and classification.",
                {"amount": amount},
            ))

        if not description or len(description.strip()) < 4:
            findings.append(_finding(
                record,
                "missing_or_weak_ledger_narration",
                "low",
                "Missing or weak ledger narration",
                "Ledger entry has no meaningful narration, text, or description.",
            ))

    for voucher, duplicate_records in voucher_index.items():
        if len(duplicate_records) > 1:
            first = duplicate_records[0]
            findings.append(_finding(
                first,
                "duplicate_ledger_voucher_reference",
                "medium",
                "Duplicate ledger voucher/reference",
                "Same voucher/reference appears more than once in ledger data. Review whether this is valid multi-line accounting or duplicate posting.",
                {
                    "voucher": voucher,
                    "duplicate_count": len(duplicate_records),
                    "source_rows": [getattr(record, "source_row", None) for record in duplicate_records],
                    "record_ids": [getattr(record, "id", None) for record in duplicate_records],
                },
            ))

    for key, repeated_records in ledger_amount_date_index.items():
        if len(repeated_records) > 1:
            first = repeated_records[0]
            ledger_name, amount, txn_date = key
            findings.append(_finding(
                first,
                "repeated_ledger_pattern",
                "medium",
                "Repeated ledger amount/date pattern",
                "Same ledger, same amount, and same date appears multiple times. Review for duplicate posting or repeated adjustment.",
                {
                    "ledger_name": ledger_name,
                    "amount": amount,
                    "transaction_date": txn_date,
                    "duplicate_count": len(repeated_records),
                    "source_rows": [getattr(record, "source_row", None) for record in repeated_records],
                },
            ))

    return findings
