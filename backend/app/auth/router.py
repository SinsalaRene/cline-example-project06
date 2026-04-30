"""
Authentication router with endpoints for login, refresh, logout, and token management.

Endpoints:
- POST /auth/login - Authenticate and receive access + refresh tokens
- POST /auth/refresh - Obtain new access token using refresh token
- POST /auth/logout - Revoke refresh token
- POST /auth/revoke - Revoke any token (access or refresh)
- GET /auth/me - Get current authenticated user info
"""

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


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get tokens",
    description="Authenticate with username and password to receive access and refresh tokens."
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

    Rate limited to prevent brute-force attacks.
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
    description="Use a refresh token to obtain a new access token. Implements token rotation."
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

    Rate limited to prevent abuse.
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
    description="Revoke the provided refresh token to logout."
)
async def logout(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Logout by revoking the refresh token.

    The refresh token is added to the blacklist and can no longer be used
    to obtain new access tokens.
    """
    revoked = revoke_token(request.refresh_token)
    if revoked:
        logger.info("Refresh token revoked successfully")

    return {"message": "Successfully logged out", "token_revoked": revoked}


@router.post(
    "/revoke",
    summary="Revoke any token",
    description="Revoke an access or refresh token by adding it to the blacklist."
)
async def revoke(
    request: TokenBlacklistRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Revoke a token (access or refresh).

    The token is added to the blacklist and can no longer be used.
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
    description="Get information about the currently authenticated user."
)
async def get_me(
    current_user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """
    Get information about the currently authenticated user.

    Requires a valid access token in the Authorization header.
    """
    return current_user