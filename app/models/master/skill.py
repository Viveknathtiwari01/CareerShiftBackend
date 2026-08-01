import uuid
from sqlalchemy import String, Integer, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import MasterBaseModel

class Skill(MasterBaseModel):
    __tablename__ = "skills"

    specialization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proficiency_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    roles: Mapped[str | None] = mapped_column(Text, nullable=True) # Could be JSON, storing as text for now
    transferability: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_impact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    future_trajectory: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_text: Mapped[str | None] = mapped_column(String, nullable=True)

    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="skills")

    __table_args__ = (
        Index('ix_skills_skill_name', 'skill_name'),
        Index('ix_skills_search_text', 'search_text'),
    )
