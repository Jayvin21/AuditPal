from datetime import date, datetime
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
    lowered = {str(k).strip().lower(): v for k, v in raw.items()}

    for key in keys:
        if key in raw and raw[key] not in [None, ""]:
            return raw[key]

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
        or _raw(record, "Party Name", "Customer Name", "Vendor Name", "Supplier Name", "Name 1", "Account")
        or ""
    )


def _invoice_date(record):
    return (
        getattr(record, "transaction_date", None)
        or _raw(record, "Invoice Date", "Bill Date", "Document Date", "Posting Date", "Date")
    )


def _due_date(record):
    return _raw(record, "Due Date", "Payment Due Date", "Net Due Date", "Aging Date", "Due") or ""


def _outstanding(record):
    return _amount(
        _raw(
            record,
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

    direct = _amount(_raw(record, "Days Overdue", "Overdue Days", "Age", "Aging Days", "Days"))
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


def _is_receivable(record):
    typ = _lower(getattr(record, "record_type", ""))
    text = " ".join([
        typ,
        _lower(_raw(record, "Report Type", "Type", "Nature") or ""),
        _lower(_party(record)),
    ])
    return "receivable" in text or "debtor" in text or "customer" in text


def _is_payable(record):
    typ = _lower(getattr(record, "record_type", ""))
    text = " ".join([
        typ,
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
