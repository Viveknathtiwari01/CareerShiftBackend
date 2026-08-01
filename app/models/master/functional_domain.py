import uuid
from typing import List
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import MasterBaseModel

class FunctionalDomain(MasterBaseModel):
    __tablename__ = "functional_domains"

    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    department: Mapped["Department"] = relationship("Department", back_populates="functional_domains")
    specializations: Mapped[List["Specialization"]] = relationship(
        "Specialization", back_populates="functional_domain", cascade="all, delete-orphan"
    )
