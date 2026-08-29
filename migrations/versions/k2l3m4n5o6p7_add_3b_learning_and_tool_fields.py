"""add learn_future and learn_current to assessment_task_analysis

Revision ID: k2l3m4n5o6p7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_task_analysis",
        sa.Column("learn_future", sa.Text(), nullable=True),
    )
    op.add_column(
        "assessment_task_analysis",
        sa.Column("learn_current", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_task_analysis", "learn_current")
    op.drop_column("assessment_task_analysis", "learn_future")
