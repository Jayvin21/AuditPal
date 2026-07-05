from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse, FindingUpdate

router = APIRouter(prefix="/findings", tags=["Findings"])

ALLOWED_STATUSES = {
    "needs_review",
    "confirmed_issue",
    "false_positive",
    "needs_client_clarification",
    "resolved",
}


@router.get("/{workspace_id}")
def list_findings(
    workspace_id: int,
    audit_run_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Finding).filter(Finding.workspace_id == workspace_id)

    if audit_run_id is not None:
        query = query.filter(Finding.audit_run_id == audit_run_id)

    findings = query.order_by(Finding.id.desc()).all()

    return [
        {
            "id": finding.id,
            "workspace_id": finding.workspace_id,
            "audit_run_id": finding.audit_run_id,
            "finding_type": finding.finding_type,
            "risk_level": finding.risk_level,
            "title": finding.title,
            "description": finding.description,
            "source_record_id": finding.source_record_id,
            "matched_record_id": finding.matched_record_id,
            "evidence": finding.evidence,
            "status": finding.status,
            "reviewer_note": finding.reviewer_note,
            "created_at": finding.created_at,
        }
        for finding in findings
    ]


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(finding_id: int, payload: FindingUpdate, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if payload.status is not None:
        if payload.status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid finding status")
        finding.status = payload.status

    if payload.reviewer_note is not None:
        finding.reviewer_note = payload.reviewer_note

    db.commit()
    db.refresh(finding)
    return finding
