from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    client_name: str
    audit_period: str
    audit_type: str


class WorkspaceResponse(BaseModel):
    id: int
    client_name: str
    audit_period: str
    audit_type: str
    status: str

    class Config:
        from_attributes = True
