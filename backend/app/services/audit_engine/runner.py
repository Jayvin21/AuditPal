import os

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_run import AuditRun
from app.models.extracted_record import ExtractedRecord
from app.models.file_column_mapping import FileColumnMapping
from app.models.finding import Finding
from app.models.uploaded_file import UploadedFile
from app.services.audit_engine.checks.basic_purchase_checks import run_basic_purchase_checks
from app.services.audit_engine.checks.expense_checks import run_expense_checks
from app.services.audit_engine.checks.sales_checks import run_sales_checks
from app.services.audit_engine.checks.bank_reco_checks import run_bank_reconciliation_checks
from app.services.extractors.tabular_extractor import extract_tabular_file


PURCHASE_FILE_TYPES = {
    "purchase_register",
    "purchase",
    "purchase_ledger",
    "expense_ledger",
    "expenses",
}


EXPENSE_FILE_TYPES = {
    "expense_ledger",
    "expenses",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "tally_purchase_register",
}


SALES_FILE_TYPES = {
    "sales_register",
    "generic_sales_register",
    "sales",
    "sap_customer_line_items",
}

BANK_FILE_TYPES = {
    "bank_statement",
    "bank",
}

LEDGER_FILE_TYPES = {
    "cash_bank_ledger",
    "bank_ledger",
    "ledger",
    "tally_bank_book",
}


def parse_uploaded_file(file_id: int, db: Session, force_reparse: bool = False) -> dict:
    uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()

    if not uploaded_file:
        raise ValueError("Uploaded file not found")

    file_path = os.path.join(settings.upload_dir, uploaded_file.stored_filename)

    existing_records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.file_id == uploaded_file.id)
        .all()
    )

    if existing_records and not force_reparse:
        return {
            "file_id": uploaded_file.id,
            "message": "File already parsed",
            "records_extracted": len(existing_records),
            "metadata": {
                "status": "already_parsed",
            },
        }

    if existing_records and force_reparse:
        db.query(ExtractedRecord).filter(ExtractedRecord.file_id == uploaded_file.id).delete()
        db.commit()

    saved_mapping = (
        db.query(FileColumnMapping)
        .filter(FileColumnMapping.file_id == uploaded_file.id)
        .first()
    )

    user_mapping = saved_mapping.mapping if saved_mapping else None

    records_data, metadata = extract_tabular_file(
        file_path=file_path,
        file_id=uploaded_file.id,
        workspace_id=uploaded_file.workspace_id,
        record_type=uploaded_file.file_type,
        user_mapping=user_mapping,
    )

    records = [ExtractedRecord(**record_data) for record_data in records_data]

    db.add_all(records)
    uploaded_file.status = "parsed"
    db.commit()

    return {
        "file_id": uploaded_file.id,
        "message": "File parsed successfully",
        "records_extracted": len(records),
        "metadata": metadata,
    }


def parse_workspace_files(workspace_id: int, db: Session, force_reparse: bool = False) -> dict:
    uploaded_files = (
        db.query(UploadedFile)
        .filter(UploadedFile.workspace_id == workspace_id)
        .all()
    )

    results = []

    for uploaded_file in uploaded_files:
        extension = os.path.splitext(uploaded_file.original_filename)[1].lower()

        if extension not in [".xlsx", ".xls", ".csv"]:
            results.append({
                "file_id": uploaded_file.id,
                "filename": uploaded_file.original_filename,
                "status": "skipped",
                "reason": "Only Excel/CSV parsing is supported in this stage",
            })
            continue

        result = parse_uploaded_file(uploaded_file.id, db, force_reparse=force_reparse)
        results.append({
            "file_id": uploaded_file.id,
            "filename": uploaded_file.original_filename,
            "status": "parsed",
            "records_extracted": result["records_extracted"],
            "metadata": result["metadata"],
        })

    return {
        "workspace_id": workspace_id,
        "files_processed": len(results),
        "results": results,
    }


def clear_findings(workspace_id: int, db: Session):
    # Keep previous audit-run findings so review state/history is preserved.
    # Individual runs can be deleted from the Audit Runs history.
    return None


