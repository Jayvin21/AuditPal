import re
from collections import defaultdict
from typing import Any

from app.models.extracted_record import ExtractedRecord


GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().upper())


def normalize_document_id(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip().upper()
    value = re.sub(r"[^A-Z0-9]", "", value)
    return value


def is_round_amount(amount: float | None) -> bool:
    if amount is None:
        return False
    return amount >= 10000 and amount % 1000 == 0


def is_high_value(amount: float | None, threshold: float = 50000) -> bool:
    return amount is not None and amount >= threshold


def is_year_end_date(date_value: str | None) -> bool:
    if not date_value:
        return False
    return date_value.endswith("-03-31") or date_value.endswith("-03-30") or date_value.endswith("-03-29")


def make_finding(
    finding_type: str,
    risk_level: str,
    title: str,
    description: str,
    source_record_id: int | None,
    evidence: dict[str, Any],
    matched_record_id: int | None = None,
) -> dict[str, Any]:
    return {
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": title,
        "description": description,
        "source_record_id": source_record_id,
        "matched_record_id": matched_record_id,
        "evidence": evidence,
    }


def run_basic_purchase_checks(records: list[ExtractedRecord]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    invoice_groups: dict[tuple[str, str], list[ExtractedRecord]] = defaultdict(list)
    vendor_amount_date_groups: dict[tuple[str, float, str], list[ExtractedRecord]] = defaultdict(list)

    for record in records:
        row_ref = {
            "record_id": record.id,
            "source_row": record.source_row,
            "document_id": record.document_id,
            "party_name": record.party_name,
            "transaction_date": record.transaction_date,
            "amount": record.amount,
            "gstin": record.gstin,
            "raw_data": record.raw_data,
        }

        if not record.document_id:
            findings.append(
                make_finding(
                    finding_type="missing_invoice_number",
                    risk_level="high",
                    title="Missing invoice or bill number",
                    description="This purchase record does not contain an invoice, bill, voucher, or document number.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )

        if not record.party_name:
            findings.append(
                make_finding(
                    finding_type="missing_party_name",
                    risk_level="medium",
                    title="Missing vendor or party name",
                    description="This purchase record does not contain a vendor, supplier, or party name.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )

        if record.amount is None:
            findings.append(
                make_finding(
                    finding_type="missing_amount",
                    risk_level="high",
                    title="Missing transaction amount",
                    description="This purchase record has no usable amount field.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )
        elif record.amount <= 0:
            findings.append(
                make_finding(
                    finding_type="non_positive_amount",
                    risk_level="high",
                    title="Zero or negative purchase amount",
                    description="This purchase record has a zero or negative amount, which needs manual verification.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )

        if record.gstin:
            gstin = normalize_text(record.gstin)
            if not GSTIN_REGEX.match(gstin):
                findings.append(
                    make_finding(
                        finding_type="invalid_gstin",
                        risk_level="medium",
                        title="Invalid GSTIN format",
                        description="The GSTIN on this record does not match the standard Indian GSTIN format.",
                        source_record_id=record.id,
                        evidence={**row_ref, "normalized_gstin": gstin},
                    )
                )
        else:
            findings.append(
                make_finding(
                    finding_type="missing_gstin",
                    risk_level="low",
                    title="Missing GSTIN",
                    description="This purchase record does not contain a GSTIN. This may be acceptable for non-GST vendors but should be reviewed.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )

        if is_round_amount(record.amount):
            findings.append(
                make_finding(
                    finding_type="round_amount",
                    risk_level="low",
                    title="Large round-number transaction",
                    description="This purchase amount is a large round number. Round-number transactions are not automatically wrong but are useful audit review candidates.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )

        if is_high_value(record.amount):
            findings.append(
                make_finding(
                    finding_type="high_value_purchase",
                    risk_level="medium",
                    title="High-value purchase transaction",
                    description="This purchase amount crosses the configured high-value threshold and should be reviewed.",
                    source_record_id=record.id,
                    evidence={**row_ref, "threshold": 50000},
                )
            )

        if is_year_end_date(record.transaction_date):
            findings.append(
                make_finding(
                    finding_type="year_end_transaction",
                    risk_level="medium",
                    title="Year-end purchase transaction",
                    description="This transaction is posted near financial year-end and should be reviewed for cutoff accuracy.",
                    source_record_id=record.id,
                    evidence=row_ref,
                )
            )

        normalized_invoice = normalize_document_id(record.document_id)
        normalized_party = normalize_text(record.party_name)

        if normalized_invoice:
            invoice_groups[(normalized_party, normalized_invoice)].append(record)

        if normalized_party and record.amount is not None and record.transaction_date:
            vendor_amount_date_groups[(normalized_party, float(record.amount), record.transaction_date)].append(record)

    for (party, invoice_no), grouped_records in invoice_groups.items():
        if len(grouped_records) > 1:
            rows = [record.source_row for record in grouped_records]
            record_ids = [record.id for record in grouped_records]

            findings.append(
                make_finding(
                    finding_type="duplicate_invoice_number",
                    risk_level="high",
                    title="Duplicate invoice number suspected",
                    description="The same vendor and invoice number appear more than once in the uploaded purchase records.",
                    source_record_id=grouped_records[0].id,
                    evidence={
                        "party_name_normalized": party,
                        "invoice_no_normalized": invoice_no,
                        "rows": rows,
                        "record_ids": record_ids,
                        "count": len(grouped_records),
                    },
                )
            )

    for (party, amount, transaction_date), grouped_records in vendor_amount_date_groups.items():
        if len(grouped_records) > 1:
            rows = [record.source_row for record in grouped_records]
            record_ids = [record.id for record in grouped_records]

            findings.append(
                make_finding(
                    finding_type="same_vendor_amount_date_repeated",
                    risk_level="medium",
                    title="Repeated same vendor, amount, and date",
                    description="Multiple records share the same vendor, amount, and date. This may be legitimate but is a duplicate-risk pattern.",
                    source_record_id=grouped_records[0].id,
                    evidence={
                        "party_name_normalized": party,
                        "amount": amount,
                        "transaction_date": transaction_date,
                        "rows": rows,
                        "record_ids": record_ids,
                        "count": len(grouped_records),
                    },
                )
            )

    return findings
