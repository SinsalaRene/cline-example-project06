"""
Pydantic schemas for Approval Workflows.
"""

from datetime import datetime
from typing import Optional, list
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    Create = "create"
    Update = "update"
    Delete = "delete"


class ApprovalStatus(str, Enum):
    Pending = "pending"
    Approved = "approved"
    Rejected = "rejected"
    Revoked = "revoked"
    Expired = "expired"


class ApprovalRole(str, Enum):
    WorkloadStakeholder = "workload_stakeholder"
    SecurityStakeholder = "security_stakeholder"


# --- Request Schemas ---

class ApprovalStepCreate(BaseModel):
    """Schema for creating an approval step."""
    approver_id: Optional[UUID] = None
    approver_role: ApprovalRole


class ApprovalRequestCreate(BaseModel):
    """Schema for creating an approval request."""
    rule_ids: list[UUID] = Field(..., min_length=1)
    change_type: ChangeType
    description: Optional[str] = None
    workload_id: Optional[UUID] = None
    required_approvals: int = Field(default=2, ge=1)
    approval_flow: str = "multi_level"


class ApprovalRequestApprove(BaseModel):
    """Schema for approving an approval request."""
    comment: Optional[str] = None


class ApprovalRequestReject(BaseModel):
    """Schema for rejecting an approval request."""
    comment: str


class ApprovalRequestComment(BaseModel):
    """Schema for adding a comment to an approval request."""
    comment: str


# --- Response Schemas ---

class ApprovalStepResponse(BaseModel):
    """Response schema for an approval step."""
    id: UUID
    approval_request_id: UUID
    approver_id: Optional[UUID] = None
    approver_role: ApprovalRole
    status: ApprovalStatus
    comments: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalRequestResponse(BaseModel):
    """Response schema for an approval request."""
    id: UUID
    rule_ids: list[UUID]
    change_type: ChangeType
    description: Optional[str] = None
    current_user_id: Optional[UUID] = None
    status: ApprovalStatus
    workload_id: Optional[UUID] = None
    required_approvals: int
    current_approval_stage: int
    approval_flow: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    approval_steps: Optional[list[ApprovalStepResponse]] = None

    model_config = {"from_attributes": True}


class ApprovalWorkflowDefinitionCreate(BaseModel):
    """Schema for creating an approval workflow definition."""
    name: str
    description: Optional[str] = None
    trigger_conditions: Optional[dict] = None
    required_roles: list[str] = Field(..., min_length=1)
    timeout_hours: int = Field(default=48, ge=1)


class ApprovalWorkflowDefinitionResponse(BaseModel):
    """Response schema for an approval workflow definition."""
    id: UUID
    name: str
    description: Optional[str] = None
    trigger_conditions: Optional[dict] = None
    required_roles: list[str]
    timeout_hours: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}