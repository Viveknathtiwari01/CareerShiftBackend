import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base, AuditMixin


class AssessmentTask(AuditMixin, Base):
    __tablename__ = "assessment_tasks"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hours_per_week: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    complexity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    creativity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    human_touch: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="AI_GENERATED")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    frequency: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_criticality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    time_allocation: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_assistance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment = relationship("Assessment", back_populates="tasks")
    analysis = relationship(
        "AssessmentTaskAnalysis",
        back_populates="task",
        uselist=False,
    )

    __table_args__ = (
        Index("ix_assessment_tasks_assessment_sort", "assessment_id", "sort_order"),
    )
