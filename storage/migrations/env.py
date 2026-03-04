"""Alembic environment configuration.

Reads sqlalchemy.url from config.settings.db_url so the same migrations
work for both SQLite (dev) and PostgreSQL (production).
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make project root importable when running `alembic` from the repo root
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config import settings
from storage.models import Base

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Set the DB URL from application settings (overrides any value in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.db_url)

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for --autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live connection).

    Useful for generating migration scripts to review or run manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (apply directly to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
