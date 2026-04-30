"""
Approval workflow service for managing multi-level approvals.

Refactored to use class-based dependency injection pattern for proper
FastAPI integration with dependency injection support.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.approval import (
    ApprovalRequest, ApprovalStep, ApprovalStatus, ApprovalRole,
    ChangeType, ApprovalWorkflowDefinition
)

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for approval workflow management with dependency injection.

    This service manages multi-level approval workflows with support for
    step-based approval tracking, timeout handling, and escalation.

    Usage in FastAPI:
        @app.post("/approvals")
        def create_approval(db: Session = Depends(get_db)):
            service = ApprovalService()
            return service.create_approval_request(db, ...)
    """

    def __init__(self, logger_name: str = __name__, default_timeout_hours: int = 48):
        """Initialize the ApprovalService.

        Args:
            logger_name: Name for the logger instance.
            default_timeout_hours: Default timeout for approval requests in hours.
        """
        self._logger = logging.getLogger(logger_name)
        self._default_timeout_hours = default_timeout_hours
        self._logger.debug("ApprovalService initialized with timeout=%dh", default_timeout_hours)

    def create_approval_request(
        self,
        db: Session,
        rule_ids: list[UUID],
        change_type: ChangeType,
        description: str,
        user_id: UUID,
        workload_id: Optional[UUID] = None,
        required_approvals: int = 2,
    ) -> ApprovalRequest:
        """Create a new approval request with initial approval steps.

        Args:
            db: SQLAlchemy database session.
            rule_ids: List of UUIDs of rules requiring approval.
            change_type: Type of change being requested.
            description: Description of the change.
            user_id: UUID of the user creating the request.
            workload_id: Optional UUID of associated workload.
            required_approvals: Number of approvals required.

        Returns:
            The created ApprovalRequest object.

        Raises:
            ValueError: If rule_ids is empty or description is blank.
            Exception: Database commit or connection errors.
        """
        self._logger.info("create_approval_request called: change_type=%s, rules=%d, user=%s",
                          change_type, len(rule_ids), user_id)

        if not rule_ids:
            raise ValueError("At least one rule ID is required")
        if not description or not description.strip():
            raise ValueError("Approval description is required")
        if required_approvals < 1:
            raise ValueError("required_approvals must be at least 1")

        # Convert UUIDs to strings for JSON serialization
        rule_ids_str = [str(r) for r in rule_ids]
        approval_request = ApprovalRequest(
            rule_ids=json.dumps(rule_ids_str),
            change_type=change_type,
            description=description,
            current_user_id=user_id,
            workload_id=workload_id,
            required_approvals=required_approvals,
        )
        db.add(approval_request)
        db.flush()

        steps = self._create_approval_steps(db, approval_request)

        try:
            db.commit()
            db.refresh(approval_request)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to create approval request for change_type=%s", change_type)
            raise

        self._logger.info("Created approval request %s with %d steps", approval_request.id, len(steps))
        return approval_request

    def _create_approval_steps(self, db: Session, approval_request: ApprovalRequest) -> list[ApprovalStep]:
        """Create approval steps for the approval request.

        Creates a two-stage approval workflow:
        1. Workload Stakeholder approval
        2. Security Stakeholder approval

        Args:
            db: SQLAlchemy database session.
            approval_request: The approval request to create steps for.

        Returns:
            List of created ApprovalStep objects.
        """
        self._logger.info("Creating approval steps for request %s", approval_request.id)
        steps = []

        # Stage 1: Workload Stakeholder
        step1 = ApprovalStep(
            approval_request_id=approval_request.id,
            approver_role=ApprovalRole.WorkloadStakeholder,
            status=ApprovalStatus.Pending,
        )
        db.add(step1)
        steps.append(step1)
        self._logger.debug("Created step 1 (WorkloadStakeholder) for request %s", approval_request.id)

        # Stage 2: Security Stakeholder
        step2 = ApprovalStep(
            approval_request_id=approval_request.id,
            approver_role=ApprovalRole.SecurityStakeholder,
            status=ApprovalStatus.Pending,
        )
        db.add(step2)
        steps.append(step2)
        self._logger.debug("Created step 2 (SecurityStakeholder) for request %s", approval_request.id)

        return steps

    def approve_step(
        self,
        db: Session,
        step_id: UUID,
        approver_id: UUID,
        comment: Optional[str] = None,
    ) -> ApprovalStep:
        """Approve a step in the approval workflow.

        Args:
            db: SQLAlchemy database session.
            step_id: UUID of the approval step to approve.
            approver_id: UUID of the approver.
            comment: Optional approval comment.

        Returns:
            The updated ApprovalStep object.

        Raises:
            ValueError: If step not found or already approved.
        """
        self._logger.info("approve_step called for step_id %s by approver %s", step_id, approver_id)
        step = db.query(ApprovalStep).filter(ApprovalStep.id == step_id).first()
        if not step:
            msg = f"Approval step {step_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)

        if step.status == ApprovalStatus.Approved:
            msg = f"Step {step_id} is already approved"
            self._logger.warning(msg)
            raise ValueError(msg)

        step.status = ApprovalStatus.Approved
        step.approver_id = approver_id
        step.comments = comment
        step.approved_at = datetime.now(timezone.utc)
        self._logger.info("Approved step %s", step_id)

        approval_request = step.approval_request
        current_stage = self._get_current_pending_step(approval_request, db)

        if current_stage:
            self._logger.info("Next pending step %s for request %s", current_stage.id, approval_request.id)
        else:
            # All stages complete
            approval_request.status = ApprovalStatus.Approved
            approval_request.completed_at = datetime.now(timezone.utc)
            db.flush()
            self._logger.info("Approval request %s fully approved", approval_request.id)

        try:
            db.commit()
            db.refresh(step)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to commit approval for step %s", step_id)
            raise

        return step

    def reject_step(
        self,
        db: Session,
        step_id: UUID,
        approver_id: UUID,
        comment: str,
    ) -> ApprovalStep:
        """Reject a step in the approval workflow.

        Args:
            db: SQLAlchemy database session.
            step_id: UUID of the approval step to reject.
            approver_id: UUID of the approver.
            comment: Required rejection comment.

        Returns:
            The updated ApprovalStep object.

        Raises:
            ValueError: If step not found or comment is empty.
        """
        self._logger.info("reject_step called for step_id %s by approver %s", step_id, approver_id)

        if not comment or not comment.strip():
            raise ValueError("Rejection comment is required")

        step = db.query(ApprovalStep).filter(ApprovalStep.id == step_id).first()
        if not step:
            msg = f"Approval step {step_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)

        step.status = ApprovalStatus.Rejected
        step.approver_id = approver_id
        step.comments = comment
        step.approved_at = datetime.now(timezone.utc)

        approval_request = step.approval_request
        approval_request.status = ApprovalStatus.Rejected
        approval_request.completed_at = datetime.now(timezone.utc)

        try:
            db.commit()
            db.refresh(step)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to reject step %s", step_id)
            raise

        self._logger.info("Rejected step %s for request %s", step_id, approval_request.id)
        return step

    def _get_current_pending_step(self, approval_request: ApprovalRequest, db: Session):
        """Get the next pending approval step for the request.

        Args:
            approval_request: The approval request to check.
            db: SQLAlchemy database session.

        Returns:
            The next pending ApprovalStep, or None if all steps are complete.
        """
        steps = db.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == approval_request.id,
            ApprovalStep.status == ApprovalStatus.Pending
        ).order_by(ApprovalStep.created_at).all()

        return steps[0] if steps else None

    def check_and_expire_pending_approvals(self, db: Session) -> int:
        """Check for approval requests that have exceeded their timeout.

        Args:
            db: SQLAlchemy database session.

        Returns:
            Number of expired approval requests.
        """
        self._logger.info("Checking for expired approval requests (timeout=%dh)", self._default_timeout_hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self._default_timeout_hours)
        expired_count = 0

        try:
            pending_requests = db.query(ApprovalRequest).filter(
                ApprovalRequest.status == ApprovalStatus.Pending,
                ApprovalRequest.created_at < cutoff_time,
            ).all()

            for request in pending_requests:
                request.status = ApprovalStatus.Expired
                request.completed_at = datetime.now(timezone.utc)
                self._logger.info("Expired approval request %s after %d hours",
                                request.id, self._default_timeout_hours)
                expired_count += 1

            if expired_count:
                db.commit()

            self._logger.info("Expired %d approval requests", expired_count)
        except Exception:
            db.rollback()
            self._logger.exception("Error expiring approval requests")
            raise

        return expired_count

    def get_approval_requests(
        self,
        db: Session,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get approval requests with filtering and pagination.

        Args:
            db: SQLAlchemy database session.
            user_id: Optional UUID to filter by creator or workload owner.
            status: Optional status string to filter.
            page: Page number for pagination (1-based).
            page_size: Number of items per page.

        Returns:
            Dictionary containing paginated approval requests and metadata.
        """
        self._logger.info("get_approval_requests called for user %s", user_id)

        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1:
            raise ValueError(f"page_size must be >= 1, got {page_size}")

        query = db.query(ApprovalRequest)

        if user_id:
            query = query.filter(
                (ApprovalRequest.current_user_id == user_id) |
                (ApprovalRequest.workload_id == user_id)
            )
        if status:
            query = query.filter(ApprovalRequest.status == status)

        total = query.count()
        self._logger.info("Found %d approval requests for user %s", total, user_id)

        query = query.order_by(desc(ApprovalRequest.created_at))

        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()

        self._logger.debug("Returning %d items for page %d", len(items), page)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }