import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, Index, text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database.base import Base, AuditMixin
from app.core.constants import (
    PIPELINE_STATUS_PENDING,
    PIPELINE_TYPE_COMPETENCY_MAPPING,
)


class Assessment(AuditMixin, Base):
    __tablename__ = "assessments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True
    )
    pipeline_type: Mapped[str] = mapped_column(
        String, nullable=False, default=PIPELINE_TYPE_COMPETENCY_MAPPING
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=PIPELINE_STATUS_PENDING
    )
    ai_toolkit_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    task_analysis_input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_analysis_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", backref="assessments")
    profile = relationship("UserProfile", backref="assessments")
    competency_mapping = relationship(
        "CareerCompetencyMapping",
        back_populates="assessment",
        uselist=False,
    )
    tasks = relationship(
        "AssessmentTask",
        back_populates="assessment",
        order_by="AssessmentTask.sort_order",
    )

    __table_args__ = (
        Index(
            "ix_assessments_user_active",
            "user_id",
            "status",
            postgresql_where=text("status IN ('PENDING', 'PROCESSING')"),
        ),
    )
