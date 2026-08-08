"""align career_intelligence_reports columns with model

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-08-08 23:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("career_intelligence_reports")}

    if "overview_json" not in columns:
        op.add_column(
            "career_intelligence_reports",
            sa.Column(
                "overview_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        op.alter_column("career_intelligence_reports", "overview_json", server_default=None)

    if "career_identity_json" not in columns:
        op.add_column(
            "career_intelligence_reports",
            sa.Column(
                "career_identity_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        op.alter_column("career_intelligence_reports", "career_identity_json", server_default=None)

    if "action_plan_json" not in columns:
        op.add_column(
            "career_intelligence_reports",
            sa.Column(
                "action_plan_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        op.alter_column("career_intelligence_reports", "action_plan_json", server_default=None)

    if "supplemental_json" in columns:
        op.drop_column("career_intelligence_reports", "supplemental_json")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("career_intelligence_reports")}

    if "supplemental_json" not in columns:
        op.add_column(
            "career_intelligence_reports",
            sa.Column(
                "supplemental_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        op.alter_column("career_intelligence_reports", "supplemental_json", server_default=None)

    for column in ("action_plan_json", "career_identity_json", "overview_json"):
        if column in columns:
            op.drop_column("career_intelligence_reports", column)
