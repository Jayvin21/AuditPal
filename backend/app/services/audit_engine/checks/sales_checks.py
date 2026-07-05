from collections import defaultdict
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


def _gstin_valid(gstin):
    gstin = _norm(gstin).upper()
    if not gstin:
        return False
    if len(gstin) != 15:
        return False
    if not gstin[:2].isdigit():
        return False
    if not gstin[2:12].isalnum():
        return False
    return True


def _money(value):
    amount = _amount(value)
    if amount is None:
        return ""
    return f"₹{amount:,.0f}"


def _context_title(base_title, record):
    document_id = _norm(getattr(record, "document_id", None))
    party_name = _norm(getattr(record, "party_name", None))
    amount = _money(getattr(record, "amount", None))
    source_row = getattr(record, "source_row", None)

    bits = []
    if document_id:
        bits.append(document_id)
    if party_name:
        bits.append(party_name)
    if amount:
        bits.append(amount)
    if source_row:
        bits.append(f"row {source_row}")

    if not bits:
        return base_title

    return f"{base_title} — {' · '.join(bits[:3])}"


def _finding(record, finding_type, risk_level, title, description, extra=None):
    evidence = {
        "record_id": getattr(record, "id", None),
        "source_row": getattr(record, "source_row", None),
        "document_id": getattr(record, "document_id", None),
        "party_name": getattr(record, "party_name", None),
        "transaction_date": _date_string(getattr(record, "transaction_date", None)),
        "amount": getattr(record, "amount", None),
        "gstin": getattr(record, "gstin", None),
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(record, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _context_title(title, record),
        "description": description,
        "evidence": evidence,
    }


def _group_finding(records, finding_type, risk_level, title, description, extra=None):
    first = records[0]
    source_rows = [getattr(record, "source_row", None) for record in records]
    record_ids = [getattr(record, "id", None) for record in records]

    evidence = {
        "record_ids": record_ids,
        "source_rows": source_rows,
        "duplicate_count": len(records),
        "document_id": getattr(first, "document_id", None),
        "party_name": getattr(first, "party_name", None),
        "transaction_date": _date_string(getattr(first, "transaction_date", None)),
        "amount": getattr(first, "amount", None),
        "gstin": getattr(first, "gstin", None),
    }

    if extra:
        evidence.update(extra)

    return {
        "source_record_id": getattr(first, "id", None),
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": _context_title(title, first),
        "description": description,
        "evidence": evidence,
    }


def run_sales_checks(records):
    findings = []

    invoice_index = defaultdict(list)
    customer_amount_date_index = defaultdict(list)

    for record in records:
        document_id = _norm(getattr(record, "document_id", None))
        party_name = _norm(getattr(record, "party_name", None))
        txn_date = getattr(record, "transaction_date", None)
        txn_date_text = _date_string(txn_date)
        amount = _amount(getattr(record, "amount", None))
        gstin = _norm(getattr(record, "gstin", None))
        description = _record_description(record)
        description_lower = _lower(description)

        if document_id:
            invoice_index[document_id.lower()].append(record)

        if party_name and amount is not None and txn_date_text:
            key = (party_name.lower(), round(abs(amount), 2), txn_date_text)
            customer_amount_date_index[key].append(record)

        if not document_id:
            findings.append(_finding(
                record,
                "missing_sales_invoice_number",
                "high",
                "Missing sales invoice number",
                "Sales entry does not have an invoice, bill, voucher, or reference number.",
            ))

        if not party_name:
            findings.append(_finding(
                record,
                "missing_customer_name",
                "medium",
                "Missing customer/party name",
                "Sales entry does not identify the customer or party.",
            ))

        if amount is None:
            findings.append(_finding(
                record,
                "missing_sales_amount",
                "high",
                "Missing sales amount",
                "Sales entry does not contain a usable amount.",
            ))
            continue

        if amount <= 0:
            findings.append(_finding(
                record,
                "non_positive_sales_amount",
                "high",
                "Zero or negative sales amount",
                "Sales entry has zero or negative value. Check for cancellation, credit note, or incorrect posting.",
                {"amount": amount},
            ))

        if abs(amount) >= 100000:
            findings.append(_finding(
                record,
                "high_value_sales_invoice",
                "medium",
                "High-value sales invoice",
                "Sales invoice is above ₹1,00,000 and should be verified for billing, GST, and collection trail.",
                {"amount": amount},
            ))

        if abs(amount) >= 1000 and abs(amount) % 1000 == 0:
            findings.append(_finding(
                record,
                "round_number_sales",
                "low",
                "Round-number sales invoice",
                "Sales amount is a round number. This is not necessarily wrong but should be reviewed for estimated/manual billing.",
                {"amount": amount},
            ))

        if not gstin:
            findings.append(_finding(
                record,
                "missing_customer_gstin",
                "medium",
                "Missing customer GSTIN",
                "Customer GSTIN is missing. This may be acceptable for B2C sales but should be reviewed for B2B invoices.",
            ))
        elif not _gstin_valid(gstin):
            findings.append(_finding(
                record,
                "invalid_customer_gstin",
                "high",
                "Invalid customer GSTIN format",
                "Customer GSTIN does not match the expected 15-character Indian GSTIN pattern.",
                {"gstin": gstin},
            ))

        if _is_year_end(txn_date):
            findings.append(_finding(
                record,
                "year_end_sales_invoice",
                "medium",
                "Year-end sales invoice",
                "Sales invoice was recorded near financial year end. Check cut-off, dispatch/service completion, and revenue recognition.",
                {"transaction_date": txn_date_text},
            ))

        if any(word in description_lower for word in ["cancel", "cancelled", "void"]):
            findings.append(_finding(
                record,
                "cancelled_sales_indicator",
                "medium",
                "Cancellation indicator in sales narration",
                "Sales narration suggests a cancelled or void invoice. Verify whether the entry should remain in revenue.",
                {"description": description},
            ))

        if any(word in description_lower for word in ["credit note", "sales return", "return"]):
            findings.append(_finding(
                record,
                "sales_return_or_credit_note_indicator",
                "medium",
                "Sales return / credit note indicator",
                "Narration suggests a sales return or credit note. Verify adjustment, GST impact, and linkage to original invoice.",
                {"description": description},
            ))

    for invoice, duplicate_records in invoice_index.items():
        if len(duplicate_records) > 1:
            findings.append(_group_finding(
                duplicate_records,
                "duplicate_sales_invoice",
                "high",
                f"Duplicate sales invoice {getattr(duplicate_records[0], 'document_id', invoice)}",
                "Same sales invoice/reference number appears more than once. Review the listed source rows together instead of treating each row as a separate issue.",
                {"invoice": invoice},
            ))

    for key, repeated_records in customer_amount_date_index.items():
        if len(repeated_records) > 1:
            customer_name, amount, txn_date = key
            findings.append(_group_finding(
                repeated_records,
                "repeated_sales_pattern",
                "medium",
                f"Repeated sales pattern for {customer_name}",
                "Same customer, same amount, and same date appears multiple times. Check for duplicate billing.",
                {
                    "customer_name": customer_name,
                    "amount": amount,
                    "transaction_date": txn_date,
                },
            ))

    return findings
