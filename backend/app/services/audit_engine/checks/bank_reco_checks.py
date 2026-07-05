from datetime import datetime
from collections import defaultdict
from typing import Any

from rapidfuzz import fuzz

from app.models.extracted_record import ExtractedRecord


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


def date_diff_days(a: str | None, b: str | None) -> int | None:
    da = parse_date(a)
    db = parse_date(b)

    if not da or not db:
        return None

    return abs((da - db).days)


def normalize_amount(value: float | None) -> float | None:
    if value is None:
        return None
    return round(abs(float(value)), 2)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.upper().split())


def description(record: ExtractedRecord) -> str:
    raw = record.raw_data or {}
    return raw.get("description") or record.party_name or ""


def make_finding(
    finding_type: str,
    risk_level: str,
    title: str,
    description_text: str,
    source_record_id: int | None,
    evidence: dict[str, Any],
    matched_record_id: int | None = None,
) -> dict[str, Any]:
    return {
        "finding_type": finding_type,
        "risk_level": risk_level,
        "title": title,
        "description": description_text,
        "source_record_id": source_record_id,
        "matched_record_id": matched_record_id,
        "evidence": evidence,
    }


def record_evidence(record: ExtractedRecord) -> dict[str, Any]:
    return {
        "record_id": record.id,
        "record_type": record.record_type,
        "source_row": record.source_row,
        "document_id": record.document_id,
        "party_name": record.party_name,
        "transaction_date": record.transaction_date,
        "amount": record.amount,
        "description": description(record),
        "raw_data": record.raw_data,
    }


def find_best_match(
    source: ExtractedRecord,
    candidates: list[ExtractedRecord],
    amount_tolerance: float = 1.0,
    date_tolerance_days: int = 3,
):
    source_amount = normalize_amount(source.amount)

    if source_amount is None:
        return None, 0, "missing_amount"

    best = None
    best_score = 0
    best_reason = ""

    for candidate in candidates:
        candidate_amount = normalize_amount(candidate.amount)

        if candidate_amount is None:
            continue

        amount_diff = abs(source_amount - candidate_amount)

        if amount_diff > amount_tolerance:
            continue

        days = date_diff_days(source.transaction_date, candidate.transaction_date)
        date_score = 35 if days is not None and days <= date_tolerance_days else 10

        source_text = normalize_text(description(source))
        candidate_text = normalize_text(description(candidate))
        text_score = fuzz.partial_ratio(source_text, candidate_text) if source_text and candidate_text else 0

        score = 50 + date_score + int(text_score * 0.15)

        if score > best_score:
            best = candidate
            best_score = score
            best_reason = f"amount matched within {amount_tolerance}, date difference={days}, text similarity={text_score}"

    return best, best_score, best_reason


def run_bank_reconciliation_checks(
    bank_records: list[ExtractedRecord],
    ledger_records: list[ExtractedRecord],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    matched_bank_ids = set()
    matched_ledger_ids = set()

    for bank_record in bank_records:
        match, score, reason = find_best_match(bank_record, ledger_records)

        if match and score >= 60:
            matched_bank_ids.add(bank_record.id)
            matched_ledger_ids.add(match.id)
            continue

        risk = "high" if bank_record.amount is not None and abs(bank_record.amount) >= 50000 else "medium"

        findings.append(
            make_finding(
                finding_type="bank_entry_missing_in_books",
                risk_level=risk,
                title="Bank transaction not matched in books",
                description_text="This bank statement entry does not have a strong matching ledger/book entry.",
                source_record_id=bank_record.id,
                evidence={
                    "bank_record": record_evidence(bank_record),
                    "match_attempt": {
                        "best_score": score,
                        "reason": reason,
                    },
                },
            )
        )

    for ledger_record in ledger_records:
        if ledger_record.id in matched_ledger_ids:
            continue

        match, score, reason = find_best_match(ledger_record, bank_records)

        if match and score >= 60:
            continue

        risk = "high" if ledger_record.amount is not None and abs(ledger_record.amount) >= 50000 else "medium"

        findings.append(
            make_finding(
                finding_type="book_entry_missing_in_bank",
                risk_level=risk,
                title="Book entry not matched in bank statement",
                description_text="This ledger/book entry does not have a strong matching bank statement entry.",
                source_record_id=ledger_record.id,
                evidence={
                    "ledger_record": record_evidence(ledger_record),
                    "match_attempt": {
                        "best_score": score,
                        "reason": reason,
                    },
                },
            )
        )

    bank_duplicate_groups = defaultdict(list)

    for record in bank_records:
        amount = normalize_amount(record.amount)
        if amount is None:
            continue
        key = (amount, record.transaction_date, normalize_text(description(record))[:24])
        bank_duplicate_groups[key].append(record)

    for key, group in bank_duplicate_groups.items():
        if len(group) <= 1:
            continue

        findings.append(
            make_finding(
                finding_type="duplicate_bank_transaction_pattern",
                risk_level="medium",
                title="Repeated bank transaction pattern",
                description_text="Multiple bank statement entries share the same amount, date, and similar narration.",
                source_record_id=group[0].id,
                evidence={
                    "group_key": key,
                    "count": len(group),
                    "records": [record_evidence(record) for record in group],
                },
            )
        )

    return findings