from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.audit_chat_service import handle_audit_chat_message


router = APIRouter(prefix="/audit-chat", tags=["Audit Chat"])


class AuditChatRequest(BaseModel):
    message: str


@router.post("/{workspace_id}/message")
def audit_chat_message(
    workspace_id: int,
    payload: AuditChatRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    try:
        api_base_url = str(request.base_url).rstrip("/")
        return handle_audit_chat_message(
            workspace_id=workspace_id,
            message=payload.message,
            db=db,
            api_base_url=api_base_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Audit chat failed: {str(exc)}")
