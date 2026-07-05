from pydantic import BaseModel
from typing import Any


class ColumnMappingSave(BaseModel):
    mapping: dict[str, str | None]


class ColumnMappingResponse(BaseModel):
    file_id: int
    workspace_id: int
    available_columns: list[str]
    detected_mapping: dict[str, str]
    saved_mapping: dict[str, str | None] | None = None
    preview_rows: list[dict[str, Any]]