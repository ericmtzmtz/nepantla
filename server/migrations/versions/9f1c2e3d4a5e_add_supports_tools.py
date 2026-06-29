"""Add supports_tools column to models table

Revision ID: 9f1c2e3d4a5e
Revises: 80afc1137139
Create Date: 2026-06-29 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f1c2e3d4a5e"
down_revision: str | None = "80afc1137139"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("models",
        sa.Column("supports_tools", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")))
    op.alter_column("models", "supports_tools", server_default=None)


def downgrade() -> None:
    op.drop_column("models", "supports_tools")
