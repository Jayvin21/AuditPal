from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_run import AuditRun
from app.models.extracted_record import ExtractedRecord
from app.models.finding import Finding
from app.models.uploaded_file import UploadedFile
from app.services.audit_engine.runner import (
    parse_workspace_files,
    run_aging_review,
    run_bank_reconciliation,
    run_document_matching,
    run_expense_audit,
    run_fixed_asset_audit,
    run_gst_reconciliation,
    run_ledger_scrutiny,
    run_purchase_audit,
    run_sales_audit,
    run_tds_review,
    run_trial_balance_review,
)


MODULE_RUNNERS = {
    "purchase": ("Purchase Audit", run_purchase_audit),
    "sales": ("Sales Audit", run_sales_audit),
    "expense": ("Expense Audit", run_expense_audit),
    "gst": ("GST Reconciliation", run_gst_reconciliation),
    "bank": ("Bank Reconciliation", run_bank_reconciliation),
    "ledger": ("Ledger Scrutiny", run_ledger_scrutiny),
    "tds": ("TDS Review", run_tds_review),
    "fixed_asset": ("Fixed Asset Audit", run_fixed_asset_audit),
    "trial_balance": ("Trial Balance Review", run_trial_balance_review),
    "aging": ("Receivables/Payables Aging", run_aging_review),
    "document_match": ("Support Document Matching", run_document_matching),
}


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _fmt_money(value: Any) -> str:
    try:
        if value is None:
            return "-"
        return f"₹{float(value):,.0f}"
    except Exception:
        return str(value)


def _format_audit_type(value: str) -> str:
    return str(value or "").replace("_", " ").title()


def _finding_blob(finding: Finding) -> str:
    return " ".join([
        str(finding.title or ""),
        str(finding.description or ""),
        str(finding.finding_type or ""),
        str(finding.risk_level or ""),
        str(finding.status or ""),
        str(finding.evidence or ""),
    ]).lower()


def _record_blob(record: ExtractedRecord) -> str:
    return " ".join([
        str(record.document_id or ""),
        str(record.party_name or ""),
        str(record.transaction_date or ""),
        str(record.amount or ""),
        str(record.gstin or ""),
        str(record.record_type or ""),
        str(record.raw_data or ""),
    ]).lower()


def _score_text(query_terms: list[str], blob: str) -> int:
    return sum(1 for term in query_terms if term and term in blob)


def retrieve_context(message: str, findings: list[Finding], records: list[ExtractedRecord]) -> dict[str, Any]:
    terms = [term for term in re_split_terms(message) if len(term) >= 3]

    scored_findings = []
    for finding in findings:
        score = _score_text(terms, _finding_blob(finding))
        if score > 0:
            scored_findings.append((score, finding))

    scored_records = []
    for record in records:
        score = _score_text(terms, _record_blob(record))
        if score > 0:
            scored_records.append((score, record))

    scored_findings.sort(key=lambda item: (item[0], item[1].id), reverse=True)
    scored_records.sort(key=lambda item: (item[0], item[1].id), reverse=True)

    return {
        "findings": [serialize_finding(finding) for _, finding in scored_findings[:8]],
        "records": [serialize_record(record) for _, record in scored_records[:8]],
    }


def re_split_terms(text: str) -> list[str]:
    cleaned = ""
    for ch in str(text or "").lower():
        cleaned += ch if ch.isalnum() else " "
    return [part.strip() for part in cleaned.split() if part.strip()]


def serialize_finding(finding: Finding) -> dict[str, Any]:
    evidence = finding.evidence or {}

    return {
        "id": finding.id,
        "audit_run_id": finding.audit_run_id,
        "type": finding.finding_type,
        "risk": finding.risk_level,
        "status": finding.status,
        "title": finding.title,
        "description": finding.description,
        "party": evidence.get("party_name") or evidence.get("books_party") or evidence.get("vendor") or "-",
        "document": evidence.get("document_id") or evidence.get("document_key") or "-",
        "amount": evidence.get("amount") or evidence.get("outstanding_amount") or evidence.get("books_amount"),
    }


