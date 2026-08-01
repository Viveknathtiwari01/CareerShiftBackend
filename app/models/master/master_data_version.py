from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import MasterBaseModel
from datetime import datetime, timezone

def get_utc_now():
    return datetime.now(timezone.utc)

class MasterDataVersion(MasterBaseModel):
    __tablename__ = "master_data_versions"

    version: Mapped[str] = mapped_column(String(50), nullable=False)
    taxonomy_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    imported_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
