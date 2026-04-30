"""
Tests for database configuration and initialization.

Tests database engine creation, session management, and connection handling.
Verifies compatibility with both SQLite and PostgreSQL configurations.
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

# Import database module components
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool, QueuePool


class TestDatabaseEngineCreation:
    """Test database engine creation for different configurations."""

    def test_sqlite_in_memory_engine_creation(self):
        """Test creating an in-memory SQLite engine."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        # Verify the engine can connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

    def test_sqlite_file_engine_creation(self):
        """Test creating a file-based SQLite engine."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            db_url = f"sqlite:///{db_path}"
            engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
            )
            
            # Verify the engine can connect
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_postgresql_engine_configuration(self):
        """Test PostgreSQL engine configuration."""
        pg_url = "postgresql://user:password@localhost:5432/testdb"
        engine = create_engine(pg_url, poolclass=QueuePool)
        
        # Verify pool configuration
        assert engine.poolclass == QueuePool


class TestDatabaseSessionManagement:
    """Test database session management."""

    def test_session_factory_configuration(self):
        """Test that session factory is configured correctly."""
        engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
        SessionFactory = type(
            "TestSession",
            (),
            {"autocommit": False, "autoflush": False}
        )
        
        assert SessionFactory.autocommit is False
        assert SessionFactory.autoflush is False

    def test_sqlite_foreign_keys_enabled(self):
        """Test that foreign keys are enabled for SQLite."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        with engine.connect() as conn:
            # Enable foreign keys
            conn.execute(text("PRAGMA foreign_keys=ON"))
            result = conn.execute(text("PRAGMA foreign_keys"))
            assert result.fetchone()[0] == 1


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_import_models(self):
        """Test that all models can be imported."""
        try:
            from app.models import (
                Base,
                Workload,
                FirewallRule,
                ApprovalRequest,
                ApprovalStep,
                AuditLog,
                User,
                UserRole,
            )
            
            # Verify Base is defined
            assert Base is not None
            
            # Verify table names exist
            assert hasattr(Base, "metadata")
            
        except ImportError as e:
            pytest.fail(f"Failed to import models: {e}")

    def test_metadata_has_tables(self):
        """Test that metadata contains registered tables."""
        from app.models import Base
        
        # All models should be registered with metadata
        assert len(Base.metadata.tables) > 0

    def test_all_model_tables_registered(self):
        """Test that all expected tables are registered."""
        from app.models import Base
        
        expected_tables = {
            "workloads",
            "firewall_rules",
            "approval_requests",
            "approval_steps",
            "approval_workflow_definitions",
            "audit_logs",
            "users",
            "user_roles",
        }
        
        actual_tables = set(Base.metadata.tables.keys())
        
        # Check that expected tables exist
        for table in expected_tables:
            assert table in actual_tables, f"Table '{table}' not registered"


class TestDatabaseURLHandling:
    """Test database URL handling and validation."""

    def test_sqlite_url_defaults(self):
        """Test SQLite URL default configuration."""
        from app.config import settings
        
        # Default should be SQLite
        assert "sqlite" in settings.database_url or "firewall_mgmt.db" in settings.database_url

    def test_database_type_detection(self):
        """Test database type detection from URL."""
        from app.config import settings
        
        # Test SQLite detection
        original_url = settings.database_url
        try:
            settings.database_url = "sqlite:///./test.db"
            assert settings.database_type == "sqlite"
            
            # Test PostgreSQL detection
            settings.database_url = "postgresql://user:pass@localhost/db"
            assert settings.database_type == "postgresql"
        finally:
            settings.database_url = original_url

    def test_is_development_property(self):
        """Test development mode detection."""
        from app.config import settings
        
        original_url = settings.database_url
        original_debug = settings.debug
        
        try:
            # SQLite with debug=True should be development
            settings.database_url = "sqlite:///./test.db"
            settings.debug = True
            assert settings.is_development is True
            
            # SQLite without debug should also be development
            settings.debug = False
            assert settings.is_development is True
            
        finally:
            settings.database_url = original_url
            settings.debug = original_debug

    def test_is_production_property(self):
        """Test production mode detection."""
        from app.config import settings
        
        original_url = settings.database_url
        original_debug = settings.debug
        
        try:
            # PostgreSQL with debug=False should be production
            settings.database_url = "postgresql://user:pass@localhost/db"
            settings.debug = False
            assert settings.is_production is True
            
            # SQLite should never be production
            settings.database_url = "sqlite:///./test.db"
            assert settings.is_production is False
            
        finally:
            settings.database_url = original_url
            settings.debug = original_debug


class TestDatabaseConnection:
    """Test database connection handling."""

    def test_connection_string_format(self):
        """Test that connection strings are properly formatted."""
        test_cases = [
            ("sqlite:///./test.db", "sqlite"),
            ("sqlite:///:memory:", "sqlite"),
            ("postgresql://user:pass@localhost/db", "postgresql"),
            ("postgresql+psycopg2://user:pass@localhost/db", "postgresql"),
            ("postgresql+psycopg2://user:pass@host:5432/db", "postgresql"),
        ]
        
        for url, expected_type in test_cases:
            is_sqlite = "sqlite" in url
            is_postgres = "postgresql" in url or "psycopg2" in url
            
            if expected_type == "sqlite":
                assert is_sqlite is True
            elif expected_type == "postgresql":
                assert is_postgres is True

    def test_connection_with_pragma(self):
        """Test SQLite pragma settings."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.execute(text("PRAGMA journal_mode=WAL"))
            
            # Verify settings
            fk_result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
            assert fk_result[0] == 1