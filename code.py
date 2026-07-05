from pathlib import Path

ROOT = Path(r"D:\1Workspace\AuditPal")
CHECKS = ROOT / "backend" / "app" / "services" / "audit_engine" / "checks"

TDS = CHECKS / "tds_checks.py"
TRIAL_BALANCE = CHECKS / "trial_balance_checks.py"
AGING = CHECKS / "aging_checks.py"

# ----------------------------------------------------
# 1. TDS checks: prefer canonical mapped fields
# ----------------------------------------------------

TDS.write_text(
r'''from collections import defaultdict
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


def _description(record):
    return (
        _raw(record, "description", "narration", "Narration", "Description", "Particulars", "Text", "Nature")
        or getattr(record, "description", None)
        or ""
    )


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "party_name", "Party Name", "Vendor Name", "Supplier Name", "Name 1", "Particulars")
        or ""
    )


def _pan(record):
    return _raw("pan") if False else (
        _raw(record, "pan", "PAN", "Vendor PAN", "Supplier PAN", "Permanent Account Number", "PAN No", "PAN Number")
        or ""
    )


def _tds_amount(record):
    return _amount(
        _raw(
            record,
            "tds_amount",
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
    return (
        _raw(record, "tds_section", "TDS Section", "Section", "TDS Nature", "194C/194J", "Withholding Tax Code", "WHT Code")
        or ""
    )


def _nature(record):
    return (
        _raw(record, "payment_nature", "Nature", "Expense Nature", "Payment Nature", "Ledger Name", "G/L Account", "GL Account")
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
''',
encoding="utf-8",
)

# ----------------------------------------------------
# 2. Trial Balance checks: prefer canonical mapped fields
# ----------------------------------------------------

