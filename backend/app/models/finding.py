from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    audit_run_id = Column(Integer, ForeignKey("audit_runs.id"), nullable=True)

    finding_type = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)

    source_record_id = Column(Integer, ForeignKey("extracted_records.id"), nullable=True)
    matched_record_id = Column(Integer, ForeignKey("extracted_records.id"), nullable=True)

    evidence = Column(JSON, nullable=True)
    status = Column(String, default="needs_review")
    reviewer_note = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
