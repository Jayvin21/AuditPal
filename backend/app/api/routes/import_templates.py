from fastapi import APIRouter, HTTPException
from app.services.import_templates import get_import_template, get_import_templates

router = APIRouter(prefix="/import-templates", tags=["import-templates"])


@router.get("")
def list_import_templates():
    return get_import_templates()


@router.get("/{template_key}")
def read_import_template(template_key: str):
    template = get_import_template(template_key)
    if not template:
        raise HTTPException(status_code=404, detail="Import template not found")
    return template
