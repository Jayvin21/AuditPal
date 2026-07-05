import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
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

    extension = os.path.splitext(file.filename)[1]
    stored_filename = f"{uuid4().hex}{extension}"
    file_path = os.path.join(settings.upload_dir, stored_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

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
