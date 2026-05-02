"""
Pydantic schemas for Users and Authentication.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# ---- Auth Schemas ----

class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    """Schema for login response with tokens."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class LogoutRequest(BaseModel):
    """Schema for logout request."""
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None


class TokenBlacklistRequest(BaseModel):
    """Schema for token blacklist request."""
    token: str = Field(..., description="Token to blacklist")
    token_type: str = Field(default="access", description="Type of token (access or refresh)")


class UserInfo(BaseModel):
    """Schema for authenticated user information."""
    object_id: UUID
    email: str
    display_name: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    is_active: bool = True

    model_config = {"from_attributes": True}


class UserRole(str, Enum):
    Owner = "owner"
    Admin = "admin"
    Developer = "developer"
    SecurityReader = "security_reader"
    NetworkAdmin = "network_admin"
    Viewer = "viewer"


# ---- Rate Limiting Schemas ----

class RateLimitInfo(BaseModel):
    """Schema for rate limit information."""
    limit: int
    remaining: int
    reset_in: int


# ---- User Management Schemas ----

class UserRoleAssignment(BaseModel):
    """Schema for user role assignment."""
    role: UserRole
    workload_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None


class UserRoleAssignmentResponse(BaseModel):
    """Response schema for user role assignment."""
    id: UUID
    user_id: UUID
    role: str
    workload_id: Optional[UUID] = None
    granted_by: Optional[UUID] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CreateUserRequest(BaseModel):
    """Schema for creating a user."""
    object_id: UUID
    email: str
    display_name: str
    given_name: Optional[str] = None
    surname: Optional[str] = None


class UpdateUserRequest(BaseModel):
    """Schema for updating a user."""
    display_name: Optional[str] = None
    given_name: Optional[str] = None
    surname: Optional[str] = None
    is_active: Optional[bool] = None