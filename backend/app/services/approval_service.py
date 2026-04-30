"""
Approval workflow service for managing multi-level approvals.
"""

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.approval import (
    ApprovalRequest, ApprovalStep, ApprovalStatus, ApprovalRole,
    ChangeType, ApprovalWorkflowDefinition
)


class ApprovalService:
    """Service for approval workflow management."""
    
    @staticmethod
    def create_approval_request(
        db: Session,
        rule_ids: list[UUID],
        change_type: ChangeType,
        description: str,
        user_id: UUID,
        workload_id: UUID = None,
        required_approvals: int = 2,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        approval_request = ApprovalRequest(
            rule_ids=rule_ids,
            change_type=change_type,
            description=description,
            current_user_id=user_id,
            workload_id=workload_id,
            required_approvals=required_approvals,
        )
        db.add(approval_request)
        db.flush()
        
        # Create approval steps based on workflow definition
        steps = ApprovalService._create_approval_steps(db, approval_request)
        
        db.commit()
        db.refresh(approval_request)
        return approval_request
    
    @staticmethod
    def _create_approval_steps(db: Session, approval_request: ApprovalRequest) -> list[ApprovalStep]:
        """Create approval steps for the approval request."""
        steps = []
        
        # Stage 1: Workload Stakeholder
        step1 = ApprovalStep(
            approval_request_id=approval_request.id,
            approver_role=ApprovalRole.WorkloadStakeholder,
            status=ApprovalStatus.Pending,
        )
        db.add(step1)
        steps.append(step1)
        
        # Stage 2: Security Stakeholder
        step2 = ApprovalStep(
            approval_request_id=approval_request.id,
            approver_role=ApprovalRole.SecurityStakeholder,
            status=ApprovalStatus.Pending,
        )
        db.add(step2)
        steps.append(step2)
        
        db.flush()
        return steps
    
    @staticmethod
    def approve_step(
        db: Session,
        step_id: UUID,
        approver_id: UUID,
        comment: str = None,
    ) -> ApprovalStep:
        """Approve a step in the approval workflow."""
        step = db.query(ApprovalStep).filter(ApprovalStep.id == step_id).first()
        if not step:
            raise ValueError(f"Approval step {step_id} not found")
        
        if step.status == ApprovalStatus.Approved:
            raise ValueError(f"Step {step_id} is already approved")
        
        step.status = ApprovalStatus.Approved
        step.approver_id = approver_id
        step.comments = comment
        step.approved_at = datetime.now(timezone.utc)
        
        # Update the parent approval request
        approval_request = step.approval_request
        
        # Check if all steps at current stage are approved
        current_stage = ApprovalService._get_current_stage(approval_request, db)
        
        if current_stage:
            current_stage.status = ApprovalStatus.Approved
            approval_request.current_approval_stage += 1
        else:
            # All stages complete
            approval_request.status = ApprovalStatus.Approved
            approval_request.completed_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(step)
        return step
    
    @staticmethod
    def reject_step(
        db: Session,
        step_id: UUID,
        approver_id: UUID,
        comment: str,
    ) -> ApprovalStep:
        """Reject a step in the approval workflow."""
        step = db.query(ApprovalStep).filter(ApprovalStep.id == step_id).first()
        if not step:
            raise ValueError(f"Approval step {step_id} not found")
        
        step.status = ApprovalStatus.Rejected
        step.approver_id = approver_id
        step.comments = comment
        
        # Reject the entire approval request
        approval_request = step.approval_request
        approval_request.status = ApprovalStatus.Rejected
        approval_request.completed_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(step)
        return step
    
    @staticmethod
    def _get_current_stage(approval_request: ApprovalRequest, db: Session):
        """Get the current pending approval stage."""
        steps = db.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == approval_request.id,
            ApprovalStep.status == ApprovalStatus.Pending
        ).order_by(ApprovalStep.created_at).all()
        
        return steps[0] if steps else None
    
    @staticmethod
    def get_approval_requests(
        db: Session,
        user_id: UUID = None,
        status: str = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get approval requests with filtering and pagination."""
        query = db.query(ApprovalRequest)
        
        if user_id:
            query = query.filter(
                (ApprovalRequest.current_user_id == user_id) |
                (ApprovalRequest.workload_id == user_id)
            )
        if status:
            query = query.filter(ApprovalRequest.status == status)
        
        total = query.count()
        query = query.order_by(desc(ApprovalRequest.created_at))
        
        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }