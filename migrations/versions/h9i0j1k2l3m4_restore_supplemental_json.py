"""restore supplemental_json on career_intelligence_reports

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-08-14 10:15:00.000000

Production ran f7a8b9c0d1e2 which dropped supplemental_json in favor of
overview_json / career_identity_json / action_plan_json, but the app model
still persists overview, career_identity, action_plan, competencies, and
daily_work inside supplemental_json.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "h9i0j1k2l3m4"
down_revision: Union[str, Sequence[str], None] = "g8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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

        # Backfill from split columns added by f7a8b9c0d1e2 when present.
        has_overview = "overview_json" in columns
        has_identity = "career_identity_json" in columns
        has_action = "action_plan_json" in columns
        if has_overview or has_identity or has_action:
            overview_expr = "COALESCE(overview_json, '{}'::jsonb)" if has_overview else "'{}'::jsonb"
            identity_expr = (
                "COALESCE(career_identity_json, '{}'::jsonb)" if has_identity else "'{}'::jsonb"
            )
            action_expr = "COALESCE(action_plan_json, '{}'::jsonb)" if has_action else "'{}'::jsonb"
            op.execute(
                sa.text(
                    f"""
                    UPDATE career_intelligence_reports
                    SET supplemental_json = jsonb_build_object(
                        'overview', {overview_expr},
                        'career_identity', {identity_expr},
                        'action_plan', {action_expr},
                        'competencies', '[]'::jsonb,
                        'daily_work', '{{}}'::jsonb
                    )
                    """
                )
            )

        op.alter_column("career_intelligence_reports", "supplemental_json", server_default=None)

    for column in ("overview_json", "career_identity_json", "action_plan_json"):
        if column in columns:
            op.drop_column("career_intelligence_reports", column)


def downgrade() -> None:
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
        op.execute(
            sa.text(
                """
                UPDATE career_intelligence_reports
                SET
                    overview_json = COALESCE(supplemental_json->'overview', '{}'::jsonb),
                    career_identity_json = COALESCE(supplemental_json->'career_identity', '{}'::jsonb),
                    action_plan_json = COALESCE(supplemental_json->'action_plan', '{}'::jsonb)
                """
            )
        )
        op.drop_column("career_intelligence_reports", "supplemental_json")
