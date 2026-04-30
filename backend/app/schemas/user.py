"""
Pydantic schemas for Users and Authentication.
"""

from datetime import datetime
from typing import Optional, list
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    Owner = "owner"
    Admin = "admin"
    Developer = "developer"
    SecurityReader = "security_reader"
    NetworkAdmin = "network_admin"
    Viewer = "viewer"


# --- Auth Schemas ---

class UserInfo(BaseModel):
    """Schema for authenticated user information."""
    object_id: UUID
    email: str
    display_name: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., min_length=1)


# --- User Management Schemas ---

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