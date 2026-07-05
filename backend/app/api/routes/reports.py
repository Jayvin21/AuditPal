from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.reports.report_generator import (
    generate_audit_pdf,
    generate_findings_csv,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{workspace_id}/findings.csv")
def export_findings_csv(workspace_id: int, db: Session = Depends(get_db)):
    try:
        csv_content = generate_findings_csv(workspace_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV export failed: {str(exc)}")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="auditpal_workspace_{workspace_id}_findings.csv"'
        },
    )


@router.get("/{workspace_id}/audit-report.pdf")
def export_audit_pdf(workspace_id: int, db: Session = Depends(get_db)):
    try:
        pdf_content = generate_audit_pdf(workspace_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF export failed: {str(exc)}")

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="auditpal_workspace_{workspace_id}_report.pdf"'
        },
    )