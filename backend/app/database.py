"""
Database configuration and session management.

This module handles database engine creation, session management,
and database initialization for both SQLite (development) and PostgreSQL (production).

Usage:
    from app.database import SessionLocal, init_db, get_db
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from typing import Generator, Optional
import os

from app.config import settings


def _build_database_url() -> str:
    """Build database URL from settings with environment-specific defaults.

    Returns:
        str: Database connection URL compatible with SQLite and PostgreSQL.
    """
    db_url = os.environ.get(
        "DATABASE_URL",
        settings.database_url
    )
    return db_url


def create_engine_instance(database_url: Optional[str] = None):
    """Create SQLAlchemy engine with appropriate configuration.

    Creates an engine configured for:
    - SQLite: Uses StaticPool for thread-safety in development
    - PostgreSQL: Uses QueuePool for production connections

    Args:
        database_url: Optional database URL. Defaults to settings.database_url.

    Returns:
        sqlalchemy.engine.Engine: Configured SQLAlchemy engine instance.
    """
    if database_url is None:
        database_url = _build_database_url()

    is_sqlite = "sqlite" in database_url

    # Base engine configuration
    engine_kwargs = {
        "url": database_url,
        "echo": settings.debug,  # SQL query logging controlled by debug mode
    }

    # Database-specific configuration
    if is_sqlite:
        # SQLite-specific settings
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool
    else:
        # PostgreSQL-specific settings
        engine_kwargs["poolclass"] = QueuePool
        engine_kwargs["pool_size"] = 5
        engine_kwargs["pool_recycle"] = 1800  # 30 minutes
        engine_kwargs["pool_pre_ping"] = True  # Test connections on checkout

    engine = create_engine(**engine_kwargs)

    # Enable foreign keys for SQLite (required for proper constraint enforcement)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


# Create engine with configured settings
engine = create_engine_instance()

# Session factory configuration
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent expired object errors after commit
)


def get_db_session() -> Generator[Session, None, None]:
    """Generator-based dependency for getting a database session.

    Yields a database session and ensures it's properly closed afterwards.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db() -> Session:
    """Get a database session.

    Returns:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    return db


def init_db():
    """Initialize database tables.

    Creates all tables defined in the SQLAlchemy models.
    Import all models to ensure they're registered with SQLAlchemy metadata
    before creating tables.
    """
    # Import all models to register them with SQLAlchemy Base metadata
    # This is necessary because models are defined in separate modules
    import app.models  # noqa: F401, F403 - Ensure all models are loaded
    import app.models.firewall_rule  # noqa: F401
    import app.models.approval  # noqa: F401
    import app.models.audit  # noqa: F401

    # Import Base after models are loaded to ensure all tables are registered
    from app.models import Base

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


def drop_all_tables():
    """Drop all database tables. Useful for development/testing."""
    from app.models import Base
    Base.metadata.drop_all(bind=engine)
    print("All database tables dropped.")