import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.file_column_mapping import FileColumnMapping
from app.models.uploaded_file import UploadedFile
from app.schemas.column_mapping import ColumnMappingSave
from app.services.extractors.tabular_extractor import preview_tabular_file

router = APIRouter(prefix="/column-mappings", tags=["Column Mappings"])


def get_uploaded_file_or_404(file_id: int, db: Session) -> UploadedFile:
    uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()

    if not uploaded_file:
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    return uploaded_file


@router.get("/file/{file_id}")
def get_column_mapping(file_id: int, db: Session = Depends(get_db)):
    uploaded_file = get_uploaded_file_or_404(file_id, db)

    file_path = os.path.join(settings.upload_dir, uploaded_file.stored_filename)

    try:
        preview = preview_tabular_file(file_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not preview file: {str(exc)}")

    saved = (
        db.query(FileColumnMapping)
        .filter(FileColumnMapping.file_id == file_id)
        .first()
    )

    return {
        "file_id": uploaded_file.id,
        "workspace_id": uploaded_file.workspace_id,
        "file_type": uploaded_file.file_type,
        "available_columns": preview["available_columns"],
        "detected_mapping": preview["detected_mapping"],
        "saved_mapping": saved.mapping if saved else None,
        "preview_rows": preview["preview_rows"],
    }


@router.post("/file/{file_id}")
def save_column_mapping(file_id: int, payload: ColumnMappingSave, db: Session = Depends(get_db)):
    uploaded_file = get_uploaded_file_or_404(file_id, db)

    file_path = os.path.join(settings.upload_dir, uploaded_file.stored_filename)

    try:
        preview = preview_tabular_file(file_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not preview file: {str(exc)}")

    allowed_columns = set(preview["available_columns"])
    cleaned_mapping = {}

    for field, column in payload.mapping.items():
        if column is None or column == "":
            cleaned_mapping[field] = None
        elif column in allowed_columns:
            cleaned_mapping[field] = column
        else:
            raise HTTPException(status_code=400, detail=f"Invalid column selected: {column}")

    existing = (
        db.query(FileColumnMapping)
        .filter(FileColumnMapping.file_id == file_id)
        .first()
    )

    if existing:
        existing.mapping = cleaned_mapping
        existing.detected_mapping = preview["detected_mapping"]
        existing.available_columns = preview["available_columns"]
        existing.preview_rows = preview["preview_rows"]
    else:
        existing = FileColumnMapping(
            workspace_id=uploaded_file.workspace_id,
            file_id=uploaded_file.id,
            mapping=cleaned_mapping,
            detected_mapping=preview["detected_mapping"],
            available_columns=preview["available_columns"],
            preview_rows=preview["preview_rows"],
        )
        db.add(existing)

    uploaded_file.status = "mapped"
    db.commit()

    return {
        "message": "Column mapping saved",
        "file_id": uploaded_file.id,
        "mapping": cleaned_mapping,
    }