def serialize_record(record: ExtractedRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "file_id": record.file_id,
        "record_type": record.record_type,
        "source_row": record.source_row,
        "document_id": record.document_id,
        "party_name": record.party_name,
        "transaction_date": record.transaction_date,
        "amount": record.amount,
        "gstin": record.gstin,
        "confidence": record.confidence,
    }


def infer_module_from_files(files: list[UploadedFile]) -> str:
    if not files:
        return "purchase"

    latest = sorted(files, key=lambda file: file.id, reverse=True)[0]
    file_type = _lower(latest.file_type)

    if "gstr" in file_type or "gst" in file_type:
        return "gst"
    if "bank" in file_type:
        return "bank"
    if "tds" in file_type:
        return "tds"
    if "fixed" in file_type or "asset" in file_type or "depreciation" in file_type:
        return "fixed_asset"
    if "trial" in file_type or "financial_statement" in file_type:
        return "trial_balance"
    if "aging" in file_type or "receivable" in file_type or "payable" in file_type or "outstanding" in file_type or "open_items" in file_type:
        return "aging"
    if "ocr" in file_type or "support" in file_type or "document" in file_type:
        return "document_match"
    if "sales" in file_type or "customer" in file_type:
        return "sales"
    if "expense" in file_type:
        return "expense"
    if "ledger" in file_type:
        return "ledger"

    return "purchase"


def detect_requested_module(message: str, files: list[UploadedFile]) -> str | None:
    text = _lower(message)

    if any(word in text for word in ["gst", "gstr", "2b", "itc"]):
        return "gst"
    if "bank" in text or "reconciliation" in text:
        return "bank"
    if "tds" in text or "pan" in text or "194" in text:
        return "tds"
    if "fixed asset" in text or "asset" in text or "depreciation" in text or "wdv" in text:
        return "fixed_asset"
    if "trial balance" in text or "balance sheet" in text or "financial statement" in text:
        return "trial_balance"
    if "aging" in text or "ageing" in text or "receivable" in text or "payable" in text or "outstanding" in text:
        return "aging"
    if "document" in text or "ocr" in text or "support" in text or "invoice match" in text or "matching" in text:
        return "document_match"
    if "sales" in text or "customer" in text:
        return "sales"
    if "expense" in text or "spend" in text:
        return "expense"
    if "ledger" in text or "scrutiny" in text or "journal" in text:
        return "ledger"
    if "purchase" in text or "vendor" in text or "bill" in text:
        return "purchase"

    if any(word in text for word in ["run audit", "audit this", "check this", "analyze this", "analyse this"]):
        return infer_module_from_files(files)

    return None


def summarize_workspace(files, records, findings, audit_runs) -> str:
    risk_counts = Counter(_lower(finding.risk_level) for finding in findings)
    status_counts = Counter(_lower(finding.status) for finding in findings)

    latest_run = audit_runs[0] if audit_runs else None

    lines = [
        f"Workspace summary:",
        f"- Files: {len(files)}",
        f"- Extracted records: {len(records)}",
        f"- Audit runs: {len(audit_runs)}",
        f"- Findings: {len(findings)}",
        f"- Risk split: High {risk_counts.get('high', 0)}, Medium {risk_counts.get('medium', 0)}, Low {risk_counts.get('low', 0)}",
        f"- Review status: Needs review {status_counts.get('needs_review', 0)}, Confirmed {status_counts.get('confirmed_issue', 0)}, Clarification {status_counts.get('needs_client_clarification', 0)}, Resolved {status_counts.get('resolved', 0)}",
    ]

    if latest_run:
        lines.append(
            f"- Latest run: {_format_audit_type(latest_run.audit_type)} #{latest_run.id}, "
            f"{latest_run.issues_found} issues, status {latest_run.status}"
        )

    return "\n".join(lines)


