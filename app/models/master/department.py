import uuid
from typing import List
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import MasterBaseModel

class Department(MasterBaseModel):
    __tablename__ = "departments"

    sector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    sector: Mapped["Sector"] = relationship("Sector", back_populates="departments")
    functional_domains: Mapped[List["FunctionalDomain"]] = relationship(
        "FunctionalDomain", back_populates="department", cascade="all, delete-orphan"
    )
