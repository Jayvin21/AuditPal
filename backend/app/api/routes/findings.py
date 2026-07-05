from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.finding import Finding
from app.schemas.finding import FindingResponse

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("/{workspace_id}", response_model=list[FindingResponse])
def list_findings(workspace_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Finding)
        .filter(Finding.workspace_id == workspace_id)
        .order_by(Finding.id.desc())
        .all()
    )
