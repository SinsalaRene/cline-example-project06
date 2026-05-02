"""
Authentication API router with endpoints for login, refresh, logout, and token management.

This module provides OAuth 2.0 Bearer token-based authentication endpoints.
All endpoints (except ``/auth/login``) require a valid ``Bearer`` token in the
``Authorization`` header.

## Authentication Flow

The application uses a dual-token approach:

1. **Login** - Obtain an access token (short-lived) and refresh token (long-lived)
2. **Access** - Use the access token in the ``Authorization: Bearer <token>`` header
3. **Refresh** - Use the refresh token to obtain a new access token pair
4. **Logout** - Revoke the refresh token to invalidate the session

## Request Format

All endpoints that require authentication use the ``Bearer`` scheme::

    Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

For login, the request body must match the ``LoginRequest`` Pydantic schema::

    {
        "username": "admin",
        "password": "secure-password"
    }

For refresh and logout, the request body must match the ``RefreshTokenRequest`` schema::

    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
    }

## Response Format

Successful authentication responses follow this structure::

    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 1800,
        "token_type": "Bearer"
    }

## Error Codes

| Code         | Status | Description                                  |
|-------------|--------|----------------------------------------------|
| AUTH_REQUIRED    | 401  | Missing or invalid authentication token       |
| INVALID_CREDENTIALS | 401 | Invalid username or password                  |
| INVALID_TOKEN    | 401  | Token is invalid or expired                     |
| RATE_LIMIT       | 429  | Rate limit exceeded (brute-force protection)   |
| VALIDATION_ERROR | 422  | Request body failed Pydantic validation         |
| INTERNAL_ERROR   | 500  | Unexpected server-side error                    |

## Token Lifetimes

| Token Type    | Default Lifetime    | Storage           |
|---------------|---------------------|-------------------|
| Access Token  | 30 minutes          | Client-side       |
| Refresh Token | 7 days (default)    | Redis / Database  |
"""  # noqa: E501

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.auth_service import (
    create_access_token,
    create_refresh_token,
    refresh_access_token as refresh_token_impl,
    revoke_token,
    validate_refresh_token,
    validate_access_token,
    get_current_user,
    check_rate_limit,
    _get_rate_limit_key,
)
from app.database import get_db
from app.schemas.user import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserInfo,
    TokenBlacklistRequest,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Authentication Endpoints
# ============================================================================


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get tokens",
    description=(
        "Authenticate with username and password to receive access and refresh tokens.\n\n"
        "The access token is short-lived (30 minutes by default) and should be used "
        "for API requests. The refresh token is long-lived (7 days by default) and "
        "should be used to obtain new access tokens.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "username": "admin",\n'
        '  "password": "secure-password"\n'
        "}\n"
        "```\n\n"
        "**Example Response**:\n"
        "```json\n"
        "{\n"
        '  "access_token": "eyJhbGciOiJIUzI1NiIs...",\n'
        '  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",\n'
        '  "expires_in": 1800,\n'
        '  "token_type": "Bearer"\n'
        "}\n"
        "```\n\n"
        "**Rate Limited**: Maximum 10 attempts per minute per IP."
    ),
    responses={
        200: {
            "description": "Authentication successful - tokens issued",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                        "expires_in": 1800,
                        "token_type": "Bearer"
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Missing credentials",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid credentials: username and password are required"
                    }
                }
            },
        },
        429: {
            "description": "Rate limit exceeded - Too many login attempts",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Too many login attempts, please try again later."
                    }
                }
            },
        },
    },
)
async def login(
    request: LoginRequest,
    req: Request,
    db: Session = Depends(get_db)
) -> LoginResponse:
    """
    Authenticate user and return tokens.

    This endpoint accepts username/password credentials and returns both
    an access token (short-lived) and a refresh token (long-lived).

    Rate limited to prevent brute-force attacks (10 attempts per minute per IP).

    **Request Body**: Must contain ``username`` and ``password`` (required).

    **Response**: ``LoginResponse`` containing access token, refresh token,
    expiry time, and token type.
    """
    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    rate_key = _get_rate_limit_key(client_ip, "/auth/login")
    if not check_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts, please try again later.",
        )

    # TODO: In production, validate against actual user store / Entra ID
    # For development, accept any non-empty credentials
    if not request.username or not request.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials: username and password are required",
        )

    # In production, verify credentials against database
    # For demo, we accept any credentials
    user_data = {
        "sub": str(UUID(int=hash(request.username) % (2**128))),
        "username": request.username,
        "email": f"{request.username}@example.com",
        "name": request.username,
    }

    # Create access token (short-lived)
    access_token = create_access_token(data=user_data)
    access_token_expires_in = 30 * 60  # 30 minutes in seconds (aligns with config default)

    # Create refresh token (long-lived, stored separately)
    refresh_token, _ = create_refresh_token(data=user_data)

    logger.info(f"User '{request.username}' logged in successfully")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_token_expires_in,
        token_type="Bearer"
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description=(
        "Use a refresh token to obtain a new access token. Implements token rotation "
        "(the old refresh token is invalidated and a new one issued).\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."\n'
        "}\n"
        "```\n\n"
        "**Example Response**:\n"
        "```json\n"
        "{\n"
        '  "access_token": "eyJhbGciOiJIUzI1NiIs...",\n'
        '  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",\n'
        '  "expires_in": 1800,\n'
        '  "token_type": "Bearer"\n'
        "}\n"
        "```\n\n"
        "**Rate Limited**: Maximum 20 requests per minute per IP."
    ),
    responses={
        200: {
            "description": "Token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                        "expires_in": 1800,
                        "token_type": "Bearer"
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Invalid or expired refresh token",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid or expired refresh token"
                    }
                }
            },
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Too many refresh requests, please try again later."
                    }
                }
            },
        },
    },
)
async def refresh(
    request: RefreshTokenRequest,
    req: Request,
    db: Session = Depends(get_db)
) -> RefreshTokenResponse:
    """
    Refresh access token using a valid refresh token.

    This endpoint issues new access + refresh token pairs while invalidating
    the old refresh token (token rotation).

    Rate limited to prevent abuse (20 requests per minute per IP).

    **Request Body**: Must contain ``refresh_token`` (required).

    **Response**: ``RefreshTokenResponse`` with new access and refresh tokens.
    """
    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    rate_key = _get_rate_limit_key(client_ip, "/auth/refresh")
    if not check_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Too many refresh requests, please try again later.",
        )

    # Validate the refresh token
    payload = validate_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    # Get user_id from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token: missing user ID",
        )

    # Use the implementation function to handle rotation
    result = refresh_token_impl(request.refresh_token)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Failed to refresh token",
        )

    new_access_token, new_refresh_token = result
    access_token_expires_in = 30 * 60  # 30 minutes in seconds

    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=access_token_expires_in,
        token_type="Bearer"
    )


