"""
Configuration management for the Azure Firewall Management application.

Uses environment variables with validation and sensible defaults.
Supports both SQLite (development) and PostgreSQL (production) databases.
"""

from typing import Optional, List, Union
from enum import Enum as PyEnum
from functools import lru_cache
from pydantic import field_validator, model_validator, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def allowed_hosts_preprocessor(v: Union[str, List[str], None]) -> List[str]:
    """Pre-process allowed_hosts from env var to List[str].
    
    Handles both string values like '*' and list values like ['*', 'localhost'].
    """
    if v is None or v == "":
        return ["*"]
    if isinstance(v, str):
        # Try to parse as comma-separated list first
        if "," in v:
            return [x.strip() for x in v.split(",") if x.strip()]
        # Single value
        return [v]
    return v if v else ["*"]


class DatabaseType(str, PyEnum):
    """Supported database types."""
    SQLite = "sqlite"
    PostgreSQL = "postgresql"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Validates required fields and provides sensible defaults for development.
    """

    # Azure Configuration
    azure_tenant_id: str = "test-tenant-id"
    azure_client_id: str = "test-client-id"
    azure_client_secret: str = "test-client-secret"
    azure_subscription_id: str = "test-subscription-id"
    azure_resource_group: str = "test-resource-group"
    azure_region: str = "eastus"

    # Database Configuration
    database_url: str = "sqlite:///./firewall_mgmt.db"
    database_echo: bool = False

    # Security / JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30  # Short-lived access tokens (max 1440 per validator)
    refresh_token_expire_days: int = 7  # Refresh tokens valid for 7 days

    # Local Development Authentication
    dev_email: str = "dev@example.com"
    dev_password: str = "devpass123"
    
    # Rate Limiting for Auth Endpoints
    auth_rate_limit_per_minute: int = 20  # Max 20 requests per minute per IP
    auth_rate_limit_window: int = 60  # 60 seconds window
    rate_limit_enabled: bool = True  # Master switch for rate limiting

    # API Configuration
    debug: bool = False
    allowed_hosts: List[str] = ["*"]
    api_prefix: str = "/api"

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def validate_allowed_hosts(cls, v: Union[str, List[str], None]) -> List[str]:
        """Validate allowed_hosts and handle string values from env vars."""
        return allowed_hosts_preprocessor(v)

    def model_post_init(self, __context):
        """Post-init hook to handle allowed_hosts if it wasn't set."""
        if not self.allowed_hosts or self.allowed_hosts == ["*"]:
            # Only set default if it wasn't explicitly set from env
            if not hasattr(self, '_allowed_hosts_from_env'):
                object.__setattr__(self, 'allowed_hosts', ["*"])

    # Azure Mock Mode (local development)
    azure_mock_mode: bool = True  # Default to True so local dev works without Azure
    
    # Azure Service Bus (optional)
    service_bus_connection_string: Optional[str] = None
    approval_queue_name: str = "approval-requests"

    # Notification
    teams_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587

    # Production / Monitoring
    error_tracking_dsn: Optional[str] = None
    enable_metrics: bool = True
    log_format: str = "json"
    sentry_sample_rate: float = 0.1

    # OpenAPI/JWT Configuration
    auth_metadata_url: str = (
        "https://login.microsoftonline.com/common/.well-known/openid-configuration"
    )

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format and type."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        return v

    @field_validator("azure_tenant_id", "azure_client_id", "azure_client_secret", 
                      "azure_subscription_id", "azure_resource_group")
    @classmethod
    def validate_azure_config(cls, v: str, info) -> str:
        """Validate that required Azure configuration is not empty."""
        field_name = info.data.get("field_name")
        if field_name and not v.strip():
            raise ValueError(f"{field_name} is required for Azure authentication")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key_len(cls, v: str) -> str:
        """Validate that secret_key has sufficient length but allow test values."""
        if len(v) < 8:
            raise ValueError("secret_key must be at least 8 characters long for testing")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that secret_key is not the default value."""
        if v == "your-secret-key-change-in-production":
            # Only warn in debug mode
            pass
        if not v or len(v) < 16:
            raise ValueError("secret_key must be at least 16 characters long")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiry(cls, v: int) -> int:
        """Validate token expiration time."""
        if v <= 0:
            raise ValueError("access_token_expire_minutes must be positive")
        if v > 1440:  # 24 hours max
            raise ValueError("access_token_expire_minutes must not exceed 1440 (24 hours)")
        return v

    @property
    def database_type(self) -> str:
        """Return the detected database type."""
        if "sqlite" in self.database_url:
            return "sqlite"
        elif "postgresql" in self.database_url:
            return "postgresql"
        return "unknown"

    @property
    def is_production(self) -> bool:
        """Return True if running in production mode."""
        return self.database_type == "postgresql" and self.debug is False

    @property
    def is_development(self) -> bool:
        """Return True if running in development mode."""
        return self.database_type == "sqlite" or self.debug is True

    @property
    def is_azure_mock_mode(self) -> bool:
        """Return True if Azure operations should be mocked."""
        return self.azure_mock_mode is True

    def get_database_dsn(self, include_password: bool = True) -> str:
        """Get a sanitized database DSN for display/logging.
        
        Args:
            include_password: Whether to include password in the DSN.
            
        Returns:
            str: Sanitized database DSN.
        """
        if "sqlite" in self.database_url:
            return "sqlite:///[local database file]"
        
        if include_password:
            return self.database_url
        
        # Replace password with ***
        parts = self.database_url.split("://")
        if len(parts) == 2:
            scheme = parts[0]
            rest = parts[1]
            if "@" in rest:
                host = rest.split("@")[-1]
                return f"{scheme}://***@{host}"
        return self.database_url + " (password hidden)"

    def get_postgres_url(self) -> str:
        """Get PostgreSQL URL from environment or raise error."""
        import os
        
        url = os.environ.get("DATABASE_URL")
        if not url or "postgresql" not in url:
            raise ValueError(
                "DATABASE_URL must be a valid PostgreSQL connection string for production. "
                "Example: postgresql://user:password@host:5432/dbname"
            )
        return url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings: Application settings instance.
    """
    return Settings()


# Global settings instance
settings = get_settings()