from decimal import Decimal, InvalidOperation


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
    lowered = {str(k).strip().lower(): v for k, v in raw.items()}

    for key in keys:
        if key in raw and raw[key] not in [None, ""]:
            return raw[key]

        lowered_key = key.strip().lower()
        if lowered_key in lowered and lowered[lowered_key] not in [None, ""]:
            return lowered[lowered_key]

    return None


def _ledger_name(record):
    return (
        getattr(record, "party_name", None)
        or _raw(record, "Ledger Name", "Account Name", "Account", "Particulars", "G/L Account", "GL Account", "Ledger")
        or ""
    )


def _group(record):
    return _raw(record, "Group", "Primary Group", "Schedule", "FS Group", "Classification", "Nature") or ""


def _debit(record):
    return _amount(_raw(record, "Debit", "Debit Balance", "Dr", "Dr Balance"))


def _credit(record):
    return _amount(_raw(record, "Credit", "Credit Balance", "Cr", "Cr Balance"))


def _closing_balance(record):
    direct = _amount(
        _raw(
            record,
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
        bits.append(f"₹{abs(balance):,.0f} { _balance_side(balance) }")

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

    if difference > 1:
        pseudo_record = records[0] if records else None
        if pseudo_record:
            findings.append(_finding(
                pseudo_record,
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
