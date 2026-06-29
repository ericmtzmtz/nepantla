# ruff: noqa: E402, F403
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root so 'server' module can be imported
PROJECT_ROOT = Path(__file__).resolve().parent / ".." / ".."
sys.path.insert(0, str(PROJECT_ROOT))

from server.core.config import settings
from server.core.database import Base
from server.models import *  # noqa: F401, F403 — register all models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Use settings directly to avoid ConfigParser interpolation issues with special chars
    context.configure(
        url=settings.DATABASE_URL_SYNC,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Pass URL directly via dict (bypasses ConfigParser which mangles % in passwords)
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.DATABASE_URL_SYNC},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