TRIAL_BALANCE.write_text(
r'''from decimal import Decimal, InvalidOperation


ASSET_KEYWORDS = [
    "cash", "bank", "debtor", "receivable", "asset", "fixed asset", "inventory",
    "stock", "advance", "deposit", "loan given", "prepaid"
]

LIABILITY_KEYWORDS = [
    "creditor", "payable", "liability", "loan", "unsecured loan", "secured loan",
    "capital", "provision", "duties", "tax payable", "gst payable", "tds payable"
]

INCOME_KEYWORDS = [
    "sales", "revenue", "income", "interest received", "commission received"
]

EXPENSE_KEYWORDS = [
    "expense", "purchase", "salary", "wages", "rent", "professional fees",
    "repairs", "maintenance", "depreciation", "travelling", "office"
]

SUSPENSE_KEYWORDS = ["suspense", "temporary", "dummy", "unknown", "unclassified"]
CASH_BANK_KEYWORDS = ["cash", "bank"]
LOAN_ADVANCE_KEYWORDS = ["loan", "advance", "deposit"]


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


def _ledger_name(record):
    return (
        _raw(record, "ledger_name", "Ledger Name", "Account Name", "Account", "Particulars", "G/L Account", "GL Account", "Ledger")
        or getattr(record, "party_name", None)
        or ""
    )


def _group(record):
    return _raw(record, "ledger_group", "Group", "Primary Group", "Schedule", "FS Group", "Classification", "Nature") or ""


def _debit(record):
    return _amount(_raw(record, "debit_balance", "Debit", "Debit Balance", "Dr", "Dr Balance"))


def _credit(record):
    return _amount(_raw(record, "credit_balance", "Credit", "Credit Balance", "Cr", "Cr Balance"))


def _closing_balance(record):
    direct = _amount(
        _raw(
            record,
            "closing_balance",
            "Closing Balance",
            "Balance",
            "Amount",
            "Closing",
            "Net Balance",
            "Current Year Balance",
        )
    )

    if direct is not None:
        return direct

    debit = _debit(record)
    credit = _credit(record)

    if debit is not None or credit is not None:
        return (debit or 0) - (credit or 0)

    return _amount(getattr(record, "amount", None))


def _balance_side(balance):
    if balance is None:
        return ""
    if balance > 0:
        return "debit"
    if balance < 0:
        return "credit"
    return "zero"


def _classification_text(record):
    return " ".join([
        _lower(_ledger_name(record)),
        _lower(_group(record)),
        _lower(_raw(record, "Description", "Narration", "Text") or ""),
    ])


def _expected_nature(text):
    if any(keyword in text for keyword in ASSET_KEYWORDS):
        return "asset"
    if any(keyword in text for keyword in LIABILITY_KEYWORDS):
        return "liability"
    if any(keyword in text for keyword in INCOME_KEYWORDS):
        return "income"
    if any(keyword in text for keyword in EXPENSE_KEYWORDS):
        return "expense"
    return "unknown"


def _title(base, record):
    ledger = _ledger_name(record)
    balance = _closing_balance(record)
    bits = []

    if ledger:
        bits.append(ledger)
    if balance is not None:
        bits.append(f"₹{abs(balance):,.0f} {_balance_side(balance)}")

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:2])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    balance = _closing_balance(record)

    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "ledger_name": _ledger_name(record),
        "group": _group(record),
        "closing_balance": balance,
        "balance_side": _balance_side(balance),
        "debit": _debit(record),
        "credit": _credit(record),
        "document_id": getattr(record, "document_id", None),
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


def run_trial_balance_checks(records):
    findings = []

    total_debit_balance = 0
    total_credit_balance = 0

    for record in records:
        ledger = _ledger_name(record)
        text = _classification_text(record)
        expected = _expected_nature(text)
        balance = _closing_balance(record)
        side = _balance_side(balance)

        if not ledger:
            findings.append(_finding(
                record,
                "missing_ledger_name_trial_balance",
                "high",
                "Missing ledger/account name",
                "Trial balance row does not contain a usable ledger/account name.",
            ))

        if balance is None:
            findings.append(_finding(
                record,
                "missing_trial_balance_amount",
                "high",
                "Missing trial balance amount",
                "Trial balance row does not contain debit, credit, or closing balance amount.",
            ))
            continue

        if balance > 0:
            total_debit_balance += balance
        elif balance < 0:
            total_credit_balance += abs(balance)

        if any(keyword in text for keyword in SUSPENSE_KEYWORDS) and abs(balance) > 0:
            findings.append(_finding(
                record,
                "suspense_balance_present",
                "high",
                "Suspense/temporary account has balance",
                "Suspense, temporary, dummy, unknown, or unclassified ledger has a non-zero balance.",
                {"classification_text": text},
            ))

        if any(keyword in text for keyword in CASH_BANK_KEYWORDS) and balance < 0:
            findings.append(_finding(
                record,
                "negative_cash_or_bank_balance",
                "high",
                "Negative cash/bank balance",
                "Cash or bank ledger has credit/negative balance. Review overdraft classification, bank reconciliation, or posting error.",
                {"classification_text": text},
            ))

        if expected == "asset" and side == "credit":
            findings.append(_finding(
                record,
                "asset_ledger_credit_balance",
                "medium",
                "Asset ledger has credit balance",
                "Ledger appears to be an asset but has a credit balance. Review classification and postings.",
                {"expected_nature": expected},
            ))

        if expected == "liability" and side == "debit":
            findings.append(_finding(
                record,
                "liability_ledger_debit_balance",
                "medium",
                "Liability ledger has debit balance",
                "Ledger appears to be a liability but has a debit balance. Review classification, advances, or reversal postings.",
                {"expected_nature": expected},
            ))

        if expected == "income" and side == "debit":
            findings.append(_finding(
                record,
                "income_ledger_debit_balance",
                "medium",
                "Income ledger has debit balance",
                "Ledger appears to be income/revenue but has a debit balance. Review returns, reversals, or classification.",
                {"expected_nature": expected},
            ))

        if expected == "expense" and side == "credit":
            findings.append(_finding(
                record,
                "expense_ledger_credit_balance",
                "medium",
                "Expense ledger has credit balance",
                "Ledger appears to be expense but has a credit balance. Review reversals, provisions, or classification.",
                {"expected_nature": expected},
            ))

        if abs(balance) >= 500000:
            findings.append(_finding(
                record,
                "high_value_trial_balance_ledger",
                "medium",
                "High-value trial balance ledger",
                "Ledger balance is above ₹5,00,000. Consider materiality, variance, and supporting schedule review.",
                {"balance": balance},
            ))

        if abs(balance) >= 10000 and abs(balance) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_trial_balance_ledger",
                "low",
                "Round-number ledger balance",
                "Ledger balance is a round number. This can be normal but may indicate manual estimate or provision.",
                {"balance": balance},
            ))

        if any(keyword in text for keyword in LOAN_ADVANCE_KEYWORDS) and abs(balance) >= 100000:
            findings.append(_finding(
                record,
                "loan_advance_deposit_balance_review",
                "medium",
                "Loan/advance/deposit balance review",
                "Ledger appears to involve loan, advance, or deposit balance. Verify confirmation, classification, and recoverability.",
                {"classification_text": text, "balance": balance},
            ))

    difference = round(abs(total_debit_balance - total_credit_balance), 2)

    if difference > 1 and records:
        findings.append(_finding(
            records[0],
            "trial_balance_not_balanced",
            "high",
            "Trial balance debit/credit totals do not match",
            "Total debit balances and total credit balances do not agree. Review export format, missing rows, or mapping.",
            {
                "total_debit_balance": round(total_debit_balance, 2),
                "total_credit_balance": round(total_credit_balance, 2),
                "difference": difference,
            },
        ))

    return findings
''',
encoding="utf-8",
)

