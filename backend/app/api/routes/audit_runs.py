from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit_run import AuditRun
from app.models.finding import Finding
from app.services.audit_engine.runner import (
    run_bank_reconciliation,
    run_expense_audit,
    run_purchase_audit,
    run_sales_audit,
)

router = APIRouter(prefix="/audit-runs", tags=["Audit Runs"])


@router.post("/{workspace_id}/run-purchase-audit")
def run_real_purchase_audit(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_purchase_audit(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Purchase audit failed: {str(exc)}")


@router.post("/{workspace_id}/run-sales-audit")
def run_real_sales_audit(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_sales_audit(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Sales audit failed: {str(exc)}")


@router.post("/{workspace_id}/run-expense-audit")
def run_real_expense_audit(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_expense_audit(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Expense audit failed: {str(exc)}")


@router.post("/{workspace_id}/run-bank-reconciliation")
def run_real_bank_reconciliation(workspace_id: int, db: Session = Depends(get_db)):
    try:
        return run_bank_reconciliation(workspace_id=workspace_id, db=db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Bank reconciliation failed: {str(exc)}")


@router.get("/{workspace_id}")
def list_audit_runs(workspace_id: int, db: Session = Depends(get_db)):
    runs = (
        db.query(AuditRun)
        .filter(AuditRun.workspace_id == workspace_id)
        .order_by(AuditRun.id.desc())
        .all()
    )

    response = []

    for run in runs:
        findings = db.query(Finding).filter(Finding.audit_run_id == run.id).all()

        status_counts = {
            "needs_review": 0,
            "confirmed_issue": 0,
            "false_positive": 0,
            "needs_client_clarification": 0,
            "resolved": 0,
        }

        risk_counts = {
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for finding in findings:
            status_counts[finding.status] = status_counts.get(finding.status, 0) + 1
            risk_counts[finding.risk_level] = risk_counts.get(finding.risk_level, 0) + 1

        response.append(
            {
                "id": run.id,
                "workspace_id": run.workspace_id,
                "audit_type": run.audit_type,
                "status": run.status,
                "total_records": run.total_records,
                "checked_records": run.checked_records,
                "issues_found": run.issues_found,
                "unchecked_records": run.unchecked_records,
                "created_at": run.created_at,
                "status_counts": status_counts,
                "risk_counts": risk_counts,
            }
        )

    return response


@router.delete("/{audit_run_id}")
def delete_audit_run(audit_run_id: int, db: Session = Depends(get_db)):
    run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Audit run not found")

    workspace_id = run.workspace_id

    db.query(Finding).filter(Finding.audit_run_id == audit_run_id).delete()
    db.delete(run)
    db.commit()

    return {
        "audit_run_id": audit_run_id,
        "workspace_id": workspace_id,
        "message": "Audit run and its findings deleted successfully",
    }
