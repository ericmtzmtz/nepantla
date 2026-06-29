"""Add unique index on hourly_agg (hour, type, platform, model_id)

Revision ID: add_hourly_agg_unique_index
Revises: 80afc1137139
Create Date: 2026-06-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_hourly_agg_unique_index"
down_revision: str | None = "80afc1137139"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_hourly_agg_unique",
        "hourly_agg",
        ["hour", "type", "platform", "model_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_hourly_agg_unique", table_name="hourly_agg")
