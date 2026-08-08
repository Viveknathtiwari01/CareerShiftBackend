import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, AuditMixin


class CareerIntelligenceReport(AuditMixin, Base):
    __tablename__ = "career_intelligence_reports"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    ai_readiness_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    task_routing_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    before_after_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    upskill_roadmap_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ai_toolkit_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cost_roi_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    market_urgency_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    overview_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    career_identity_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    action_plan_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    strategic_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    assessment = relationship("Assessment", backref="career_intelligence_report")
