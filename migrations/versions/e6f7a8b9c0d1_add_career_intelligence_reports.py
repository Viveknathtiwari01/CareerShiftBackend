"""add career_intelligence_reports

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-08 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "career_intelligence_reports",
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("ai_readiness_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("task_routing_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("before_after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("upskill_roadmap_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_toolkit_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cost_roi_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("market_urgency_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overview_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("career_identity_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strategic_note", sa.Text(), nullable=True),
        sa.Column("report_version", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id"),
    )
    op.create_index(
        "ix_career_intelligence_reports_assessment_id",
        "career_intelligence_reports",
        ["assessment_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_career_intelligence_reports_assessment_id", table_name="career_intelligence_reports")
    op.drop_table("career_intelligence_reports")
