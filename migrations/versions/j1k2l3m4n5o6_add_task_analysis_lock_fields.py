"""add task analysis lock fields to assessments

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-08-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i0j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("task_analysis_input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "assessments",
        sa.Column("task_analysis_generated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "task_analysis_generated_at")
    op.drop_column("assessments", "task_analysis_input_hash")
