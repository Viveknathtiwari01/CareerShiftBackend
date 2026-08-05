"""add_assessment_task_analysis

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-04 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_task_analysis",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.String(length=500), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("next_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("auto_potential", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=True),
        sa.Column("future_impact", sa.String(length=16), nullable=True),
        sa.Column("recommended_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["assessment_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(
        "ix_task_analysis_task_id",
        "assessment_task_analysis",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_analysis_task_id", table_name="assessment_task_analysis")
    op.drop_table("assessment_task_analysis")
