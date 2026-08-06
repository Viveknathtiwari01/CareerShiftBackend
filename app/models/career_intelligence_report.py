import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database.base import Base, AuditMixin, get_utc_now


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
    supplemental_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    strategic_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    report_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )

    __table_args__ = (
        Index("ix_career_reports_assessment_id", "assessment_id"),
    )
