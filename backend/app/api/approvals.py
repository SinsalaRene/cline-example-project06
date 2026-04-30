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
    BulkApproveRequest,
    BulkRejectRequest,
    EscalationRequest,
    PendingApprovalCountResponse,
    BulkApproveResponse,
    BulkRejectResponse,
    TimeoutResultResponse,
)
from app.models.approval import ApprovalRole
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
    from app.models.approval import ApprovalComment
    from datetime import datetime, timezone
    comment = comment_data.get("comment", "")
    if not comment:
        raise HTTPException(status_code=422, detail="Comment is required")
    
    approval_comment = ApprovalComment(
        id=uuid4(),
        approval_request_id=approval_id,
        user_id=current_user.object_id,
        comment=comment,
        created_at=datetime.now(timezone.utc),
    )
    db.add(approval_comment)
    db.commit()
    
    return {"message": "Comment added successfully"}


@router.get(
    "/{approval_id}/history",
    response_model=dict,
    summary="Get approval history",
    description="Get full history of an approval request including comments and steps",
)
async def get_approval_history(
    approval_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full history of an approval request."""
    from app.models.approval import ApprovalRequest, ApprovalStep, ApprovalComment
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    # Get approval steps
    steps = db.query(ApprovalStep).filter(
        ApprovalStep.approval_request_id == approval_id
    ).all()
    
    # Get comments
    comment_query = db.query(ApprovalComment).filter(
        ApprovalComment.approval_request_id == approval_id
    ).order_by(ApprovalComment.created_at.desc())
    
    # Paginate comments
    total_comments = comment_query.count()
    comments = comment_query.skip(max(0, page - 1) * page_size).limit(page_size).all()
    
    return {
        "approval": approval,
        "steps": steps,
        "comments": {
            "total": total_comments,
            "page": page,
            "page_size": page_size,
            "items": comments,
        }
    }


@router.post(
    "/bulk/approve",
    response_model=dict,
    summary="Bulk approve",
    description="Approve multiple approval requests in bulk",
)
async def bulk_approve(
    bulk_data: BulkApproveRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk approve multiple approval requests."""
    service = ApprovalService()
    result = service.bulk_approve(
        db=db,
        approval_ids=bulk_data.approval_ids,
        approver_id=current_user.object_id,
        comment=bulk_data.comment,
        required_approvals=bulk_data.required_approvals,
    )
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="bulk_approve",
        resource_type="approval_request",
        resource_id=str(len(bulk_data.approval_ids)),
        new_value={"approved_count": len(result.get("approved_ids", []))},
        correlation_id=None,
    )
    
    return result


@router.post(
    "/bulk/reject",
    response_model=dict,
    summary="Bulk reject",
    description="Reject multiple approval requests in bulk",
)
async def bulk_reject(
    bulk_data: BulkRejectRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk reject multiple approval requests."""
    service = ApprovalService()
    result = service.bulk_reject(
        db=db,
        approval_ids=bulk_data.approval_ids,
        approver_id=current_user.object_id,
        comment=bulk_data.comment,
    )
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="bulk_reject",
        resource_type="approval_request",
        resource_id=str(len(bulk_data.approval_ids)),
        new_value={"rejected_count": len(result.get("rejected_ids", []))},
        correlation_id=None,
    )
    
    return result


@router.post(
    "/{approval_id}/escalate",
    response_model=ApprovalRequestResponse,
    summary="Escalate approval",
    description="Escalate an approval request to a higher role",
)
async def escalate_approval(
    approval_id: UUID,
    escalation: EscalationRequest,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Escalate an approval request to a higher role."""
    service = ApprovalService()
    result = service.escalate_approval(
        db=db,
        approval_id=approval_id,
        approver_id=current_user.object_id,
        new_approver_role=escalation.target_role,
        reason=escalation.reason or "",
    )
    
    return result


@router.post(
    "/handle-timeouts",
    response_model=dict,
    summary="Handle timeouts",
    description="Handle timeouts for all pending approval requests",
)
async def handle_timeouts(
    timeout_hours: Optional[int] = Query(None, description="Override timeout in hours"),
    escalate_to_role: Optional[str] = Query(None, description="Role to escalate to"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle timeouts for all pending approval requests."""
    role = ApprovalRole(escalate_to_role) if escalate_to_role else None
    service = ApprovalService()
    result = service.handle_timeout_escalation(
        db=db,
        timeout_hours=timeout_hours,
        escalate_to_role=role,
    )
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="handle_timeouts",
        resource_type="approval_request",
        resource_id="bulk",
        new_value={
            "expired_count": result.get("expired_count", 0),
            "escalated_count": result.get("escalated_count", 0),
        },
        correlation_id=None,
    )
    
    return result


@router.get(
    "/pending/count",
    response_model=PendingApprovalCountResponse,
    summary="Get pending approval count",
    description="Get count of pending approval requests for the current user",
)
async def get_pending_count(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get count of pending approval requests."""
    service = ApprovalService()
    count = service.get_pending_approval_count(
        db=db,
        user_id=current_user.object_id,
    )
    
    return {"count": count}
