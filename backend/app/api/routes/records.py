from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.extracted_record import ExtractedRecord
from app.models.uploaded_file import UploadedFile
from app.services.audit_engine.runner import parse_uploaded_file, parse_workspace_files

router = APIRouter(prefix="/records", tags=["Records"])


@router.post("/parse-file/{file_id}")
def parse_file(
    file_id: int,
    force_reparse: bool = Query(False),
    db: Session = Depends(get_db),
):
    try:
        return parse_uploaded_file(file_id=file_id, db=db, force_reparse=force_reparse)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {str(exc)}")


@router.post("/parse-workspace/{workspace_id}")
def parse_workspace(
    workspace_id: int,
    force_reparse: bool = Query(False),
    db: Session = Depends(get_db),
):
    try:
        return parse_workspace_files(
            workspace_id=workspace_id,
            db=db,
            force_reparse=force_reparse,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse workspace files: {str(exc)}")


@router.get("/workspace/{workspace_id}")
def list_workspace_records(workspace_id: int, db: Session = Depends(get_db)):
    records = (
        db.query(ExtractedRecord)
        .filter(ExtractedRecord.workspace_id == workspace_id)
        .order_by(ExtractedRecord.id.desc())
        .all()
    )

    return [
        {
            "id": record.id,
            "file_id": record.file_id,
            "record_type": record.record_type,
            "source_row": record.source_row,
            "document_id": record.document_id,
            "party_name": record.party_name,
            "transaction_date": record.transaction_date,
            "amount": record.amount,
            "gstin": record.gstin,
            "confidence": record.confidence,
            "raw_data": record.raw_data,
        }
        for record in records
    ]


@router.get("/files/{workspace_id}")
def list_uploaded_files(workspace_id: int, db: Session = Depends(get_db)):
    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.workspace_id == workspace_id)
        .order_by(UploadedFile.id.desc())
        .all()
    )

    return [
        {
            "id": file.id,
            "workspace_id": file.workspace_id,
            "original_filename": file.original_filename,
            "file_type": file.file_type,
            "status": file.status,
            "created_at": file.created_at,
        }
        for file in files
    ]