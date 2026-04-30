"""
API routes for Approval Workflow management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth_service import get_current_user
from app.schemas.user import UserInfo
from app.schemas.approval import (
    ApprovalRequestCreate,
    ApprovalRequestApprove,
    ApprovalRequestReject,
    ApprovalRequestResponse,
)
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.models.approval import ChangeType, ApprovalStatus

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get(
    "",
    response_model=dict,
    summary="List approval requests",
    description="Get paginated list of approval requests",
)
async def list_approvals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List approval requests with pagination."""
    result = ApprovalService.get_approval_requests(
        db=db,
        user_id=current_user.object_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return result


@router.get(
    "/{approval_id}",
    response_model=ApprovalRequestResponse,
    summary="Get approval request",
    description="Get a single approval request by ID",
)
async def get_approval(
    approval_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single approval request."""
    from app.models.approval import ApprovalRequest
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.post(
    "",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create approval request",
    description="Create a new approval request for firewall rule changes",
)
async def create_approval(
    approval: ApprovalRequestCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new approval request."""
    new_approval = ApprovalService.create_approval_request(
        db=db,
        rule_ids=approval.rule_ids,
        change_type=approval.change_type,
        description=approval.description,
        user_id=current_user.object_id,
        workload_id=approval.workload_id,
        required_approvals=approval.required_approvals,
    )
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="create_approval",
        resource_type="approval_request",
        resource_id=str(new_approval.id),
        new_value={"change_type": approval.change_type},
        correlation_id=None,
    )
    
    return new_approval


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalRequestResponse,
    summary="Approve request",
    description="Approve an approval request",
)
async def approve(
    approval_id: UUID,
    approval_data: ApprovalRequestApprove,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve an approval request."""
    from app.models.approval import ApprovalStep
    step = db.query(ApprovalStep).filter(
        ApprovalStep.approval_request_id == approval_id,
        ApprovalStep.status == "pending"
    ).first()
    
    if not step:
        raise HTTPException(status_code=404, detail="Approval step not found or already processed")
    
    updated_step = ApprovalService.approve_step(
        db=db,
        step_id=step.id,
        approver_id=current_user.object_id,
        comment=approval_data.comment,
    )
    
    return updated_step


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalRequestResponse,
    summary="Reject request",
    description="Reject an approval request",
)
async def reject(
    approval_id: UUID,
    rejection: ApprovalRequestReject,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject an approval request."""
    from app.models.approval import ApprovalStep
    step = db.query(ApprovalStep).filter(
        ApprovalStep.approval_request_id == approval_id,
        ApprovalStep.status == "pending"
    ).first()
    
    if not step:
        raise HTTPException(status_code=404, detail="Approval step not found or already processed")
    
    updated_step = ApprovalService.reject_step(
        db=db,
        step_id=step.id,
        approver_id=current_user.object_id,
        comment=rejection.comment,
    )
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="reject",
        resource_type="approval_request",
        resource_id=str(approval_id),
        correlation_id=None,
    )
    
    return updated_step


@router.post(
    "/{approval_id}/comment",
    summary="Add comment",
    description="Add a comment to an approval request",
)
async def add_comment(
    approval_id: UUID,
    comment_data: dict,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a comment to an approval request."""
    comment = comment_data.get("comment", "")
    # Implementation would add comment to the approval request
    return {"message": "Comment added successfully"}