import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import UUID

def get_utc_now():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass

class AuditMixin:
    """Provides common audit fields for all models."""
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)
    
    # User ID string or UUID to track who made changes. Keeping string for simplicity, or we can use UUID.
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # For optimistic locking / versioning
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # We could implement a SQLAlchemy mapper event to automatically increment version on update
