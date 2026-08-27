import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database.base import Base, AuditMixin


class AssessmentTaskAnalysis(AuditMixin, Base):
    __tablename__ = "assessment_task_analysis"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_tasks.id"), nullable=False, unique=True, index=True
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    rationale: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    auto_potential: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    future_impact: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recommended_tools: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    components: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    importance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    feasibility_tier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feasibility_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_capability: Mapped[str | None] = mapped_column(Text, nullable=True)
    velocity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    velocity_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    learn_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    learn_do: Mapped[str | None] = mapped_column(Text, nullable=True)
    learn_dont: Mapped[str | None] = mapped_column(Text, nullable=True)
    where_to_learn: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    task = relationship("AssessmentTask", back_populates="analysis")

    __table_args__ = (
        Index("ix_task_analysis_task_id", "task_id"),
    )
