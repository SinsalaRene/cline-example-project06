"""
Azure integration package for firewall management.

This package provides Azure SDK integration for firewall rule management,
including authentication, rule validation, duplicate detection,
and synchronization with Azure Firewall.
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

__all__ = [
    "AzureClient",
    "AzureClientError",
    "AzureAuthenticationError",
    "AzureResourceNotFoundError",
    "AzureRuleValidationError",
    "AzureRateLimitExceededError",
    "create_azure_client_from_settings",
]