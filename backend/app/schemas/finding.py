from pydantic import BaseModel
from typing import Any


class FindingResponse(BaseModel):
    id: int
    finding_type: str
    risk_level: str
    title: str
    description: str
    evidence: dict[str, Any] | None
    status: str
    reviewer_note: str | None

    class Config:
        from_attributes = True


class FindingUpdate(BaseModel):
    status: str | None = None
    reviewer_note: str | None = None