def summarize_findings(findings: list[Finding], only_open: bool = False, only_high: bool = False) -> str:
    selected = findings

    if only_open:
        selected = [
            finding for finding in selected
            if finding.status not in {"resolved", "false_positive"}
        ]

    if only_high:
        selected = [
            finding for finding in selected
            if _lower(finding.risk_level) == "high"
        ]

    if not selected:
        return "No matching findings found."

    risk_counts = Counter(_lower(finding.risk_level) for finding in selected)
    status_counts = Counter(_lower(finding.status) for finding in selected)
    type_counts = Counter(finding.finding_type for finding in selected)

    top_types = type_counts.most_common(5)

    lines = [
        f"Found {len(selected)} matching findings.",
        f"- Risk split: High {risk_counts.get('high', 0)}, Medium {risk_counts.get('medium', 0)}, Low {risk_counts.get('low', 0)}",
        f"- Open review: {status_counts.get('needs_review', 0)} needs review, {status_counts.get('needs_client_clarification', 0)} needs clarification",
        "- Top issue types:",
    ]

    for issue_type, count in top_types:
        lines.append(f"  - {_format_audit_type(issue_type)}: {count}")

    lines.append("")
    lines.append("Top findings:")

    for finding in selected[:8]:
        evidence = finding.evidence or {}
        party = evidence.get("party_name") or evidence.get("books_party") or "-"
        doc = evidence.get("document_id") or evidence.get("document_key") or "-"
        amount = evidence.get("amount") or evidence.get("outstanding_amount") or evidence.get("books_amount")
        lines.append(
            f"- [{finding.risk_level.upper()}] {finding.title} | Party: {party} | Doc: {doc} | Amount: {_fmt_money(amount)} | Status: {_format_audit_type(finding.status)}"
        )

    return "\n".join(lines)


def vendor_concentration(findings: list[Finding]) -> str:
    counter = Counter()

    for finding in findings:
        evidence = finding.evidence or {}
        party = (
            evidence.get("party_name")
            or evidence.get("books_party")
            or evidence.get("support_party")
            or evidence.get("vendor")
            or ""
        )
        party = str(party).strip()

        if party and party != "-":
            counter[party] += 1

    if not counter:
        return "I could not find vendor/party names inside the current findings evidence."

    lines = ["Vendors/parties with the most findings:"]
    for party, count in counter.most_common(10):
        lines.append(f"- {party}: {count} finding(s)")

    return "\n".join(lines)


def draft_clarification_list(findings: list[Finding]) -> str:
    candidates = [
        finding for finding in findings
        if finding.status in {"needs_review", "needs_client_clarification"} or finding.risk_level == "high"
    ]

    if not candidates:
        return "No open or high-risk findings available for a clarification draft."

    lines = [
        "Client clarification draft:",
        "",
        "Please clarify/provide supporting documents for the following audit observations:",
    ]

    for idx, finding in enumerate(candidates[:12], start=1):
        evidence = finding.evidence or {}
        party = evidence.get("party_name") or evidence.get("books_party") or "-"
        doc = evidence.get("document_id") or evidence.get("document_key") or "-"
        amount = evidence.get("amount") or evidence.get("outstanding_amount") or evidence.get("books_amount")
        lines.append(
            f"{idx}. {finding.title} | Party: {party} | Reference: {doc} | Amount: {_fmt_money(amount)}"
        )

    return "\n".join(lines)


def build_export_links(workspace_id: int, api_base_url: str) -> list[dict[str, str]]:
    base = api_base_url.rstrip("/")
    return [
        {
            "label": "Download Findings CSV",
            "url": f"{base}/reports/{workspace_id}/findings.csv",
        },
        {
            "label": "Download Audit Report PDF",
            "url": f"{base}/reports/{workspace_id}/audit-report.pdf",
        },
    ]