def save_findings(
    workspace_id: int,
    audit_run_id: int,
    finding_payloads: list[dict],
    db: Session,
):
    findings = [
        Finding(
            workspace_id=workspace_id,
            audit_run_id=audit_run_id,
            finding_type=payload["finding_type"],
            risk_level=payload["risk_level"],
            title=payload["title"],
            description=payload["description"],
            source_record_id=payload.get("source_record_id"),
            matched_record_id=payload.get("matched_record_id"),
            evidence=payload.get("evidence"),
        )
        for payload in finding_payloads
    ]

    db.add_all(findings)
    db.commit()


def risk_counts(finding_payloads: list[dict]) -> dict:
    counts = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for payload in finding_payloads:
        risk = payload["risk_level"]
        counts[risk] = counts.get(risk, 0) + 1

    return counts


def run_purchase_audit(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    purchase_records = [
        record for record in records
        if record.record_type.lower() in PURCHASE_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not purchase_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="purchase_audit",
            status="completed_with_limitations",
            total_records=len(records),
            checked_records=0,
            issues_found=0,
            unchecked_records=len(records),
        )
        db.add(audit_run)
        db.commit()
        db.refresh(audit_run)

        return {
            "audit_run_id": audit_run.id,
            "status": audit_run.status,
            "message": "No purchase records found. Upload a file tagged as purchase_register.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "purchase_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_basic_purchase_checks(purchase_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="purchase_audit",
        status="completed",
        total_records=len(purchase_records),
        checked_records=len(purchase_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(purchase_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Purchase audit completed using uploaded records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "purchase_records_checked": len(purchase_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_sales_audit(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    sales_records = [
        record for record in records
        if record.record_type.lower() in SALES_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not sales_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="sales_audit",
            status="completed_with_limitations",
            total_records=len(records),
            checked_records=0,
            issues_found=0,
            unchecked_records=len(records),
        )
        db.add(audit_run)
        db.commit()
        db.refresh(audit_run)

        return {
            "audit_run_id": audit_run.id,
            "status": audit_run.status,
            "message": "No sales records found. Upload a file tagged as generic_sales_register or sap_customer_line_items.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "sales_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_sales_checks(sales_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="sales_audit",
        status="completed",
        total_records=len(sales_records),
        checked_records=len(sales_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(sales_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Sales audit completed using uploaded sales records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "sales_records_checked": len(sales_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_expense_audit(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    expense_records = [
        record for record in records
        if record.record_type.lower() in EXPENSE_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not expense_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="expense_audit",
            status="completed_with_limitations",
            total_records=len(records),
            checked_records=0,
            issues_found=0,
            unchecked_records=len(records),
        )
        db.add(audit_run)
        db.commit()
        db.refresh(audit_run)

        return {
            "audit_run_id": audit_run.id,
            "status": audit_run.status,
            "message": "No expense records found. Upload a file tagged as expense_ledger, tally_ledger_vouchers, or sap_gl_line_items.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "expense_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_expense_checks(expense_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="expense_audit",
        status="completed",
        total_records=len(expense_records),
        checked_records=len(expense_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(expense_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Expense audit completed using uploaded ledger records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "expense_records_checked": len(expense_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_bank_reconciliation(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    bank_records = [
        record for record in records
        if record.record_type.lower() in BANK_FILE_TYPES
    ]

    ledger_records = [
        record for record in records
        if record.record_type.lower() in LEDGER_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not bank_records or not ledger_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="bank_reconciliation",
            status="completed_with_limitations",
            total_records=len(records),
            checked_records=0,
            issues_found=0,
            unchecked_records=len(records),
        )
        db.add(audit_run)
        db.commit()
        db.refresh(audit_run)

        return {
            "audit_run_id": audit_run.id,
            "status": audit_run.status,
            "message": "Bank reconciliation needs one bank_statement file and one cash_bank_ledger/bank_ledger file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "bank_records": len(bank_records),
                "ledger_records": len(ledger_records),
                "checked_records": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_bank_reconciliation_checks(bank_records, ledger_records)

    checked_records = len(bank_records) + len(ledger_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="bank_reconciliation",
        status="completed",
        total_records=checked_records,
        checked_records=checked_records,
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - checked_records),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Bank reconciliation completed using uploaded bank and ledger records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "bank_records": len(bank_records),
            "ledger_records": len(ledger_records),
            "checked_records": checked_records,
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }