from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/{workspace_id}", response_model=list[FindingResponse])
def list_findings(workspace_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Finding)
        .filter(Finding.workspace_id == workspace_id)
        .order_by(Finding.id.desc())
        .all()
    )


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