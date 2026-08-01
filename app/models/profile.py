import uuid
from typing import List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import Base, AuditMixin

class UserProfile(AuditMixin, Base):
    __tablename__ = "user_profiles"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Career Identity
    job_title: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[str] = mapped_column(String, nullable=False)
    business_function: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    specialization: Mapped[str] = mapped_column(String, nullable=False)
    
    # Professional Background
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False)
    salary: Mapped[str | None] = mapped_column(String, nullable=True) # E.g., "$100k - $120k" or specific value
    
    # Skills Intelligence
    technical_skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    professional_skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    soft_skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    behavioural_skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    digital_skills: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    
    # AI Readiness
    ai_frequency: Mapped[str] = mapped_column(String, nullable=False)
    ai_tools: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    ai_comfort_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    user = relationship("User", back_populates="profile")
