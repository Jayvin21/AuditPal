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
from app.services.audit_engine.checks.gst_reco_checks import run_gst_reconciliation_checks
from app.services.audit_engine.checks.ledger_scrutiny_checks import run_ledger_scrutiny_checks
from app.services.audit_engine.checks.tds_checks import run_tds_checks
from app.services.audit_engine.checks.fixed_asset_checks import run_fixed_asset_checks
from app.services.audit_engine.checks.trial_balance_checks import run_trial_balance_checks
from app.services.audit_engine.checks.aging_checks import run_aging_checks
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


GST_BOOK_FILE_TYPES = {
    "purchase_register",
    "purchase",
    "purchase_ledger",
    "tally_purchase_register",
    "sap_vendor_line_items",
}

GSTR_2B_FILE_TYPES = {
    "gstr_2b",
    "gst_2b",
    "gstr2b",
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


LEDGER_SCRUTINY_FILE_TYPES = {
    "ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "cash_bank_ledger",
    "bank_ledger",
    "trial_balance",
}


TDS_FILE_TYPES = {
    "tds_ledger",
    "expense_ledger",
    "tally_ledger_vouchers",
    "sap_gl_line_items",
    "sap_vendor_line_items",
    "purchase_register",
    "tally_purchase_register",
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


def run_aging_review(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    aging_records = [
        record for record in records
        if record.record_type.lower() in AGING_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not aging_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="aging_review",
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
            "message": "Aging review needs receivables/payables aging or open-item files.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "aging_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_aging_checks(aging_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="aging_review",
        status="completed",
        total_records=len(aging_records),
        checked_records=len(aging_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(aging_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Aging review completed using uploaded receivable/payable records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "aging_records_checked": len(aging_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_trial_balance_review(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    trial_balance_records = [
        record for record in records
        if record.record_type.lower() in TRIAL_BALANCE_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not trial_balance_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="trial_balance_review",
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
            "message": "Trial balance review needs a trial_balance, Tally trial balance, SAP trial balance, or financial statement file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "trial_balance_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_trial_balance_checks(trial_balance_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="trial_balance_review",
        status="completed",
        total_records=len(trial_balance_records),
        checked_records=len(trial_balance_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(trial_balance_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Trial balance review completed using uploaded trial balance records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "trial_balance_records_checked": len(trial_balance_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_fixed_asset_audit(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    fixed_asset_records = [
        record for record in records
        if record.record_type.lower() in FIXED_ASSET_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not fixed_asset_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="fixed_asset_audit",
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
            "message": "Fixed asset audit needs a fixed asset register or depreciation schedule file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "fixed_asset_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_fixed_asset_checks(fixed_asset_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="fixed_asset_audit",
        status="completed",
        total_records=len(fixed_asset_records),
        checked_records=len(fixed_asset_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(fixed_asset_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Fixed asset audit completed using uploaded asset records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "fixed_asset_records_checked": len(fixed_asset_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_tds_review(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    tds_records = [
        record for record in records
        if record.record_type.lower() in TDS_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not tds_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="tds_review",
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
            "message": "TDS review needs expense/vendor/ledger records such as Tally Ledger Vouchers, SAP Vendor Line Items, or Expense Ledger.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "tds_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_tds_checks(tds_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="tds_review",
        status="completed",
        total_records=len(tds_records),
        checked_records=len(tds_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(tds_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "TDS review completed using uploaded records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "tds_records_checked": len(tds_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_ledger_scrutiny(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    ledger_records = [
        record for record in records
        if record.record_type.lower() in LEDGER_SCRUTINY_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not ledger_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="ledger_scrutiny",
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
            "message": "Ledger scrutiny needs ledger-style records such as Tally Ledger Vouchers, SAP G/L Line Items, Expense Ledger, or Trial Balance.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "ledger_records_checked": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_ledger_scrutiny_checks(ledger_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="ledger_scrutiny",
        status="completed",
        total_records=len(ledger_records),
        checked_records=len(ledger_records),
        issues_found=len(finding_payloads),
        unchecked_records=max(0, len(records) - len(ledger_records)),
    )

    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    save_findings(workspace_id, audit_run.id, finding_payloads, db)

    return {
        "audit_run_id": audit_run.id,
        "status": audit_run.status,
        "message": "Ledger scrutiny completed using uploaded ledger records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "ledger_records_checked": len(ledger_records),
            "unchecked_records": audit_run.unchecked_records,
            "issues_found": len(finding_payloads),
            "risk_counts": risk_counts(finding_payloads),
        },
    }


def run_gst_reconciliation(workspace_id: int, db: Session) -> dict:
    parse_summary = parse_workspace_files(workspace_id, db, force_reparse=False)

    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .all()
    )

    book_records = [
        record for record in records
        if record.record_type.lower() in GST_BOOK_FILE_TYPES
    ]

    gstr_2b_records = [
        record for record in records
        if record.record_type.lower() in GSTR_2B_FILE_TYPES
    ]

    clear_findings(workspace_id, db)

    if not book_records or not gstr_2b_records:
        audit_run = AuditRun(
            workspace_id=workspace_id,
            audit_type="gst_reconciliation",
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
            "message": "GST reconciliation needs one books purchase file and one GSTR-2B file.",
            "parse_summary": parse_summary,
            "coverage": {
                "total_records": len(records),
                "book_records": len(book_records),
                "gstr_2b_records": len(gstr_2b_records),
                "checked_records": 0,
                "unchecked_records": len(records),
                "issues_found": 0,
            },
        }

    finding_payloads = run_gst_reconciliation_checks(book_records, gstr_2b_records)
    checked_records = len(book_records) + len(gstr_2b_records)

    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="gst_reconciliation",
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
        "message": "GST reconciliation completed using books and GSTR-2B records",
        "parse_summary": parse_summary,
        "coverage": {
            "total_records": len(records),
            "book_records": len(book_records),
            "gstr_2b_records": len(gstr_2b_records),
            "checked_records": checked_records,
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

FIXED_ASSET_FILE_TYPES = {
    "fixed_asset_register",
    "fixed_assets",
    "asset_register",
    "depreciation_schedule",
    "sap_asset_register",
    "tally_fixed_assets",
}


TRIAL_BALANCE_FILE_TYPES = {
    "trial_balance",
    "tally_trial_balance",
    "sap_trial_balance",
    "financial_statement",
    "fs_trial_balance",
}


AGING_FILE_TYPES = {
    "receivables_aging",
    "payables_aging",
    "outstanding_receivables",
    "outstanding_payables",
    "debtors_aging",
    "creditors_aging",
    "tally_outstanding_receivables",
    "tally_outstanding_payables",
    "sap_customer_open_items",
    "sap_vendor_open_items",
}
