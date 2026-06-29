"""Add supports_embeddings column to models table

Revision ID: a3c5e2f8b1d0
Revises: 51b6b39a9bfb
Create Date: 2026-06-27 02:40:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3c5e2f8b1d0"
down_revision: str | None = "51b6b39a9bfb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("models",
        sa.Column("supports_embeddings", sa.Boolean(),
                  nullable=False, server_default=sa.text("false")))
    op.alter_column("models", "supports_embeddings", server_default=None)


def downgrade() -> None:
    op.drop_column("models", "supports_embeddings")
