"""
Tests for rate limiting functionality.

Tests cover:
- Rate limit enforcement
- Rate limit reset after window expires
- Rate limit per-endpoint tracking
- Rate limit store cleanup
- Blacklist cleanup
"""

import time
import pytest
from unittest.mock import patch, MagicMock


class TestRateLimitCheck:
    """Test rate limit check functionality."""

    def test_within_rate_limit(self):
        """Test that requests within limit are allowed."""
        from app.auth.auth_service import check_rate_limit, _get_rate_limit_key
        from app.auth import auth_service

        # Clear the store for this test
        original_store = auth_service._rate_limit_store.copy()
        auth_service._rate_limit_store.clear()

        try:
            key = _get_rate_limit_key("127.0.0.1", "/auth/login")
            # Should allow the first request
            assert check_rate_limit(key) is True
        finally:
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)

    def test_rate_limit_enforcement(self):
        """Test that rate limit is enforced after threshold."""
        from app.auth.auth_service import check_rate_limit, _get_rate_limit_key
        from app.auth import auth_service
        from app.config import settings

        original_store = auth_service._rate_limit_store.copy()
        original_enabled = settings.rate_limit_enabled
        auth_service._rate_limit_store.clear()

        try:
            # Temporarily enable rate limiting
            settings.rate_limit_enabled = True

            key = _get_rate_limit_key("127.0.0.1", "/auth/test")
            limit = 5  # Use a low limit for testing

            # Fill up the rate limit
            for _ in range(limit):
                check_rate_limit(key, limit=limit, window=60)

            # Next request should be denied
            assert check_rate_limit(key, limit=limit, window=60) is False
        finally:
            settings.rate_limit_enabled = original_enabled
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)

    def test_rate_limit_disabled(self):
        """Test that rate limit is bypassed when disabled."""
        from app.auth.auth_service import check_rate_limit
        from app.auth import auth_service
        from app.config import settings

        original_store = auth_service._rate_limit_store.copy()
        original_enabled = settings.rate_limit_enabled
        auth_service._rate_limit_store.clear()

        try:
            settings.rate_limit_enabled = False
            key = "test-key"

            # Fill up the store
            for _ in range(100):
                check_rate_limit(key, limit=5, window=60)

            # Should still be allowed when disabled
            assert check_rate_limit(key, limit=5, window=60) is True
        finally:
            settings.rate_limit_enabled = original_enabled
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)

    def test_rate_limit_per_ip_endpoint(self):
        """Test that rate limits are tracked per IP and endpoint."""
        from app.auth.auth_service import check_rate_limit
        from app.auth import auth_service
        from app.config import settings

        original_store = auth_service._rate_limit_store.copy()
        original_enabled = settings.rate_limit_enabled
        auth_service._rate_limit_store.clear()

        try:
            settings.rate_limit_enabled = True
            key1 = "127.0.0.1:/api/path1"
            key2 = "127.0.0.1:/api/path2"
            limit = 3

            # Fill up key1
            for _ in range(limit):
                check_rate_limit(key1, limit=limit, window=60)

            # key1 should be blocked
            assert check_rate_limit(key1, limit=limit, window=60) is False

            # key2 should still be allowed
            assert check_rate_limit(key2, limit=limit, window=60) is True
        finally:
            settings.rate_limit_enabled = original_enabled
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)


class TestRateLimitStore:
    """Test rate limit store operations."""

    def test_rate_limit_store_cleanup(self):
        """Test that expired entries are cleaned up."""
        from app.auth.auth_service import cleanup_rate_limits
        from app.auth import auth_service
        from app.config import settings

        original_store = auth_service._rate_limit_store.copy()
        auth_service._rate_limit_store.clear()

        try:
            # Add entries with old timestamps
            now = time.time()
            auth_service._rate_limit_store["old-entry"] = [now - 120, now - 110]
            auth_service._rate_limit_store["new-entry"] = [now - 10]

            cleaned = cleanup_rate_limits()

            # Old entry should be cleaned up
            assert "old-entry" not in auth_service._rate_limit_store
            # New entry should remain
            assert "new-entry" in auth_service._rate_limit_store
        finally:
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)