@router.post(
    "/logout",
    summary="Logout and revoke token",
    description=(
        "Revoke the provided refresh token to logout. Once revoked, the refresh "
        "token cannot be used to obtain new access tokens.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."\n'
        "}\n"
        "```\n\n"
        "**Example Response**:\n"
        "```json\n"
        "{\n"
        '  "message": "Successfully logged out",\n'
        '  "token_revoked": true\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Token revoked",
                            "value": {
                                "message": "Successfully logged out",
                                "token_revoked": True
                            }
                        },
                        "already_expired": {
                            "summary": "Token already expired",
                            "value": {
                                "message": "Token already expired or invalid",
                                "token_revoked": False
                            }
                        }
                    }
                }
            },
        },
    },
)
async def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Logout by revoking the refresh token.

    The refresh token is added to the blacklist and can no longer be used
    to obtain new access tokens.

    **Request Body**: Must contain ``refresh_token`` (required).

    **Response**: Dictionary with ``message`` and ``token_revoked`` boolean.
    """
    revoked = revoke_token(request.refresh_token)
    if revoked:
        logger.info("Refresh token revoked successfully")

    return {"message": "Successfully logged out", "token_revoked": revoked}


@router.post(
    "/revoke",
    summary="Revoke any token",
    description=(
        "Revoke an access or refresh token by adding it to the blacklist.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "token": "eyJhbGciOiJIUzI1NiIs...",\n'
        '  "token_type": "refresh"\n'
        "}\n"
        "```\n\n"
        "**Example Response**:\n"
        "```json\n"
        "{\n"
        '  "message": "Refresh token revoked",\n'
        '  "token_type": "refresh",\n'
        '  "revoked": true\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Token revoked successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Token revoked",
                            "value": {
                                "message": "Token revoked",
                                "token_type": "access",
                                "revoked": True
                            }
                        }
                    }
                }
            },
        },
    },
)
async def revoke(
    request: TokenBlacklistRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Revoke a token (access or refresh).

    The token is added to the blacklist and can no longer be used.

    **Request Body**: Must contain ``token`` (required) and ``token_type``
    (``"access"`` or ``"refresh"``).

    **Response**: Dictionary with ``message``, ``token_type``, and ``revoked`` fields.
    """
    revoked = revoke_token(request.token)
    if revoked:
        logger.info(f"Token of type '{request.token_type}' revoked")
    else:
        logger.warning(f"Failed to revoke token of type '{request.token_type}'")

    return {
        "message": f"{'Token' if request.token_type == 'access' else 'Refresh token'} revoked"
                   if revoked else "Token already expired or invalid",
        "token_type": request.token_type,
        "revoked": revoked
    }


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user info",
    description=(
        "Get information about the currently authenticated user.\n\n"
        "Requires a valid access token in the ``Authorization: Bearer <token>`` header.\n\n"
        "**Example Request**: ``GET /auth/me`` with ``Authorization: Bearer <token>``\n\n"
        "**Example Response**:\n"
        "```json\n"
        "{\n"
        '  "sub": "1234567890abcdef",\n'
        '  "username": "admin",\n'
        '  "email": "admin@example.com",\n'
        '  "name": "Admin User",\n'
        '  "roles": ["admin"]\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "sub": "1234567890abcdef",
                        "username": "admin",
                        "email": "admin@example.com",
                        "name": "Admin User",
                        "roles": ["admin"]
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing or invalid token",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Could not validate credentials"
                    }
                }
            },
        },
    },
)
async def get_me(
    current_user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """
    Get information about the currently authenticated user.

    Requires a valid access token in the Authorization header.

    **Authentication**: Bearer token required.

    **Response**: ``UserInfo`` containing user ``sub``, ``username``, ``email``,
    ``name``, and ``roles``.
    """
    return current_user