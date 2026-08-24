"""fix missing columns

Revision ID: 8548504f2797
Revises: j1k2l3m4n5o6
Create Date: 2026-08-23 10:40:56.014893

Align assessment_task_analysis with the app model and remove the
assessment_three_b_results table when present. Uses inspector checks so
production (which never had the three_b table or dev-only columns) can
apply this revision safely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8548504f2797'
down_revision: Union[str, Sequence[str], None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSONB_LIST_DEFAULT = sa.text("'[]'::jsonb")

_TARGET_COLUMNS: dict[str, sa.Column] = {
    "next_actions": sa.Column(
        "next_actions",
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=_JSONB_LIST_DEFAULT,
        nullable=False,
    ),
    "auto_potential": sa.Column("auto_potential", sa.Integer(), nullable=True),
    "risk_level": sa.Column("risk_level", sa.String(length=16), nullable=True),
    "future_impact": sa.Column("future_impact", sa.String(length=16), nullable=True),
    "recommended_tools": sa.Column(
        "recommended_tools",
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=_JSONB_LIST_DEFAULT,
        nullable=False,
    ),
    "components": sa.Column(
        "components",
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=_JSONB_LIST_DEFAULT,
        nullable=False,
    ),
}

_DEV_ONLY_COLUMNS = (
    "cost_of_staying_as_is_json",
    "learning_implication_json",
    "pace_of_change",
    "action_status",
    "action_updated_at",
    "pipeline_run_id",
    "components_json",
)


def _task_analysis_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns("assessment_task_analysis")}


def _drop_three_b_results() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "assessment_three_b_results" not in inspector.get_table_names():
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("assessment_three_b_results")}
    index_name = op.f("ix_assessment_three_b_results_assessment_id")
    if index_name in indexes:
        op.drop_index(index_name, table_name="assessment_three_b_results")

    op.drop_table("assessment_three_b_results")


def upgrade() -> None:
    _drop_three_b_results()

    columns = _task_analysis_columns()

    if "components_json" in columns and "components" not in columns:
        op.alter_column(
            "assessment_task_analysis",
            "components_json",
            new_column_name="components",
        )
        columns.remove("components_json")
        columns.add("components")

    for name, column in _TARGET_COLUMNS.items():
        if name not in columns:
            op.add_column("assessment_task_analysis", column)
            if column.server_default is not None:
                op.alter_column("assessment_task_analysis", name, server_default=None)

    columns = _task_analysis_columns()
    for name in _DEV_ONLY_COLUMNS:
        if name in columns:
            op.drop_column("assessment_task_analysis", name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _task_analysis_columns()

    for name in _DEV_ONLY_COLUMNS:
        if name in columns:
            continue
        if name == "components_json":
            op.add_column(
                "assessment_task_analysis",
                sa.Column(
                    "components_json",
                    postgresql.JSONB(astext_type=sa.Text()),
                    server_default=_JSONB_LIST_DEFAULT,
                    nullable=False,
                ),
            )
        elif name == "pipeline_run_id":
            op.add_column(
                "assessment_task_analysis",
                sa.Column("pipeline_run_id", sa.VARCHAR(length=64), nullable=True),
            )
        elif name == "action_updated_at":
            op.add_column(
                "assessment_task_analysis",
                sa.Column("action_updated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
            )
        elif name == "action_status":
            op.add_column(
                "assessment_task_analysis",
                sa.Column(
                    "action_status",
                    sa.VARCHAR(length=32),
                    server_default=sa.text("'NOT_STARTED'::character varying"),
                    nullable=False,
                ),
            )
        elif name == "pace_of_change":
            op.add_column(
                "assessment_task_analysis",
                sa.Column("pace_of_change", sa.VARCHAR(length=16), nullable=True),
            )
        elif name in {"learning_implication_json", "cost_of_staying_as_is_json"}:
            op.add_column(
                "assessment_task_analysis",
                sa.Column(name, postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )

    columns = _task_analysis_columns()
    if "components" in columns and "components_json" in columns:
        op.drop_column("assessment_task_analysis", "components")

    for name in _TARGET_COLUMNS:
        if name in columns:
            op.drop_column("assessment_task_analysis", name)

    if "assessment_three_b_results" not in inspector.get_table_names():
        op.create_table(
            "assessment_three_b_results",
            sa.Column("assessment_id", sa.UUID(), autoincrement=False, nullable=False),
            sa.Column("pipeline_run_id", sa.VARCHAR(length=64), autoincrement=False, nullable=False),
            sa.Column("pipeline_version", sa.VARCHAR(length=32), autoincrement=False, nullable=False),
            sa.Column("status", sa.VARCHAR(length=32), autoincrement=False, nullable=False),
            sa.Column("model_name", sa.VARCHAR(length=64), autoincrement=False, nullable=False),
            sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
            sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
            sa.Column("failed_stage", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
            sa.Column("error_message", sa.VARCHAR(length=1000), autoincrement=False, nullable=True),
            sa.Column("error_details", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
            sa.Column("hours_summary_json", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
            sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
            sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
            sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
            sa.Column("created_by", sa.VARCHAR(), autoincrement=False, nullable=True),
            sa.Column("updated_by", sa.VARCHAR(), autoincrement=False, nullable=True),
            sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
            sa.Column("is_deleted", sa.BOOLEAN(), autoincrement=False, nullable=False),
            sa.Column("version", sa.INTEGER(), autoincrement=False, nullable=False),
            sa.ForeignKeyConstraint(
                ["assessment_id"],
                ["assessments.id"],
                name=op.f("assessment_three_b_results_assessment_id_fkey"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("assessment_three_b_results_pkey")),
        )
        op.create_index(
            op.f("ix_assessment_three_b_results_assessment_id"),
            "assessment_three_b_results",
            ["assessment_id"],
            unique=True,
        )