def handle_audit_chat_message(workspace_id: int, message: str, db: Session, api_base_url: str) -> dict[str, Any]:
    text = _lower(message)

    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.workspace_id == workspace_id)
        .order_by(UploadedFile.id.desc())
        .all()
    )

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .order_by(ExtractedRecord.id.desc())
        .limit(2000)
        .all()
    )

    findings = (
        db.query(Finding)
        .filter(Finding.workspace_id == workspace_id)
        .order_by(Finding.id.desc())
        .all()
    )

    audit_runs = (
        db.query(AuditRun)
        .filter(AuditRun.workspace_id == workspace_id)
        .order_by(AuditRun.id.desc())
        .all()
    )

    actions: list[str] = []
    links: list[dict[str, str]] = []
    context = retrieve_context(message, findings, records)

    if any(word in text for word in ["export", "csv", "pdf", "report", "download"]):
        links = build_export_links(workspace_id, api_base_url)
        return {
            "answer": "I prepared the current export links for this workspace. These exports use the existing Reports endpoints.",
            "actions": ["Prepared CSV/PDF report links"],
            "links": links,
            "context": context,
        }

    if any(word in text for word in ["extract", "parse", "apply mapping", "reparse"]):
        force = any(word in text for word in ["force", "again", "reparse", "latest"])
        parse_summary = parse_workspace_files(workspace_id, db, force_reparse=force)
        actions.append("Parsed workspace files using saved mappings")
        return {
            "answer": "I extracted records using the saved column mappings. You can now run an audit module.",
            "actions": actions,
            "data": parse_summary,
            "context": context,
        }

    module_key = detect_requested_module(message, files)

    if module_key:
        label, runner = MODULE_RUNNERS[module_key]
        result = runner(workspace_id=workspace_id, db=db)
        actions.append(f"Ran {label}")

        return {
            "answer": (
                f"I ran {label}. "
                f"Status: {result.get('status')}. "
                f"Issues found: {result.get('coverage', {}).get('issues_found', 0)}. "
                f"Checked records: {result.get('coverage', {}).get('checked_records') or result.get('coverage', {}).get('purchase_records_checked') or result.get('coverage', {}).get('fixed_asset_records_checked') or result.get('coverage', {}).get('aging_records_checked') or result.get('coverage', {}).get('trial_balance_records_checked') or result.get('coverage', {}).get('document_match_records_checked') or 0}."
            ),
            "actions": actions,
            "data": result,
            "links": build_export_links(workspace_id, api_base_url),
            "context": context,
        }

    if any(phrase in text for phrase in ["vendor", "party", "supplier"]) and any(phrase in text for phrase in ["most", "top", "many", "concentration"]):
        return {
            "answer": vendor_concentration(findings),
            "actions": ["Grouped findings by vendor/party"],
            "context": context,
        }

    if any(phrase in text for phrase in ["clarification", "client list", "client query", "query list", "draft"]):
        return {
            "answer": draft_clarification_list(findings),
            "actions": ["Drafted client clarification list from open/high-risk findings"],
            "context": context,
        }

    if any(phrase in text for phrase in ["high risk", "high-risk", "serious"]):
        return {
            "answer": summarize_findings(findings, only_high=True),
            "actions": ["Retrieved high-risk findings"],
            "context": context,
        }

    if any(phrase in text for phrase in ["unresolved", "open", "pending", "needs review"]):
        return {
            "answer": summarize_findings(findings, only_open=True),
            "actions": ["Retrieved unresolved/open findings"],
            "context": context,
        }

    if any(phrase in text for phrase in ["summarize", "summary", "overview", "what happened", "status"]):
        return {
            "answer": summarize_workspace(files, records, findings, audit_runs),
            "actions": ["Summarized workspace audit state"],
            "context": context,
        }

    if context["findings"] or context["records"]:
        lines = [
            "I found relevant audit context for your question.",
            "",
        ]

        if context["findings"]:
            lines.append("Relevant findings:")
            for finding in context["findings"][:5]:
                lines.append(
                    f"- [{str(finding['risk']).upper()}] {finding['title']} | Status: {_format_audit_type(finding['status'])}"
                )

        if context["records"]:
            lines.append("")
            lines.append("Relevant records:")
            for record in context["records"][:5]:
                lines.append(
                    f"- {record.get('document_id') or '-'} | {record.get('party_name') or '-'} | {_fmt_money(record.get('amount'))} | {record.get('record_type')}"
                )

        return {
            "answer": "\n".join(lines),
            "actions": ["Retrieved matching findings/records"],
            "context": context,
        }

    return {
        "answer": (
            "I can help with audit actions and workspace questions. Try:\n"
            "- Run fixed asset audit\n"
            "- Summarize high-risk findings\n"
            "- Draft client clarification list\n"
            "- Which vendors have the most findings?\n"
            "- Export PDF and CSV\n"
            "- Extract records again"
        ),
        "actions": [],
        "context": context,
    }
