import uuid
from typing import List
from sqlalchemy import String, Integer, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import MasterBaseModel

class Specialization(MasterBaseModel):
    __tablename__ = "specializations"

    functional_domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("functional_domains.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    specialization_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    onet: Mapped[str | None] = mapped_column(String(100), nullable=True)
    isco: Mapped[str | None] = mapped_column(String(100), nullable=True)
    esco: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_text: Mapped[str | None] = mapped_column(String, nullable=True)

    functional_domain: Mapped["FunctionalDomain"] = relationship("FunctionalDomain", back_populates="specializations")
    job_titles: Mapped[List["JobTitle"]] = relationship(
        "JobTitle", back_populates="specialization", cascade="all, delete-orphan"
    )
    skills: Mapped[List["Skill"]] = relationship(
        "Skill", back_populates="specialization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_specializations_name', 'name'),
        Index('ix_specializations_search_text', 'search_text'),
    )
