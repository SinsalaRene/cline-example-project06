"""
Pytest configuration for integration tests.

This module provides shared fixtures and hooks for all tests.
"""
import pytest


# Clear rate limit store before each test to prevent cross-test interference
@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Clear rate limit store before each test."""
    from app.auth.auth_service import _rate_limit_store
    _rate_limit_store.clear()