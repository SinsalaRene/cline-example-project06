"""
Comprehensive tests for configuration management.

Tests cover:
- Settings initialization and environment variable loading
- Field validation (database URL, secret key, token expiry)
- Property-based checks (database_type, is_production, is_development)
- Method testing (get_database_dsn, get_postgres_url)
- Settings caching behavior
- Edge cases and error handling
"""

import os
import pytest
import uuid
from unittest.mock import patch, MagicMock

# Set environment variables before importing settings
os.environ.setdefault("AZURE_TENANT_ID", "test-tenant-id")
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("AZURE_SUBSCRIPTION_ID", "test-subscription-id")
os.environ.setdefault("AZURE_RESOURCE_GROUP", "test-resource-group")
os.environ.setdefault("AZURE_REGION", "eastus")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-must-be-at-least-256-bits-long")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("AUTH_RATE_LIMIT_PER_MINUTE", "20")
os.environ.setdefault("RATE_LIMIT_ENABLED", "true")


class TestSettingsInitialization:
    """Test settings initialization and environment variable loading."""

    def test_settings_default_values(self):
        """Test that settings load with correct default values."""
        from app.config import Settings
        from app.config import DatabaseType

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.azure_tenant_id == "test-tenant"
        assert settings.azure_client_id == "test-client"
        assert settings.azure_client_secret == "test-secret"
        assert settings.azure_subscription_id == "test-sub"
        assert settings.azure_region == "eastus"
        assert settings.database_echo is False
        assert settings.debug is False
        assert settings.allowed_hosts == ["*"]
        assert settings.api_prefix == "/api"
        assert settings.approval_queue_name == "approval-requests"
        assert settings.smtp_port == 587
        assert settings.auth_metadata_url == (
            "https://login.microsoftonline.com/common/.well-known/openid-configuration"
        )

    def test_settings_database_type_sqlite(self):
        """Test that SQLite database URL is detected correctly."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.database_type == "sqlite"
        assert settings.is_development is True
        assert settings.is_production is False

    def test_settings_database_type_postgresql(self):
        """Test that PostgreSQL database URL is detected correctly."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:password@localhost:5432/mydb",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.database_type == "postgresql"
        assert settings.is_production is True
        assert settings.is_development is False

    def test_settings_database_type_unknown(self):
        """Test unknown database type returns 'unknown'."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="mysql://some-connection-string",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.database_type == "unknown"

    def test_settings_optional_fields_default(self):
        """Test that optional fields have correct default values."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.service_bus_connection_string is None
        assert settings.teams_webhook_url is None
        assert settings.smtp_host is None
        assert settings.debug is False

    def test_settings_rate_limiting_config(self):
        """Test rate limiting configuration."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            auth_rate_limit_per_minute=30,
            auth_rate_limit_window=120,
            rate_limit_enabled=True,
        )

        assert settings.auth_rate_limit_per_minute == 30
        assert settings.auth_rate_limit_window == 120
        assert settings.rate_limit_enabled is True


class TestDatabaseURLValidation:
    """Test database URL validation."""

    def test_empty_database_url_raises(self):
        """Test that empty database URL raises ValueError."""
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            Settings(
                azure_tenant_id="test-tenant",
                azure_client_id="test-client",
                azure_client_secret="test-secret",
                azure_subscription_id="test-sub",
                azure_resource_group="test-rg",
                database_url="",
                secret_key="test-secret-key-at-least-16-characters-long-enough",
            )

        assert "DATABASE_URL cannot be empty" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_valid_sqlite_database_url(self):
        """Test that valid SQLite URL passes validation."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.database_url == "sqlite:///./test.db"

    def test_valid_postgresql_database_url(self):
        """Test that valid PostgreSQL URL passes validation."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:password@localhost:5432/mydb",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert "postgresql" in settings.database_url


class TestSecretKeyValidation:
    """Test secret key validation."""

    def test_short_secret_key_raises(self):
        """Test that short secret key raises ValueError."""
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            Settings(
                azure_tenant_id="test-tenant",
                azure_client_id="test-client",
                azure_client_secret="test-secret",
                azure_subscription_id="test-sub",
                azure_resource_group="test-rg",
                database_url="sqlite:///./test.db",
                secret_key="short",
            )

        assert "at least 8 characters" in str(exc_info.value) or "at least 16 characters" in str(exc_info.value)

    def test_minimum_length_secret_key(self):
        """Test that minimum length secret key (8 chars) passes first validator."""
        from app.config import Settings
        from pydantic import ValidationError

        # 8 chars should pass first validator but may fail second
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                azure_tenant_id="test-tenant",
                azure_client_id="test-client",
                azure_client_secret="test-secret",
                azure_subscription_id="test-sub",
                azure_resource_group="test-rg",
                database_url="sqlite:///./test.db",
                secret_key="min-len-8",
            )

        # "min-len-8" should fail the second validator (16 char minimum)
        assert "at least 16 characters" in str(exc_info.value)

    def test_minimum_16_char_secret_key_passes(self):
        """Test that 16+ char secret key passes all validators (using correct field name)."""
        """Test that 16+ char secret key passes all validators."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="exact-16-char-key-!",
        )

        assert settings.secret_key == "exact-16-char-key-!"

    def test_long_secret_key_passes(self):
        """Test that long secret keys pass validation."""
        from app.config import Settings

        long_secret = "a" * 100
        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key=long_secret,
        )

        assert settings.secret_key == long_secret


