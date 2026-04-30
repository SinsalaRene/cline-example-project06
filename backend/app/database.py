"""
Database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.config import settings
from app.models.firewall_rule import Base as ModelsBase

# Create engine based on database URL
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    poolclass=StaticPool if "sqlite" in settings.database_url else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for getting a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models to ensure they're registered with SQLAlchemy
    # Models are imported from their respective modules
    ModelsBase.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


def get_db() -> Session:
    """Get a database session."""
    db = SessionLocal()
    return db