from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class FileColumnMapping(Base):
    __tablename__ = "file_column_mappings"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False, unique=True)
    mapping = Column(JSON, nullable=False)
    detected_mapping = Column(JSON, nullable=True)
    available_columns = Column(JSON, nullable=True)
    preview_rows = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())