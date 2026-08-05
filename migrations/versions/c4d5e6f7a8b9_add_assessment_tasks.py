"""add_assessment_tasks

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-04 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_tasks",
        sa.Column("assessment_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("hours_per_week", sa.Float(), nullable=False, server_default="0"),
        sa.Column("complexity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("creativity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("human_touch", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="AI_GENERATED"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("frequency", sa.String(length=64), nullable=True),
        sa.Column("business_criticality", sa.String(length=64), nullable=True),
        sa.Column("time_allocation", sa.Float(), nullable=True),
        sa.Column("ai_assistance", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("manual_notes", sa.Text(), nullable=True),
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
        op.f("ix_assessment_tasks_assessment_id"),
        "assessment_tasks",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        "ix_assessment_tasks_assessment_sort",
        "assessment_tasks",
        ["assessment_id", "sort_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_tasks_assessment_sort", table_name="assessment_tasks")
    op.drop_index(op.f("ix_assessment_tasks_assessment_id"), table_name="assessment_tasks")
    op.drop_table("assessment_tasks")
