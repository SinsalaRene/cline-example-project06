"""
Azure integration package for firewall management.

This package provides Azure SDK integration for firewall rule management,
including authentication, rule validation, duplicate detection,
and synchronization with Azure Firewall.

For local development, set AZURE_MOCK_MODE=true in your .env file to use
the MockAzureClient instead of the real Azure SDK client.
"""

from app.integrations.azure_client import (
    AzureClient,
    AzureClientError,
    AzureAuthenticationError,
    AzureResourceNotFoundError,
    AzureRuleValidationError,
    AzureRateLimitExceededError,
    create_azure_client_from_settings,
)
from app.integrations.mock_azure_client import MockAzureClient

__all__ = [
    "AzureClient",
    "MockAzureClient",
    "AzureClientError",
    "AzureAuthenticationError",
    "AzureResourceNotFoundError",
    "AzureRuleValidationError",
    "AzureRateLimitExceededError",
    "create_azure_client_from_settings",
    "create_azure_client",
]


def create_azure_client(settings=None):
    """Factory function that returns the appropriate Azure client.

    When settings.azure_mock_mode is True, returns a MockAzureClient.
    Otherwise, returns a real AzureClient.

    Args:
        settings: Settings object with azure configuration.

    Returns:
        Either an AzureClient or MockAzureClient instance.
    """
    if settings is None:
        from app.config import settings as app_settings
        use_mock = app_settings.is_azure_mock_mode
    else:
        use_mock = getattr(settings, "is_azure_mock_mode", False)

    if use_mock:
        return MockAzureClient.from_settings(settings)
    else:
        return create_azure_client_from_settings(settings)