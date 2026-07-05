from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)

    audit_type = Column(String, nullable=False)
    status = Column(String, default="completed")

    total_records = Column(Integer, default=0)
    checked_records = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    unchecked_records = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
