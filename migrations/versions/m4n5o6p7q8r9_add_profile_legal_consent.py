"""add profile legal consent fields

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-09-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, Sequence[str], None] = "l3m4n5o6p7q8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("terms_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "user_profiles",
        sa.Column("privacy_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "user_profiles",
        sa.Column("consent_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "consent_accepted_at")
    op.drop_column("user_profiles", "privacy_accepted")
    op.drop_column("user_profiles", "terms_accepted")
