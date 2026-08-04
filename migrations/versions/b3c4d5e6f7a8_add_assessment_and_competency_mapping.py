"""add_assessment_and_competency_mapping

Revision ID: b3c4d5e6f7a8
Revises: a12688da587f
Create Date: 2026-08-04 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a12688da587f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("pipeline_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["user_profiles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessments_profile_id"), "assessments", ["profile_id"], unique=False)
    op.create_index(op.f("ix_assessments_user_id"), "assessments", ["user_id"], unique=False)
    op.create_index(
        "ix_assessments_user_active",
        "assessments",
        ["user_id", "status"],
        unique=False,
        postgresql_where=sa.text("status IN ('PENDING', 'PROCESSING')"),
    )

    op.create_table(
        "career_competency_mapping",
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("role_understanding_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("competency_discovery_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("competency_structuring_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("competency_validation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("competency_explanation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pipeline_run_id", sa.UUID(), nullable=False),
        sa.Column("pipeline_version", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_duration_seconds", sa.Float(), nullable=True),
        sa.Column("engine_metrics", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("prompt_versions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("failed_stage", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
    )
    op.create_index(
        op.f("ix_career_competency_mapping_assessment_id"),
        "career_competency_mapping",
        ["assessment_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_career_competency_mapping_pipeline_run_id"),
        "career_competency_mapping",
        ["pipeline_run_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_career_competency_mapping_pipeline_run_id"), table_name="career_competency_mapping")
    op.drop_index(op.f("ix_career_competency_mapping_assessment_id"), table_name="career_competency_mapping")
    op.drop_table("career_competency_mapping")
    op.drop_index("ix_assessments_user_active", table_name="assessments")
    op.drop_index(op.f("ix_assessments_user_id"), table_name="assessments")
    op.drop_index(op.f("ix_assessments_profile_id"), table_name="assessments")
    op.drop_table("assessments")
