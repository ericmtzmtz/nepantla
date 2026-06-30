"""make hourly_agg.id nullable, fix PK to composite (hour, type, platform, model_id)

Revision ID: 0779e8785210
Revises: e86acbf55534
Create Date: 2026-06-29 20:55:09.711815
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0779e8785210'
down_revision: Union[str, None] = 'e86acbf55534'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old PK on id, drop redundant unique index, create composite PK
    op.drop_constraint('hourly_agg_pkey', 'hourly_agg', type_='primary')
    op.drop_index(op.f('ix_hourly_agg_unique'), table_name='hourly_agg')
    op.create_primary_key('hourly_agg_pkey', 'hourly_agg', ['hour', 'type', 'platform', 'model_id'])
    op.alter_column('hourly_agg', 'id',
               existing_type=sa.UUID(),
               nullable=True)
    # RateLimitUsage.tokens should be NOT NULL per model
    op.alter_column('rate_limit_usage', 'tokens',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('0'))


def downgrade() -> None:
    # Reverse
    op.alter_column('rate_limit_usage', 'tokens',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('0'))
    op.alter_column('hourly_agg', 'id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_constraint('hourly_agg_pkey', 'hourly_agg', type_='primary')
    op.create_index(op.f('ix_hourly_agg_unique'), 'hourly_agg', ['hour', 'type', 'platform', 'model_id'], unique=True)
    op.create_primary_key('hourly_agg_pkey', 'hourly_agg', ['id'])
