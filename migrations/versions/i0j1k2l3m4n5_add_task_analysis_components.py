"""add components column to assessment_task_analysis

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-08-22 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "i0j1k2l3m4n5"
down_revision: Union[str, Sequence[str], None] = "8a3e29025104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_task_analysis",
        sa.Column(
            "components",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("assessment_task_analysis", "components")
