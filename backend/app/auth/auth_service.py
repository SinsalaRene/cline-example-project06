"""
Authentication service for handling JWT tokens, refresh tokens, and rate limiting.

Provides:
- Access token creation and validation
- Refresh token creation and validation
- Token blacklist/revoke functionality
- Rate limiting for authentication endpoints
"""

import secrets
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from uuid import UUID
import jose.jwt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.user import UserInfo


logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()

# In-memory token blacklist (use Redis in production)
_token_blacklist: Dict[str, datetime] = {}

# In-memory rate limit tracking: {(ip, endpoint): [timestamps]}
_rate_limit_store: Dict[str, list] = {}


class TokenPair(BaseModel):
    """Response model for token pair."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class RefreshTokenData(BaseModel):
    """Data stored for a refresh token."""
    user_id: str
    token_jti: str
    exp: float
    created_at: float


def _generate_token_id() -> str:
    """Generate a unique JWT ID (jti) for token identification."""
    return secrets.token_hex(16)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token.
        expires_delta: Optional timedelta to override the default expiration.

    Returns:
        str: Encoded JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "jti": _generate_token_id(),  # Unique token ID
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict) -> Tuple[str, str]:
    """Create a JWT refresh token and return (refresh_token, token_id).

    The refresh token encodes user info and a unique jti for revocation tracking.

    Args:
        data: Dictionary containing user identification data.

    Returns:
        Tuple[str, str]: A tuple of (refresh_token, token_id).
    """
    token_id = _generate_token_id()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {
        **data,
        "exp": expire,
        "jti": token_id,
        "type": "refresh"
    }
    encoded_token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_token, token_id


def validate_token(token: str, token_type: Optional[str] = None) -> Optional[dict]:
    """Validate a JWT token and return the payload.

    Args:
        token: The JWT token string to validate.
        token_type: If specified, verify the token type matches (e.g., "access" or "refresh").

    Returns:
        Optional[dict]: The token payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        # Check if token is blacklisted
        token_id = payload.get("jti")
        if token_id and _is_token_blacklisted(token_id):
            return None

        # Check token type if specified
        if token_type and payload.get("type") != token_type:
            return None

        return payload
    except JWTError:
        return None


def validate_access_token(token: str) -> Optional[dict]:
    """Validate an access token specifically.

    Args:
        token: The access token string to validate.

    Returns:
        Optional[dict]: The token payload if valid, None otherwise.
    """
    return validate_token(token, token_type="access")


def validate_refresh_token(token: str) -> Optional[dict]:
    """Validate a refresh token specifically.

    Args:
        token: The refresh token string to validate.

    Returns:
        Optional[dict]: The token payload if valid, None otherwise.
    """
    return validate_token(token, token_type="refresh")


def revoke_token(token: str) -> bool:
    """Revoke/add a token to the blacklist.

    The token's jti is stored with its expiration time. Once expired,
    it is automatically removed from the blacklist.

    Args:
        token: The JWT token string to revoke.

    Returns:
        bool: True if the token was successfully revoked, False otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        token_id = payload.get("jti")
        exp = payload.get("exp")

        if token_id and exp:
            _token_blacklist[token_id] = datetime.fromtimestamp(
                exp, tz=timezone.utc
            )
            logger.info(f"Token {token_id} revoked until {exp}")
            return True
        return False
    except JWTError:
        return False


def revoke_refresh_token(refresh_token: str) -> bool:
    """Revoke a refresh token by adding it to the blacklist.

    Args:
        refresh_token: The refresh token string to revoke.

    Returns:
        bool: True if the token was successfully revoked, False otherwise.
    """
    return revoke_token(refresh_token)


def _is_token_blacklisted(token_id: str) -> bool:
    """Check if a token ID is in the blacklist.

    Args:
        token_id: The JWT ID to check.

    Returns:
        bool: True if the token is blacklisted, False otherwise.
    """
    if token_id in _token_blacklist:
        expiry = _token_blacklist[token_id]
        # Clean up expired entries
        if datetime.now(timezone.utc) >= expiry:
            del _token_blacklist[token_id]
            return False
        return True
    return False


def blacklist_token(token_id: str, expiration: datetime) -> None:
    """Add a token ID to the blacklist.

    Args:
        token_id: The JWT ID to blacklist.
        expiration: When the token expires (for cleanup).
    """
    _token_blacklist[token_id] = expiration


def refresh_access_token(old_refresh_token: str) -> Optional[Tuple[str, str]]:
    """Use a refresh token to obtain a new access token and refresh token pair.

    Implements token rotation: the old refresh token is invalidated and a new
    pair of tokens is issued.

    Args:
        old_refresh_token: The current refresh token.

    Returns:
        Optional[Tuple[str, str]]: A tuple of (new_access_token, new_refresh_token)
                                  or None if the refresh token is invalid.
    """
    payload = validate_refresh_token(old_refresh_token)
    if not payload:
        return None

    # Get user data from the refresh token payload
    user_id = payload.get("sub")
    if not user_id:
        return None

    # Revoke the old refresh token (add to blacklist)
    token_id = payload.get("jti")
    if token_id:
        _token_blacklist[token_id] = datetime.fromtimestamp(
            payload.get("exp", 0), tz=timezone.utc
        ) if payload.get("exp") else datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    # Create new token pair
    new_access_token = create_access_token({"sub": user_id})
    new_refresh_token, _ = create_refresh_token({"sub": user_id})

    return new_access_token, new_refresh_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> UserInfo:
    """
    Dependency to get the current authenticated user.
    Validates the JWT token and returns user info.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Check if token is blacklisted
        token_id = payload.get("jti")
        if token_id and _is_token_blacklisted(token_id):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # In production, this would validate against Entra ID
    # For now, we create a UserInfo from the token payload
    return UserInfo(
        object_id=UUID(user_id) if user_id else UUID(int=0),
        email=payload.get("email", ""),
        display_name=payload.get("name", ""),
        roles=[],
        is_active=True
    )