class TestBlacklistCleanup:
    """Test blacklist cleanup functionality."""

    def test_blacklist_cleanup(self):
        """Test that expired entries are removed from blacklist."""
        from app.auth.auth_service import cleanup_blacklist
        from app.auth.auth_service import _token_blacklist
        from datetime import datetime, timedelta, timezone

        # Add entries with past and future expirations
        now = datetime.now(timezone.utc)
        _token_blacklist["expired-token"] = now - timedelta(hours=1)
        _token_blacklist["valid-token"] = now + timedelta(days=7)

        cleaned = cleanup_blacklist()

        assert cleaned == 1
        assert "expired-token" not in _token_blacklist
        assert "valid-token" in _token_blacklist

        # Cleanup
        del _token_blacklist["valid-token"]


class TestRateLimitMiddleware:
    """Test rate limit middleware functionality."""

    def test_middleware_returns_429(self):
        """Test that middleware returns 429 when rate limit exceeded."""
        from app.auth.auth_service import create_rate_limit_middleware, _get_rate_limit_key
        from app.auth import auth_service
        from app.config import settings
        from unittest.mock import PropertyMock, patch

        original_store = auth_service._rate_limit_store.copy()
        original_enabled = settings.rate_limit_enabled
        auth_service._rate_limit_store.clear()

        try:
            settings.rate_limit_enabled = True
            middleware = create_rate_limit_middleware()

            # Create mock request
            mock_request = MagicMock()
            mock_request.url.path = "/auth/login"
            mock_request.client.host = "127.0.0.1"

            # Fill the rate limit using the configured limit
            key = _get_rate_limit_key("127.0.0.1", "/auth/login")
            configured_limit = settings.auth_rate_limit_per_minute

            # Fill up to the configured limit
            for _ in range(configured_limit):
                auth_service._rate_limit_store.setdefault(key, []).append(time.time())

            # Call middleware - it's sync but returns JSONResponse
            call_next_result = MagicMock()

            result = middleware(mock_request, call_next_result)

            # Should return JSONResponse with 429
            assert hasattr(result, 'status_code')
            assert result.status_code == 429

            # call_next should NOT have been called
            call_next_result.assert_not_called()
        finally:
            settings.rate_limit_enabled = original_enabled
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)

    def test_middleware_allows_through(self):
        """Test that middleware allows requests through when under limit."""
        from app.auth.auth_service import create_rate_limit_middleware
        from app.auth import auth_service

        original_store = auth_service._rate_limit_store.copy()
        auth_service._rate_limit_store.clear()

        try:
            middleware = create_rate_limit_middleware()

            mock_request = MagicMock()
            mock_request.url.path = "/auth/login"
            mock_request.client.host = "127.0.0.1"

            call_next_result = MagicMock()

            result = middleware(mock_request, call_next_result)

            # Should call call_next and return its result
            call_next_result.assert_called_once_with(mock_request)
            # The result should be what call_next_result returns when called
            assert result == call_next_result.return_value
        finally:
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)


class TestRateLimitReset:
    """Test that rate limits reset after window expires."""

    def test_rate_limit_resets_after_window(self):
        """Test that rate limit resets after the time window passes."""
        from app.auth.auth_service import check_rate_limit, _get_rate_limit_key
        from app.auth import auth_service
        from app.config import settings

        original_store = auth_service._rate_limit_store.copy()
        original_enabled = settings.rate_limit_enabled
        auth_service._rate_limit_store.clear()

        try:
            settings.rate_limit_enabled = True

            key = _get_rate_limit_key("127.0.0.1", "/auth/test")
            limit = 2
            window = 1  # 1 second window for speed

            # Fill up the rate limit
            for _ in range(limit):
                check_rate_limit(key, limit=limit, window=window)

            # Should be blocked
            assert check_rate_limit(key, limit=limit, window=window) is False

            # Wait for window to expire
            time.sleep(window + 0.1)

            # Should be allowed again (old entries cleaned)
            assert check_rate_limit(key, limit=limit, window=window) is True
        finally:
            settings.rate_limit_enabled = original_enabled
            auth_service._rate_limit_store.clear()
            auth_service._rate_limit_store.update(original_store)