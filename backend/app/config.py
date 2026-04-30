"""
Configuration management for the Azure Firewall Management application.
Uses environment variables with sensible defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure Configuration
    azure_tenant_id: str = Field(..., description="Azure Entra ID Tenant ID")
    azure_client_id: str = Field(..., description="Azure Entra ID Client ID for the app")
    azure_client_secret: str = Field(..., description="Azure Client Secret")
    azure_subscription_id: str = Field(..., description="Azure Subscription ID")
    azure_resource_group: str = Field(..., description="Azure Resource Group name")
    azure_region: str = "eastus"

    # Database Configuration
    database_url: str = Field(
        "sqlite:///./firewall_mgmt.db",
        description="Database connection URL"
    )

    # Security
    secret_key: str = Field(
        "your-secret-key-change-in-production",
        description="Secret key for JWT signing"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # API Configuration
    debug: bool = False
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    api_prefix: str = "/api"

    # Azure Service Bus (optional)
    service_bus_connection_string: Optional[str] = None
    approval_queue_name: str = "approval-requests"

    # Notification
    teams_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587

    # OpenAPI/JWT Configuration
    auth_metadata_url: str = Field(
        default_factory=lambda: "https://login.microsoftonline.com/common/.well-known/openid-configuration"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()