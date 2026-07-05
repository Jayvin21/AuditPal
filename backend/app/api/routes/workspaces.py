import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.audit_run import AuditRun
from app.models.extracted_record import ExtractedRecord
from app.models.file_column_mapping import FileColumnMapping
from app.models.finding import Finding
from app.models.uploaded_file import UploadedFile
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)):
    workspace = Workspace(
        client_name=payload.client_name,
        audit_period=payload.audit_period,
        audit_type=payload.audit_type,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(db: Session = Depends(get_db)):
    return db.query(Workspace).order_by(Workspace.id.desc()).all()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return workspace


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    uploaded_files = (
        db.query(UploadedFile)
        .filter(UploadedFile.workspace_id == workspace_id)
        .all()
    )

    deleted_physical_files = 0

    for uploaded_file in uploaded_files:
        stored_filename = getattr(uploaded_file, "stored_filename", None)

        if stored_filename:
            file_path = os.path.join(settings.upload_dir, stored_filename)

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_physical_files += 1
            except OSError:
                pass

    db.query(Finding).filter(Finding.workspace_id == workspace_id).delete(synchronize_session=False)
    db.query(ExtractedRecord).filter(ExtractedRecord.workspace_id == workspace_id).delete(synchronize_session=False)
    db.query(FileColumnMapping).filter(FileColumnMapping.workspace_id == workspace_id).delete(synchronize_session=False)
    db.query(AuditRun).filter(AuditRun.workspace_id == workspace_id).delete(synchronize_session=False)
    db.query(UploadedFile).filter(UploadedFile.workspace_id == workspace_id).delete(synchronize_session=False)

    db.delete(workspace)
    db.commit()

    return {
        "message": "Workspace deleted",
        "workspace_id": workspace_id,
        "physical_files_deleted": deleted_physical_files,
    }
