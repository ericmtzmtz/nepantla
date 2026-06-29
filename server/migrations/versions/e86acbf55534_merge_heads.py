"""merge_heads

Revision ID: e86acbf55534
Revises: 9f1c2e3d4a5e, add_hourly_agg_unique_index
Create Date: 2026-06-28 22:59:42.754990
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e86acbf55534'
down_revision: Union[str, None] = ('9f1c2e3d4a5e', 'add_hourly_agg_unique_index')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
