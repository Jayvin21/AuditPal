from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit_run import AuditRun
from app.services.audit_engine.runner import run_bank_reconciliation, run_expense_audit, run_purchase_audit, run_sales_audit

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

    return [
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
        }
        for run in runs
    ]