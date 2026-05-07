"""
Alembic environment configuration for the Azure Firewall Management application.

This module handles database connections and migration execution for Alembic.
It reads the database URL from the DATABASE_URL environment variable or
falls back to the URL configured in alembic.ini.
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the backend directory to the Python path for imports
# This allows alembic to find our models and database configuration
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import application configuration
from app.config import settings
from app.models import Base

# Import all models to ensure they're registered with SQLAlchemy's metadata
import app.models.firewall_rule  # noqa: F401
import app.models.approval  # noqa: F401
import app.models.audit  # noqa: F401
import app.models.network  # noqa: F401

# Alembic uses 'script' as the environment variable to pass
# configuration arguments. We use this to override the database URL.
#
# Usage:
#   alembic upgrade head --url "$DATABASE_URL"
#   alembic revision --autogenerate -m "Initial migration"

from dotenv import load_dotenv
load_dotenv()

# Configure logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment or alembic.ini
# Environment variable takes precedence over alembic.ini
database_url = os.environ.get("DATABASE_URL")

# Configure target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine
    from which to obtain a connection. The URL is passed through
    the 'alembic' context object.

    Useful for generating migration scripts before they're run.
    """
    url = database_url or context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Better SQLite support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    # Allow overriding the URL via command-line argument
    online_url = context.config.get_main_option("sqlalchemy.url")

    # Use env var if provided, otherwise use alembic.ini URL
    url = database_url or online_url

    config = context.config
    config.set_main_option("sqlalchemy.url", url)

    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    connection = engine.connect()
    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Better SQLite support
            version_table="alembic_migrations",
        )

        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


# Run migrations based on context
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()