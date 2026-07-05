from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit_run import AuditRun
from app.models.finding import Finding

router = APIRouter(prefix="/audit-runs", tags=["Audit Runs"])


@router.post("/{workspace_id}/run-demo")
def run_demo_audit(workspace_id: int, db: Session = Depends(get_db)):
    audit_run = AuditRun(
        workspace_id=workspace_id,
        audit_type="purchase_audit",
        total_records=120,
        checked_records=94,
        issues_found=4,
        unchecked_records=26,
    )
    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    demo_findings = [
        Finding(
            workspace_id=workspace_id,
            audit_run_id=audit_run.id,
            finding_type="missing_proof",
            risk_level="high",
            title="Invoice exists in register but proof is missing",
            description="Purchase entry INV-1042 exists in the purchase register, but no matching uploaded invoice proof was found.",
            evidence={
                "invoice_no": "INV-1042",
                "vendor": "Raj Traders",
                "amount": 48500,
                "source": "purchase_register.xlsx",
                "row": 42,
            },
        ),
        Finding(
            workspace_id=workspace_id,
            audit_run_id=audit_run.id,
            finding_type="amount_mismatch",
            risk_level="medium",
            title="Amount mismatch between invoice and register",
            description="Invoice amount and purchase register amount differ by ₹180.",
            evidence={
                "invoice_no": "MS-184",
                "invoice_amount": 18420,
                "register_amount": 18240,
                "difference": 180,
            },
        ),
        Finding(
            workspace_id=workspace_id,
            audit_run_id=audit_run.id,
            finding_type="duplicate_invoice",
            risk_level="high",
            title="Duplicate invoice suspected",
            description="Same vendor, invoice number, and amount found more than once.",
            evidence={
                "invoice_no": "RT-778",
                "vendor": "Raj Traders",
                "amount": 32500,
                "rows": [88, 113],
            },
        ),
        Finding(
            workspace_id=workspace_id,
            audit_run_id=audit_run.id,
            finding_type="low_confidence_ocr",
            risk_level="low",
            title="Low confidence document extraction",
            description="The uploaded bill image was readable only partially and needs manual verification.",
            evidence={
                "file": "bill_45.jpg",
                "field": "amount",
                "confidence": 0.62,
            },
        ),
    ]

    db.add_all(demo_findings)
    db.commit()

    return {
        "audit_run_id": audit_run.id,
        "message": "Demo audit completed",
        "summary": {
            "total_records": audit_run.total_records,
            "checked_records": audit_run.checked_records,
            "issues_found": audit_run.issues_found,
            "unchecked_records": audit_run.unchecked_records,
        },
    }
