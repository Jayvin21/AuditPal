from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


EXPENSE_KEYWORDS_PERSONAL = [
    "hotel", "restaurant", "swiggy", "zomato", "food", "meal",
    "travel", "flight", "uber", "ola", "fuel", "petrol",
    "gift", "entertainment", "misc", "miscellaneous"
]

CASH_KEYWORDS = ["cash", "petty cash", "cash payment", "paid cash"]


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


def _record_description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text")
        or getattr(record, "description", None)
        or ""
    )


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(record, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": title,
        "description": description,
        "evidence": evidence,
    }


def run_expense_checks(records):
    findings = []

    voucher_index = defaultdict(list)
    party_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party_name = _norm(getattr(record, "party_name", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)
        amount = _amount(getattr(record, "amount", None))
        description = _record_description(record)
        description_lower = _lower(description)

        if document_id:
            voucher_index[document_id.lower()].append(record)

        if party_name and amount is not None and txn_date_text:
            key = (party_name.lower(), round(abs(amount), 2), txn_date_text)
            party_amount_date_index[key].append(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_expense_voucher_number",
                "medium",
                "Missing expense voucher/reference number",
                "Expense entry does not have a voucher, bill, invoice, or reference number.",
            ))

        if not party_name:
            findings.append(_finding(
                record,
                "missing_expense_party",
                "medium",
                "Missing vendor/party in expense entry",
                "Expense entry does not identify the vendor, employee, ledger, or party.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "missing_expense_amount",
                "high",
                "Missing expense amount",
                "Expense entry does not contain a usable amount.",
            ))
            continue

        if amount <= 0:
            findings.append(_finding(
                record,
                "non_positive_expense_amount",
                "medium",
                "Non-positive expense amount",
                "Expense entry has zero or negative amount and should be reviewed.",
                {"amount": amount},
            ))

        if abs(amount) >= 50000:
            findings.append(_finding(
                record,
                "high_value_expense",
                "high",
                "High-value expense",
                "Expense amount is above ₹50,000 and should be verified with supporting documents and approval.",
                {"amount": amount},
            ))

        if abs(amount) >= 10000 and any(keyword in description_lower for keyword in CASH_KEYWORDS):
            findings.append(_finding(
                record,
                "high_value_cash_expense",
                "high",
                "High-value cash expense",
                "Cash expense above ₹10,000 may require additional scrutiny under audit/tax review.",
                {"amount": amount, "description": description},
            ))

        if abs(amount) >= 1000 and abs(amount) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_expense",
                "low",
                "Round-number expense",
                "Expense amount is a round number. This is not necessarily wrong but can indicate estimated or unsupported entries.",
                {"amount": amount},
            ))

        if _is_year_end(txn_date):
            findings.append(_finding(
                record,
                "year_end_expense",
                "medium",
                "Year-end expense entry",
                "Expense was recorded near financial year end and should be checked for cut-off and supporting documents.",
                {"transaction_date": txn_date_text},
            ))

        if not description or len(description.strip()) < 4:
            findings.append(_finding(
                record,
                "missing_or_weak_expense_narration",
                "low",
                "Missing or weak expense narration",
                "Expense entry has no meaningful narration or description.",
            ))

        if any(keyword in description_lower for keyword in EXPENSE_KEYWORDS_PERSONAL):
            findings.append(_finding(
                record,
                "sensitive_or_discretionary_expense",
                "medium",
                "Sensitive/discretionary expense category",
                "Expense narration suggests travel, food, hotel, fuel, entertainment, gift, or miscellaneous spend. Verify business purpose and approval.",
                {"description": description},
            ))

    for voucher, duplicate_records in voucher_index.items():
        if len(duplicate_records) > 1:
            for record in duplicate_records:
                findings.append(_finding(
                    record,
                    "duplicate_expense_voucher",
                    "high",
                    "Duplicate expense voucher/reference",
                    "Same expense voucher/reference number appears more than once.",
                    {"voucher": voucher, "duplicate_count": len(duplicate_records)},
                ))

    for key, repeated_records in party_amount_date_index.items():
        if len(repeated_records) > 1:
            party_name, amount, txn_date = key
            for record in repeated_records:
                findings.append(_finding(
                    record,
                    "repeated_expense_pattern",
                    "medium",
                    "Repeated same-party same-amount expense",
                    "Same party, same amount, and same date appears multiple times. Check for duplicate booking.",
                    {
                        "party_name": party_name,
                        "amount": amount,
                        "transaction_date": txn_date,
                        "duplicate_count": len(repeated_records),
                    },
                ))

    return findings
