"""
Tests for configuration management.

Tests configuration loading, validation, and environment handling.
"""

import os
import pytest
import tempfile


class TestConfigLoading:
    """Test configuration loading from environment variables."""

    def test_default_settings_load(self):
        """Test that default settings load correctly."""
        from app.config import Settings
        
        # Create settings with minimal required values
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        
        try:
            settings = Settings()
            
            assert settings.azure_tenant_id == "test-tenant-id"
            assert settings.azure_client_id == "test-client-id"
            assert settings.azure_region == "eastus"
        finally:
            # Clean up
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_database_url_default(self):
        """Test default database URL configuration."""
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        
        try:
            from app.config import Settings
            settings = Settings()
            
            # Default should be SQLite
            assert "sqlite" in settings.database_url
        finally:
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_database_url_custom(self):
        """Test custom database URL configuration."""
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
        
        try:
            from app.config import Settings
            settings = Settings()
            
            assert "postgresql" in settings.database_url
        finally:
            del os.environ["DATABASE_URL"]
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_settings_caching(self):
        """Test that settings are cached (lru_cache behavior)."""
        from app.config import get_settings
        
        # First call should create the instance
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same instance (cached)
        assert settings1 is settings2


class TestConfigValidation:
    """Test configuration validation."""

    def test_database_url_required(self):
        """Test that database URL cannot be empty."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        
        try:
            # Empty database URL should raise validation error
            with pytest.raises(ValueError, match="DATABASE_URL cannot be empty"):
                Settings(database_url="")
        finally:
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_secret_key_minimum_length(self):
        """Test that secret key has minimum length requirement."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        
        try:
            # Valid secret key (>= 16 chars) should work
            settings = Settings()
            assert len(settings.secret_key) >= 16
        finally:
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_token_expiry_validation(self):
        """Test token expiry time validation."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "240"
        
        try:
            settings = Settings()
            assert settings.access_token_expire_minutes == 240
        finally:
            del os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_access_token_expire_minutes_upper_bound(self):
        """Test that access_token_expire_minutes cannot exceed upper bound."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "1441"
        
        try:
            with pytest.raises(ValueError, match="access_token_expire_minutes must not exceed 1440"):
                Settings()
        finally:
            del os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"]
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]


class TestDatabaseTypeDetection:
    """Test database type detection methods."""

    def test_detect_sqlite(self):
        """Test SQLite database type detection."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"
        
        try:
            settings = Settings()
            assert settings.database_type == "sqlite"
        finally:
            del os.environ["DATABASE_URL"]
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_detect_postgresql(self):
        """Test PostgreSQL database type detection."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
        
        try:
            settings = Settings()
            assert settings.database_type == "postgresql"
        finally:
            del os.environ["DATABASE_URL"]
            del os.environ["AZURE_TENANT_ID"]
            del os.environ["AZURE_CLIENT_ID"]
            del os.environ["AZURE_CLIENT_SECRET"]
            del os.environ["AZURE_SUBSCRIPTION_ID"]
            del os.environ["AZURE_RESOURCE_GROUP"]
            del os.environ["SECRET_KEY"]

    def test_is_development_sqlite(self):
        """Test that SQLite is detected as development."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"
        os.environ["DEBUG"] = "false"
        
        try:
            settings = Settings()
            assert settings.is_development is True
        finally:
            for key in ["DATABASE_URL", "DEBUG"]:
                if key in os.environ:
                    del os.environ[key]
            for key in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                        "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]

    def test_is_production_postgresql(self):
        """Test that PostgreSQL without debug is production."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
        os.environ["DEBUG"] = "false"
        
        try:
            settings = Settings()
            assert settings.is_production is True
        finally:
            for key in ["DATABASE_URL", "DEBUG"]:
                if key in os.environ:
                    del os.environ[key]
            for key in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                        "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]


class TestConfigProperties:
    """Test configuration property methods."""

    def test_get_database_dsn_sqlite(self):
        """Test DSN display for SQLite."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "sqlite:///./firewall_mgmt.db"
        
        try:
            settings = Settings()
            dsn = settings.get_database_dsn()
            assert "sqlite" in dsn.lower()
        finally:
            for key in ["DATABASE_URL"]:
                if key in os.environ:
                    del os.environ[key]
            for key in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                        "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]

    def test_get_database_dsn_postgresql_hidden_password(self):
        """Test DSN display for PostgreSQL with hidden password."""
        from app.config import Settings
        
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "postgresql://user:password123@localhost/mydb"
        
        try:
            settings = Settings()
            dsn = settings.get_database_dsn(include_password=False)
            assert "***" in dsn
            assert "password123" not in dsn
        finally:
            for key in ["DATABASE_URL"]:
                if key in os.environ:
                    del os.environ[key]
            for key in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                        "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]

    def test_get_postgres_url_success(self):
        """Test PostgreSQL URL retrieval."""
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
        
        try:
            from app.config import Settings
            settings = Settings()
            url = settings.get_postgres_url()
            assert "postgresql" in url
        finally:
            for key in ["DATABASE_URL"]:
                if key in os.environ:
                    del os.environ[key]
            for key in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                        "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]

    def test_get_postgres_url_failure(self):
        """Test PostgreSQL URL retrieval raises error for non-postgres."""
        os.environ["AZURE_TENANT_ID"] = "test-tenant-id"
        os.environ["AZURE_CLIENT_ID"] = "test-client-id"
        os.environ["AZURE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["AZURE_SUBSCRIPTION_ID"] = "test-subscription-id"
        os.environ["AZURE_RESOURCE_GROUP"] = "test-resource-group"
        os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"
        
        try:
            from app.config import Settings
            settings = Settings()
            
            with pytest.raises(ValueError, match="postgresql"):
                settings.get_postgres_url()
        finally:
            for key in ["DATABASE_URL"]:
                if key in os.environ:
                    del os.environ[key]
            for key in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET",
                        "AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "SECRET_KEY"]:
                if key in os.environ:
                    del os.environ[key]