# ---- Rate Limiting ----

def _get_rate_limit_key(ip_address: str, endpoint: str) -> str:
    """Generate a rate limit key from IP and endpoint."""
    return f"{ip_address}:{endpoint}"


def check_rate_limit(key: str, limit: int = None, window: int = None) -> bool:
    """Check if a request is within the rate limit.

    Args:
        key: The rate limit key (typically IP + endpoint).
        limit: Maximum requests allowed in the window. Defaults to settings.auth_rate_limit_per_minute.
        window: Time window in seconds. Defaults to settings.auth_rate_limit_window.

    Returns:
        bool: True if within rate limit, False if exceeded.
    """
    if not settings.rate_limit_enabled:
        return True

    limit = limit or settings.auth_rate_limit_per_minute
    window = window or settings.auth_rate_limit_window
    now = time.time()

    # Clean old entries for this key
    if key in _rate_limit_store:
        _rate_limit_store[key] = [
            ts for ts in _rate_limit_store[key]
            if now - ts < window
        ]

    # Check if limit exceeded
    if key in _rate_limit_store and len(_rate_limit_store[key]) >= limit:
        return False

    # Record this request
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    _rate_limit_store[key].append(now)

    return True


def create_rate_limit_middleware():
    """Create a rate limiting middleware for auth endpoints.

    Returns:
        A middleware function that can be applied to FastAPI routes.
    """
    from fastapi import Request

    def rate_limit_middleware(request: Request, call_next):
        """Middleware function that enforces rate limits."""
        # Only apply to auth endpoints
        path = request.url.path
        if not any(auth_path in path for auth_path in ["/auth/login", "/auth/refresh"]):
            return call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        endpoint = path
        key = _get_rate_limit_key(client_ip, endpoint)

        if not check_rate_limit(key):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests, please try again later.",
                    "retry_after": settings.auth_rate_limit_window
                },
                headers={"Retry-After": str(settings.auth_rate_limit_window)}
            )

        return call_next(request)

    return rate_limit_middleware


def cleanup_blacklist() -> int:
    """Remove expired entries from the blacklist.

    Returns:
        int: Number of entries cleaned up.
    """
    now = datetime.now(timezone.utc)
    expired_keys = []

    for token_id, expiry in _token_blacklist.items():
        if now >= expiry:
            expired_keys.append(token_id)

    for key in expired_keys:
        del _token_blacklist[key]

    return len(expired_keys)


def cleanup_rate_limits() -> int:
    """Remove expired entries from the rate limit store.

    Returns:
        int: Number of entries cleaned up.
    """
    now = time.time()
    window = settings.auth_rate_limit_window or 60
    cleaned = 0

    keys_to_remove = []
    for key, timestamps in _rate_limit_store.items():
        # Remove old timestamps
        _rate_limit_store[key] = [
            ts for ts in timestamps if now - ts < window
        ]
        if not _rate_limit_store[key]:
            keys_to_remove.append(key)
            cleaned += 1

    for key in keys_to_remove:
        del _rate_limit_store[key]

    return cleaned