# ----------------------------------------------------
# 3. Aging checks: prefer canonical mapped fields
# ----------------------------------------------------

AGING.write_text(
r'''from datetime import date, datetime
from decimal import Decimal, InvalidOperation


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


def _parse_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    return None


def _date_string(value):
    parsed = _parse_date(value)
    if parsed:
        return parsed.isoformat()
    return _norm(value)


def _party(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "party_name", "Party Name", "Customer Name", "Vendor Name", "Supplier Name", "Name 1", "Account")
        or ""
    )


def _invoice_date(record):
    return (
        _raw(record, "invoice_date", "Invoice Date", "Bill Date", "Document Date", "Posting Date", "Date")
        or getattr(record, "transaction_date", None)
    )


def _due_date(record):
    return _raw(record, "due_date", "Due Date", "Payment Due Date", "Net Due Date", "Aging Date", "Due") or ""


def _outstanding(record):
    return _amount(
        _raw(
            record,
            "outstanding_amount",
            "Outstanding",
            "Outstanding Amount",
            "Balance",
            "Closing Balance",
            "Open Amount",
            "Amount Due",
            "Net Due",
            "Amount",
        )
        or getattr(record, "amount", None)
    )


def _days_overdue(record, as_of=None):
    if as_of is None:
        as_of = date.today()

    direct = _amount(_raw(record, "days_overdue", "Days Overdue", "Overdue Days", "Age", "Aging Days", "Days"))
    if direct is not None:
        return int(direct)

    due = _parse_date(_due_date(record))
    if not due:
        return None

    return (as_of - due).days


def _bucket(days):
    if days is None:
        return "unknown"
    if days <= 0:
        return "not_due"
    if days <= 30:
        return "0_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    if days <= 180:
        return "91_180"
    return "180_plus"


def _party_type(record):
    return _lower(_raw(record, "party_type", "Party Type", "Type", "Nature") or "")


def _is_receivable(record):
    typ = _lower(getattr(record, "record_type", ""))
    party_type = _party_type(record)
    text = " ".join([
        typ,
        party_type,
        _lower(_raw(record, "Report Type", "Type", "Nature") or ""),
        _lower(_party(record)),
    ])
    return "receivable" in text or "debtor" in text or "customer" in text


def _is_payable(record):
    typ = _lower(getattr(record, "record_type", ""))
    party_type = _party_type(record)
    text = " ".join([
        typ,
        party_type,
        _lower(_raw(record, "Report Type", "Type", "Nature") or ""),
        _lower(_party(record)),
    ])
    return "payable" in text or "creditor" in text or "vendor" in text or "supplier" in text


def _title(base, record):
    bits = []

    doc = _norm(getattr(record, "document_id", None))
    party = _norm(_party(record))
    outstanding = _outstanding(record)

    if doc:
        bits.append(doc)
    if party:
        bits.append(party)
    if outstanding is not None:
        bits.append(f"₹{abs(outstanding):,.0f}")

    if not bits:
        return base

    return f"{base} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    days = _days_overdue(record)
    outstanding = _outstanding(record)

    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": _party(record),
        "invoice_date": _date_string(_invoice_date(record)),
        "due_date": _date_string(_due_date(record)),
        "days_overdue": days,
        "aging_bucket": _bucket(days),
        "outstanding_amount": outstanding,
        "party_type": _party_type(record),
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


def run_aging_checks(records):
    findings = []

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party = _norm(_party(record))
        outstanding = _outstanding(record)
        days = _days_overdue(record)
        due = _due_date(record)
        invoice_date = _invoice_date(record)

        is_receivable = _is_receivable(record)
        is_payable = _is_payable(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_aging_invoice_reference",
                "medium",
                "Missing invoice/reference in aging report",
                "Aging row does not have invoice, bill, voucher, or reference number.",
            ))

        if not party:
            findings.append(_finding(
                record,
                "missing_aging_party",
                "high",
                "Missing customer/vendor name",
                "Aging row does not identify the customer/vendor/party.",
            ))

        if not invoice_date:
            findings.append(_finding(
                record,
                "missing_aging_invoice_date",
                "medium",
                "Missing invoice/document date",
                "Aging row does not have invoice/document date.",
            ))

        if not due:
            findings.append(_finding(
                record,
                "missing_due_date",
                "medium",
                "Missing due date",
                "Aging row does not contain a due date, so overdue status cannot be verified reliably.",
            ))

        if outstanding is None:
            findings.append(_finding(
                record,
                "missing_outstanding_amount",
                "high",
                "Missing outstanding amount",
                "Aging row does not contain a usable outstanding amount.",
            ))
            continue

        if outstanding == 0:
            findings.append(_finding(
                record,
                "zero_outstanding_in_aging",
                "low",
                "Zero outstanding in aging report",
                "Aging row has zero outstanding amount. Check if it should be excluded from open-item report.",
                {"outstanding_amount": outstanding},
            ))

        if outstanding < 0:
            findings.append(_finding(
                record,
                "negative_outstanding_amount",
                "medium",
                "Negative outstanding amount",
                "Aging row has negative outstanding amount. Review credit note, advance, overpayment, or classification.",
                {"outstanding_amount": outstanding},
            ))

        if abs(outstanding) >= 500000:
            findings.append(_finding(
                record,
                "high_value_outstanding_balance",
                "high",
                "High-value outstanding balance",
                "Outstanding balance is above ₹5,00,000 and should be prioritized for confirmation/recovery/payment review.",
                {"outstanding_amount": outstanding},
            ))

        if abs(outstanding) >= 10000 and abs(outstanding) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_outstanding_balance",
                "low",
                "Round-number outstanding balance",
                "Outstanding amount is a round number. This can be normal but may indicate estimate/manual adjustment.",
                {"outstanding_amount": outstanding},
            ))

        if days is None:
            findings.append(_finding(
                record,
                "unknown_aging_bucket",
                "medium",
                "Unknown aging bucket",
                "Days overdue could not be calculated because due date or aging days are missing/invalid.",
            ))
            continue

        if days > 180:
            risk = "high" if is_receivable else "medium"
            findings.append(_finding(
                record,
                "over_180_days_outstanding",
                risk,
                "Outstanding over 180 days",
                "Open item is outstanding for more than 180 days. Review recoverability, provision, confirmation, dispute, or payment plan.",
                {"days_overdue": days},
            ))
        elif days > 90:
            findings.append(_finding(
                record,
                "over_90_days_outstanding",
                "medium",
                "Outstanding over 90 days",
                "Open item is outstanding for more than 90 days and should be reviewed for follow-up, confirmation, or settlement.",
                {"days_overdue": days},
            ))
        elif days > 60:
            findings.append(_finding(
                record,
                "over_60_days_outstanding",
                "low",
                "Outstanding over 60 days",
                "Open item is outstanding for more than 60 days.",
                {"days_overdue": days},
            ))

        if is_receivable and days > 90 and outstanding > 0:
            findings.append(_finding(
                record,
                "old_receivable_recoverability_review",
                "high",
                "Old receivable recoverability review",
                "Receivable is old and should be reviewed for recoverability, expected credit loss/provision, and balance confirmation.",
                {"days_overdue": days, "outstanding_amount": outstanding},
            ))

        if is_payable and days > 180 and outstanding > 0:
            findings.append(_finding(
                record,
                "old_payable_confirmation_review",
                "medium",
                "Old payable confirmation review",
                "Payable is old and should be reviewed for vendor confirmation, dispute, write-back, or settlement status.",
                {"days_overdue": days, "outstanding_amount": outstanding},
            ))

    return findings
''',
encoding="utf-8",
)

print("Pass 2 Task 2 applied.")
print("Updated:")
print(f"- {TDS}")
print(f"- {TRIAL_BALANCE}")
print(f"- {AGING}")