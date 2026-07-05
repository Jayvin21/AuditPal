from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class ExtractedRecord(Base):
    __tablename__ = "extracted_records"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False)

    record_type = Column(String, nullable=False)
    source_row = Column(Integer, nullable=True)

    document_id = Column(String, nullable=True)
    party_name = Column(String, nullable=True)
    transaction_date = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    gstin = Column(String, nullable=True)

    raw_data = Column(JSON, nullable=True)
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
