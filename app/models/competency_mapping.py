import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, ForeignKey, Text, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.base import Base, AuditMixin
from app.core.constants import PIPELINE_STATUS_PENDING


class CareerCompetencyMapping(AuditMixin, Base):
    __tablename__ = "career_competency_mapping"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Internal stage outputs
    role_understanding_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    competency_discovery_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    competency_structuring_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    competency_validation_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    competency_explanation_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Frontend-ready assembled output
    final_output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Pipeline metadata
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    pipeline_version: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metrics and prompt tracking
    engine_metrics: Mapped[dict[str, float]] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_versions: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)

    # Status and failure recovery
    status: Mapped[str] = mapped_column(String, nullable=False, default=PIPELINE_STATUS_PENDING)
    failed_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    assessment = relationship("Assessment", back_populates="competency_mapping")
