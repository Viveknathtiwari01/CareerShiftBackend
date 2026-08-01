from typing import List
from sqlalchemy import String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import MasterBaseModel

class Sector(MasterBaseModel):
    __tablename__ = "sectors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    isco_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_text: Mapped[str | None] = mapped_column(String, nullable=True)

    departments: Mapped[List["Department"]] = relationship(
        "Department", back_populates="sector", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_sectors_name', 'name'),
        Index('ix_sectors_search_text', 'search_text'),
    )
