"""
Tests for authentication: token creation, validation, refresh, and revoke.

Tests cover:
- Access token creation and validation
- Refresh token creation and validation
- Token refresh with rotation
- Token revocation/blacklisting
- Token expiration handling
- Blacklist persistence across validation
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

# Set minimal environment variables before importing app modules
os.environ.setdefault("AZURE_TENANT_ID", "test-tenant-id")
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("AZURE_SUBSCRIPTION_ID", "test-subscription-id")
os.environ.setdefault("AZURE_RESOURCE_GROUP", "test-resource-group")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-must-be-at-least-256-bits")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DEBUG", "true")

# Re-import settings after setting env vars
from app.config import settings as _settings


class TestAccessTokenCreation:
    """Test access token creation and validation."""

    def test_create_access_token(self):
        """Test that access tokens are created with correct claims."""
        from app.auth.auth_service import create_access_token
        from app.config import settings

        token = create_access_token({"sub": "test-user"})

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode the token to verify contents
        import jwt as pyjwt
        payload = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        assert payload["sub"] == "test-user"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "jti" in payload

    def test_access_token_has_expiration(self):
        """Test that access tokens have expiration claim."""
        from app.auth.auth_service import create_access_token
        from app.config import settings

        token = create_access_token({"sub": "test-user"})
        import jwt as pyjwt
        payload = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        assert "exp" in payload
        assert payload["exp"] > int(time.time())

    def test_access_token_default_expiration(self):
        """Test that access token uses configured expiration."""
        from app.auth.auth_service import create_access_token
        from app.config import settings

        token = create_access_token({"sub": "test-user"})
        import jwt as pyjwt
        payload = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        expected_expire_minutes = settings.access_token_expire_minutes
        expected_exp = int(payload["exp"])
        actual_duration = expected_exp - int(time.time())

        # Allow ±1 minute tolerance for execution time
        assert abs(actual_duration - (expected_expire_minutes * 60)) < 60

    def test_access_token_custom_expiration(self):
        """Test that custom expiration overrides default."""
        from datetime import timedelta
        from app.auth.auth_service import create_access_token
        from app.config import settings
        import jwt as pyjwt

        custom_duration = timedelta(minutes=15)
        token = create_access_token(
            {"sub": "test-user"},
            expires_delta=custom_duration
        )
        payload = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        actual_duration = payload["exp"] - int(time.time())
        expected_seconds = int(custom_duration.total_seconds())
        assert abs(actual_duration - expected_seconds) < 5

    def test_access_token_has_unique_jti(self):
        """Test that each access token has a unique JTI."""
        from app.auth.auth_service import create_access_token
        import jwt as pyjwt
        from app.config import settings

        token1 = create_access_token({"sub": "test-user"})
        token2 = create_access_token({"sub": "test-user"})

        payload1 = pyjwt.decode(token1, settings.secret_key, algorithms=[settings.algorithm])
        payload2 = pyjwt.decode(token2, settings.secret_key, algorithms=[settings.algorithm])

        assert payload1["jti"] != payload2["jti"]


class TestRefreshTokenCreation:
    """Test refresh token creation and validation."""

    def test_create_refresh_token(self):
        """Test that refresh tokens are created correctly."""
        from app.auth.auth_service import create_refresh_token

        refresh_token, token_id = create_refresh_token({"sub": "test-user"})

        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0
        assert isinstance(token_id, str)
        assert len(token_id) > 0

    def test_refresh_token_has_type(self):
        """Test that refresh token has type=refresh claim."""
        from app.auth.auth_service import create_refresh_token
        from app.config import settings
        import jwt as pyjwt

        refresh_token, _ = create_refresh_token({"sub": "test-user"})
        payload = pyjwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        assert payload["type"] == "refresh"
        assert payload["sub"] == "test-user"

    def test_refresh_token_expiration(self):
        """Test that refresh token has correct expiration (7 days)."""
        from app.auth.auth_service import create_refresh_token
        from app.config import settings
        import jwt as pyjwt

        refresh_token, _ = create_refresh_token({"sub": "test-user"})
        payload = pyjwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        # Refresh token should be valid for ~7 days (7 * 24 * 60 * 60 seconds)
        expected_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
        actual_duration = payload["exp"] - int(time.time())
        assert abs(actual_duration - expected_seconds) < 60


class TestTokenValidation:
    """Test token validation functionality."""

    def test_validate_valid_access_token(self):
        """Test validation of a valid access token."""
        from app.auth.auth_service import create_access_token, validate_access_token

        token = create_access_token({"sub": "test-user"})
        payload = validate_access_token(token)

        assert payload is not None
        assert payload["sub"] == "test-user"
        assert payload["type"] == "access"

    def test_validate_invalid_token(self):
        """Test that invalid tokens return None."""
        from app.auth.auth_service import validate_access_token

        payload = validate_access_token("invalid.token.here")
        assert payload is None

    def test_validate_expired_token(self):
        """Test that expired tokens return None."""
        from datetime import timedelta
        from app.auth.auth_service import create_access_token, validate_access_token
        from app.config import settings
        import jwt as pyjwt

        # Create a token that's already expired
        to_encode = {"sub": "test-user", "exp": 0}
        expired_token = pyjwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        payload = validate_access_token(expired_token)
        assert payload is None

    def test_validate_wrong_type_token(self):
        """Test that token type validation works."""
        from app.auth.auth_service import create_refresh_token, validate_access_token

        refresh_token, _ = create_refresh_token({"sub": "test-user"})

        # Refresh token should fail access token validation
        payload = validate_access_token(refresh_token)
        assert payload is None


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_access_token(self):
        """Test refreshing an access token with a refresh token."""
        from app.auth.auth_service import create_access_token, create_refresh_token, refresh_access_token

        # Create initial token pair
        access_token = create_access_token({"sub": "test-user"})
        refresh_token, _ = create_refresh_token({"sub": "test-user"})

        # Refresh
        result = refresh_access_token(refresh_token)

        assert result is not None
        new_access_token, new_refresh_token = result
        assert new_access_token != access_token
        assert new_refresh_token != refresh_token

    def test_refresh_with_invalid_token(self):
        """Test refreshing with an invalid token returns None."""
        from app.auth.auth_service import refresh_access_token

        result = refresh_access_token("invalid.token.here")
        assert result is None

    def test_refresh_with_expired_token(self):
        """Test refreshing with an expired token returns None."""
        from app.auth.auth_service import create_access_token, create_refresh_token, refresh_access_token
        from app.config import settings
        import jwt as pyjwt

        # Create an expired refresh token
        to_encode = {"sub": "test-user", "type": "refresh", "exp": 0, "jti": "test-jti"}
        expired_token = pyjwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

        result = refresh_access_token(expired_token)
        assert result is None


class TestTokenRevoke:
    """Test token revocation and blacklist functionality."""

    def test_revoke_access_token(self):
        """Test revoking an access token."""
        from app.auth.auth_service import create_access_token, revoke_token, validate_access_token

        token = create_access_token({"sub": "test-user"})
        result = revoke_token(token)

        assert result is True

        # Token should now be invalid
        payload = validate_access_token(token)
        assert payload is None

    def test_revoke_refresh_token(self):
        """Test revoking a refresh token."""
        from app.auth.auth_service import create_refresh_token, revoke_refresh_token, validate_refresh_token

        token, _ = create_refresh_token({"sub": "test-user"})
        result = revoke_refresh_token(token)

        assert result is True

        # Token should now be invalid
        payload = validate_refresh_token(token)
        assert payload is None

    def test_revoke_invalid_token(self):
        """Test revoking an invalid token returns False."""
        from app.auth.auth_service import revoke_token

        result = revoke_token("invalid.token.here")
        assert result is False

    def test_blacklist_prevents_validation(self):
        """Test that blacklisted tokens cannot be validated."""
        from app.auth.auth_service import (
            create_access_token,
            revoke_token,
            validate_access_token,
            _is_token_blacklisted,
        )

        token = create_access_token({"sub": "test-user"})
        import jwt as pyjwt
        from app.config import settings

        payload = pyjwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        token_id = payload["jti"]

        # Should not be blacklisted initially
        assert _is_token_blacklisted(token_id) is False

        # Revoke the token
        revoke_token(token)

        # Should now be blacklisted
        assert _is_token_blacklisted(token_id) is True

        # Token validation should return None
        assert validate_access_token(token) is None


class TestTokenExpiry:
    """Test token expiration handling."""

    def test_access_token_expires_configured(self):
        """Test that access token expiration matches config."""
        from app.config import settings

        assert settings.access_token_expire_minutes > 0
        assert settings.access_token_expire_minutes <= 1440

    def test_refresh_token_expires_configured(self):
        """Test that refresh token expiration is configured."""
        from app.config import settings

        assert settings.refresh_token_expire_days > 0
        assert settings.refresh_token_expire_days <= 365

    def test_token_type_enforcement(self):
        """Test that token type is correctly enforced."""
        from app.auth.auth_service import create_access_token, create_refresh_token
        from app.auth.auth_service import validate_access_token, validate_refresh_token

        access_token = create_access_token({"sub": "test-user"})
        refresh_token, _ = create_refresh_token({"sub": "test-user"})

        # Access token should validate as access, not refresh
        assert validate_access_token(access_token) is not None
        # Refresh token should NOT validate as access
        assert validate_access_token(refresh_token) is None

        # Refresh token should validate as refresh, not access
        assert validate_refresh_token(refresh_token) is not None
        # Access token should NOT validate as refresh
        assert validate_refresh_token(access_token) is None


class TestTokenRotation:
    """Test token rotation during refresh."""

    def test_old_refresh_token_invalidated(self):
        """Test that the old refresh token is invalidated during rotation."""
        from app.auth.auth_service import create_access_token, create_refresh_token, refresh_access_token

        access_token = create_access_token({"sub": "test-user"})
        old_refresh_token, _ = create_refresh_token({"sub": "test-user"})

        # First refresh
        result = refresh_access_token(old_refresh_token)
        assert result is not None

        new_access, new_refresh = result

        # Try using old refresh token again
        second_result = refresh_access_token(old_refresh_token)

        # Old refresh token should be invalidated
        # The old token's jti should be blacklisted
        import jwt as pyjwt
        from app.config import settings
        from app.auth.auth_service import validate_refresh_token

        # The old token should now be invalid
        assert validate_refresh_token(old_refresh_token) is None


class TestAuthService:
    """Test auth service utility functions."""

    def test_get_current_user(self):
        """Test getting current user from token."""
        from app.auth.auth_service import create_access_token, get_current_user

        token = create_access_token({
            "sub": "test-user-123",
            "email": "test@example.com",
            "name": "Test User"
        })

        # Verify the token can decode user info
        import jwt as pyjwt
        from app.config import settings

        payload = pyjwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "test-user-123"
        assert payload["email"] == "test@example.com"
        assert payload["name"] == "Test User"