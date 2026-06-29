"""fix_key_id_type: RateLimitUsage.key_id + RateLimitCooldown.key_id Integer -> UUID

Revision ID: 6f8f232c0a51
Revises: a3c5e2f8b1d0
Create Date: 2026-06-27 03:30:27.771631
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "6f8f232c0a51"
down_revision: str | None = "a3c5e2f8b1d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.drop_table("rate_limit_cooldowns")
    op.drop_table("rate_limit_usage")
    op.create_table("rate_limit_usage",
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("key_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("tokens", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table("rate_limit_cooldowns",
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("key_id", UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("platform", "model_id", "key_id"),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_cooldowns")
    op.drop_table("rate_limit_usage")
    op.create_table("rate_limit_usage",
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("key_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("tokens", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table("rate_limit_cooldowns",
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("key_id", sa.Integer(), nullable=False),
        sa.Column("expires_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("platform", "model_id", "key_id"),
    )
