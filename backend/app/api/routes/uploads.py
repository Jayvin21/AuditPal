import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.audit_run import AuditRun
from app.models.extracted_record import ExtractedRecord
from app.models.file_column_mapping import FileColumnMapping
from app.models.finding import Finding
from app.models.uploaded_file import UploadedFile

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("")
def upload_file(
    workspace_id: int = Form(...),
    file_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    os.makedirs(settings.upload_dir, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    existing_file = (
        db.query(UploadedFile)
        .filter(
            UploadedFile.workspace_id == workspace_id,
            UploadedFile.original_filename == file.filename,
        )
        .first()
    )

    if existing_file:
        raise HTTPException(
            status_code=400,
            detail="Duplicate file name in this workspace. Delete the existing file or rename the new file before uploading.",
        )

    extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{uuid4().hex}{extension}"
    file_path = os.path.join(settings.upload_dir, stored_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {str(exc)}")

    uploaded = UploadedFile(
        workspace_id=workspace_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_type=file_type,
        status="uploaded",
    )

    db.add(uploaded)
    db.commit()
    db.refresh(uploaded)

    return {
        "id": uploaded.id,
        "workspace_id": uploaded.workspace_id,
        "original_filename": uploaded.original_filename,
        "file_type": uploaded.file_type,
        "status": uploaded.status,
    }


@router.delete("/{file_id}")
def delete_uploaded_file(file_id: int, db: Session = Depends(get_db)):
    uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()

    if not uploaded_file:
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    workspace_id = uploaded_file.workspace_id
    stored_filename = uploaded_file.stored_filename

    db.query(ExtractedRecord).filter(ExtractedRecord.file_id == file_id).delete()
    db.query(FileColumnMapping).filter(FileColumnMapping.file_id == file_id).delete()

    # Clear generated audit output because deleted source data can make old findings stale.
    db.query(Finding).filter(Finding.workspace_id == workspace_id).delete()
    db.query(AuditRun).filter(AuditRun.workspace_id == workspace_id).delete()

    db.delete(uploaded_file)
    db.commit()

    file_path = os.path.join(settings.upload_dir, stored_filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return {
        "file_id": file_id,
        "workspace_id": workspace_id,
        "message": "File and dependent audit data deleted successfully",
    }
