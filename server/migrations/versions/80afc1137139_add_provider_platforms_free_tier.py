# ruff: noqa: E501
"""add_provider_platforms_free_tier

Revision ID: 80afc1137139
Revises: 6f8f232c0a51
Create Date: 2026-06-28 14:07:27.881330
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '80afc1137139'
down_revision: str | None = '6f8f232c0a51'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('provider_platforms',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('timeout_ms', sa.Integer(), nullable=False, server_default=sa.text('30000')),
        sa.Column('extra_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_native', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('npm_package', sa.String(length=100), nullable=True),
        sa.Column('free_tier', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('models', sa.Column('free_tier', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('models', 'free_tier')
    op.drop_table('provider_platforms')