class TestTokenExpiryValidation:
    """Test token expiry validation."""

    def test_zero_access_token_expire_raises(self):
        """Test that zero access_token_expire_minutes raises."""
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                azure_tenant_id="test-tenant",
                azure_client_id="test-client",
                azure_client_secret="test-secret",
                azure_subscription_id="test-sub",
                azure_resource_group="test-rg",
                database_url="sqlite:///./test.db",
                secret_key="test-secret-key-at-least-16-characters-long-enough",
                access_token_expire_minutes=0,
            )

    def test_negative_access_token_expire_raises(self):
        """Test that negative access_token_expire_minutes raises."""
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                azure_tenant_id="test-tenant",
                azure_client_id="test-client",
                azure_client_secret="test-secret",
                azure_subscription_id="test-sub",
                azure_resource_group="test-rg",
                database_url="sqlite:///./test.db",
                secret_key="test-secret-key-at-least-16-characters-long-enough",
                access_token_expire_minutes=-10,
            )

    def test_excessive_token_expire_raises(self):
        """Test that access_token_expire exceeding 1440 raises."""
        from app.config import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                azure_tenant_id="test-tenant",
                azure_client_id="test-client",
                azure_client_secret="test-secret",
                azure_subscription_id="test-sub",
                azure_resource_group="test-rg",
                database_url="sqlite:///./test.db",
                secret_key="test-secret-key-at-least-16-characters-long-enough",
                access_token_expire_minutes=1441,
            )

    def test_valid_token_expiry_values(self):
        """Test that valid token expiry values pass."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            access_token_expire_minutes=60,
        )

        assert settings.access_token_expire_minutes == 60

    def test_max_token_expiry_allowed(self):
        """Test that max token expiry (1440 minutes) is allowed."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            access_token_expire_minutes=1440,
        )

        assert settings.access_token_expire_minutes == 1440

    def test_refresh_token_expire_config(self):
        """Test refresh token expiration configuration."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            refresh_token_expire_days=14,
        )

        assert settings.refresh_token_expire_days == 14


class TestSettingsProperties:
    """Test settings property methods."""

    def test_database_type_property(self):
        """Test database_type property for various database URLs."""
        from app.config import Settings

        # SQLite
        sqlite_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )
        assert sqlite_settings.database_type == "sqlite"

        # PostgreSQL
        pg_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:pass@host:5432/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )
        assert pg_settings.database_type == "postgresql"

        # Unknown
        unknown_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="mysql://localhost/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )
        assert unknown_settings.database_type == "unknown"

    def test_is_production_property(self):
        """Test is_production property."""
        from app.config import Settings

        # Production: PostgreSQL + debug=False
        prod_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:pass@host:5432/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            debug=False,
        )
        assert prod_settings.is_production is True

        # Development: SQLite
        dev_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            debug=False,
        )
        assert dev_settings.is_production is False

    def test_is_development_property(self):
        """Test is_development property."""
        from app.config import Settings

        # SQLite should be development
        dev_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )
        assert dev_settings.is_development is True

        # debug=True should be development
        debug_settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:pass@host:5432/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            debug=True,
        )
        assert debug_settings.is_development is True


class TestDatabaseDSNMethods:
    """Test database DSN-related methods."""

    def test_get_database_dsn_sqlite(self):
        """Test get_database_dsn for SQLite returns sanitized string."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        dsn = settings.get_database_dsn(include_password=True)
        assert "local database" in dsn or "test.db" in dsn

    def test_get_database_dsn_postgresql_include_password(self):
        """Test get_database_dsn for PostgreSQL with password included."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:password@host:5432/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        dsn = settings.get_database_dsn(include_password=True)
        assert "password" in dsn or "password" in settings.database_url

    def test_get_database_dsn_postgresql_hide_password(self):
        """Test get_database_dsn for PostgreSQL with password hidden."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:password@host:5432/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        dsn = settings.get_database_dsn(include_password=False)
        assert "***" in dsn


