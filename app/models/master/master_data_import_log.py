from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import MasterBaseModel
from datetime import datetime

class MasterDataImportLog(MasterBaseModel):
    __tablename__ = "master_data_import_logs"

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[float | None] = mapped_column(nullable=True) # in seconds
    status: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'SUCCESS', 'FAILED', 'PARTIAL'
    
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inserted_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
