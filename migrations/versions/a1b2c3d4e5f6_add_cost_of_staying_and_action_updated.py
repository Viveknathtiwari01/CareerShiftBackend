"""add cost_of_staying_as_is_json and action_updated_at

Revision ID: a1b2c3d4e5f6
Revises: 93368b0ba1e2
Create Date: 2026-08-27 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "93368b0ba1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_task_analysis",
        sa.Column(
            "cost_of_staying_as_is_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "assessment_task_analysis",
        sa.Column("action_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_task_analysis", "action_updated_at")
    op.drop_column("assessment_task_analysis", "cost_of_staying_as_is_json")