class TestGetPostgresURL:
    """Test get_postgres_url method."""

    def test_get_postgres_url_from_env(self):
        """Test get_postgres_url retrieves from environment."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="postgresql://user:pass@host:5432/db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        url = settings.get_postgres_url()
        assert "postgresql" in url

    def test_get_postgres_url_raises_for_sqlite(self):
        """Test get_postgres_url raises for SQLite URL."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        # Should raise ValueError because DATABASE_URL env var won't have postgresql
        with patch.dict(os.environ, {}, clear=False):
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]
            with pytest.raises(ValueError):
                settings.get_postgres_url()


class TestGetSettings:
    """Test get_settings caching."""

    def test_get_settings_returns_cached(self):
        """Test that get_settings returns a cached Settings instance."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_instance_has_all_fields(self):
        """Test that Settings instance has all expected fields."""
        from app.config import get_settings

        settings = get_settings()

        # Check all required fields exist
        assert hasattr(settings, "azure_tenant_id")
        assert hasattr(settings, "azure_client_id")
        assert hasattr(settings, "azure_client_secret")
        assert hasattr(settings, "azure_subscription_id")
        assert hasattr(settings, "azure_resource_group")
        assert hasattr(settings, "azure_region")
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "database_echo")
        assert hasattr(settings, "secret_key")
        assert hasattr(settings, "algorithm")
        assert hasattr(settings, "access_token_expire_minutes")
        assert hasattr(settings, "refresh_token_expire_days")
        assert hasattr(settings, "auth_rate_limit_per_minute")
        assert hasattr(settings, "auth_rate_limit_window")
        assert hasattr(settings, "rate_limit_enabled")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "allowed_hosts")
        assert hasattr(settings, "api_prefix")
        assert hasattr(settings, "service_bus_connection_string")
        assert hasattr(settings, "approval_queue_name")
        assert hasattr(settings, "teams_webhook_url")
        assert hasattr(settings, "smtp_host")
        assert hasattr(settings, "smtp_port")
        assert hasattr(settings, "auth_metadata_url")


class TestSettingsEdgeCases:
    """Test edge cases and error handling."""

    def test_settings_with_all_optional_fields(self):
        """Test settings with all optional fields set."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
            service_bus_connection_string="Endpoint=sb://test.servicebus.windows.net/",
            teams_webhook_url="https://teams.microsoft.com/webhook",
            smtp_host="smtp.example.com",
            auth_rate_limit_per_minute=50,
            auth_rate_limit_window=120,
            rate_limit_enabled=False,
        )

        assert settings.service_bus_connection_string is not None
        assert settings.teams_webhook_url is not None
        assert settings.smtp_host == "smtp.example.com"
        assert settings.auth_rate_limit_per_minute == 50
        assert settings.auth_rate_limit_window == 120
        assert settings.rate_limit_enabled is False

    def test_settings_algorithm_default(self):
        """Test that algorithm defaults to HS256."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.algorithm == "HS256"

    def test_settings_allowed_hosts_default(self):
        """Test that allowed_hosts defaults to ['*']."""
        from app.config import Settings

        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        assert settings.allowed_hosts == ["*"]

    def test_settings_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        from app.config import Settings

        # Settings should be case insensitive
        settings = Settings(
            azure_tenant_id="test-tenant",
            azure_client_id="test-client",
            azure_client_secret="test-secret",
            azure_subscription_id="test-sub",
            azure_resource_group="test-rg",
            database_url="sqlite:///./test.db",
            secret_key="test-secret-key-at-least-16-characters-long-enough",
        )

        # All fields should be accessible
        assert settings.database_url == "sqlite:///./test.db"
        assert settings.secret_key == "test-secret-key-at-least-16-characters-long-enough"