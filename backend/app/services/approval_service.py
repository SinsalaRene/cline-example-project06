"""
Approval workflow service for managing multi-level approvals.

Refactored to use class-based dependency injection pattern for proper
FastAPI integration with dependency injection support.

Includes timeout handling, escalation logic, bulk approval operations,
and notification integration.
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
from app.services.notification_service import NotificationService, NotificationType
from app.workflows.approval_workflow import ApprovalWorkflow
from app.workflows.audit_workflow import AuditWorkflow
from app.workflows.notification_workflow import NotificationWorkflow, NotificationChannel

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

    def __init__(
        self,
        logger_name: str = __name__,
        default_timeout_hours: int = 48,
        approval_workflow: Optional[ApprovalWorkflow] = None,
        audit_workflow: Optional[AuditWorkflow] = None,
        notification_workflow: Optional[NotificationWorkflow] = None,
    ):
        """Initialize the ApprovalService.

        Args:
            logger_name: Name for the logger instance.
            default_timeout_hours: Default timeout for approval requests in hours.
            approval_workflow: Optional ApprovalWorkflow instance.
            audit_workflow: Optional AuditWorkflow instance.
            notification_workflow: Optional NotificationWorkflow instance.
        """
        self._logger = logging.getLogger(logger_name)
        self._default_timeout_hours = default_timeout_hours
        self._logger.debug("ApprovalService initialized with timeout=%dh", default_timeout_hours)
        
        # Wire up workflows for cross-module integration
        self._approval_workflow = approval_workflow
        self._audit_workflow = audit_workflow
        self._notification_workflow = notification_workflow

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

        Uses the ApprovalWorkflow to apply rule changes and the AuditWorkflow
        to log the approval. Sends notifications via NotificationWorkflow.

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
            # All stages complete - trigger rule changes
            approval_request.status = ApprovalStatus.Approved
            approval_request.completed_at = datetime.now(timezone.utc)
            db.flush()

            self._logger.info("Approval request %s fully approved - applying rule changes", approval_request.id)
            
            # Use ApprovalWorkflow to apply rule changes
            if self._approval_workflow:
                try:
                    rule_ids = approval_request.rule_uuids
                    self._approval_workflow.apply_approval_to_rules(
                        db=db,
                        approval_request=approval_request,
                        rule_ids=rule_ids,
                        user_id=approver_id,
                    )
                except Exception:
                    self._logger.exception("Failed to apply approval to rules via workflow")

            # Use AuditWorkflow to log the approval
            if self._audit_workflow:
                try:
                    self._audit_workflow.log_approval_approved(
                        db=db,
                        user_id=approver_id,
                        approval_id=approval_request.id,
                        comment=comment,
                    )
                except Exception:
                    self._logger.exception("Failed to log approval in audit workflow")

            # Use NotificationWorkflow to send notifications
            if self._notification_workflow:
                try:
                    rule_ids = approval_request.rule_uuids
                    recipients = self._approval_workflow._get_approval_recipients(
                        db, approval_request
                    )
                    for recipient in recipients:
                        self._notification_workflow.send_approval_notification(
                            db=db,
                            approval_request=approval_request,
                            notification_type=NotificationType.APPROVAL_APPROVED,
                            channel=NotificationChannel.EMAIL,
                            recipient_email=recipient.get("email", ""),
                            recipient_name=recipient.get("name", "User"),
                        )
                except Exception:
                    self._logger.exception("Failed to send notification via workflow")

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

    def bulk_approve(
        self,
        db: Session,
        approval_ids: list[UUID],
        approver_id: UUID,
        comment: Optional[str] = None,
        required_approvals: int = 2,
    ) -> dict:
        """Bulk approve multiple approval requests.
        
        Approves all pending approval steps for the given approval request IDs
        in a single transaction. Sends notifications for each approved request
        and logs the operation.
        
        Args:
            db: SQLAlchemy database session.
            approval_ids: List of approval request IDs to approve.
            approver_id: UUID of the user performing the bulk approval.
            comment: Optional approval comment.
            required_approvals: Number of approvals required per request.
        
        Returns:
            Dictionary with results containing approved_ids, rejected_ids, and counts.
        
        Raises:
            ValueError: If approval_ids is empty.
        """
        self._logger.info("bulk_approve called for %d requests by user %s",
                          len(approval_ids), approver_id)
        
        if not approval_ids:
            raise ValueError("At least one approval ID is required for bulk approval")
        
        results = {"approved_ids": [], "rejected_ids": [], "errors": []}
        
        for approval_id in approval_ids:
            try:
                approval_request = db.query(ApprovalRequest).filter(
                    ApprovalRequest.id == approval_id
                ).first()
                
                if not approval_request:
                    self._logger.warning("Approval request %s not found during bulk approve", approval_id)
                    results["errors"].append({
                        "id": str(approval_id),
                        "error": "Not found",
                    })
                    continue
                
                if approval_request.status in [
                    ApprovalStatus.Approved,
                    ApprovalStatus.Rejected,
                    ApprovalStatus.Expired,
                ]:
                    self._logger.info("Approval request %s already in terminal state: %s",
                                      approval_id, approval_request.status)
                    continue
                
                # Get all pending steps for this request
                pending_steps = db.query(ApprovalStep).filter(
                    ApprovalStep.approval_request_id == approval_id,
                    ApprovalStep.status == ApprovalStatus.Pending,
                ).all()
                
                if not pending_steps:
                    self._logger.info("No pending steps for approval %s", approval_id)
                    continue
                
                # Approve all pending steps
                for step in pending_steps:
                    step.status = ApprovalStatus.Approved
                    step.approver_id = approver_id
                    step.comments = comment
                    step.approved_at = datetime.now(timezone.utc)
                
                # Update the approval request status
                approval_request.status = ApprovalStatus.Approved
                approval_request.completed_at = datetime.now(timezone.utc)
                
                results["approved_ids"].append(str(approval_id))
                self._logger.info("Bulk approved approval %s", approval_id)
                
            except Exception:
                self._logger.exception("Error bulk approving approval %s", approval_id)
                results["errors"].append({
                    "id": str(approval_id),
                    "error": "Internal error during approval",
                })
        
        # Commit all changes
        try:
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Error committing bulk approval changes")
            raise
        
        # Send notifications for successful bulk approval
        if results["approved_ids"]:
            notification_service = NotificationService()
            notification_service.send_bulk_approval_notification(
                db=db,
                approval_ids=[uuid for uuid in approval_ids if str(uuid) in results["approved_ids"]],
                notification_type=NotificationType.APPROVAL_BULK_COMPLETED,
                initiator_name="Bulk operator",
            )
        
        results["total_processed"] = len(approval_ids)
        results["total_approved"] = len(results["approved_ids"])
        results["total_rejected"] = len(results["rejected_ids"])
        
        self._logger.info(
            "Bulk approve complete: %d approved, %d rejected, %d errors",
            len(results["approved_ids"]),
            len(results["rejected_ids"]),
            len(results["errors"]),
        )
        
        return results

    def bulk_reject(
        self,
        db: Session,
        approval_ids: list[UUID],
        approver_id: UUID,
        comment: str,
    ) -> dict:
        """Bulk reject multiple approval requests.
        
        Args:
            db: SQLAlchemy database session.
            approval_ids: List of approval request IDs to reject.
            approver_id: UUID of the user performing the bulk rejection.
            comment: Required rejection comment.
        
        Returns:
            Dictionary with results containing rejected_ids and counts.
        
        Raises:
            ValueError: If approval_ids is empty or comment is empty.
        """
        self._logger.info("bulk_reject called for %d requests by user %s",
                          len(approval_ids), approver_id)
        
        if not approval_ids:
            raise ValueError("At least one approval ID is required for bulk rejection")
        
        if not comment or not comment.strip():
            raise ValueError("Rejection comment is required")
        
        results = {"rejected_ids": [], "errors": []}
        
        for approval_id in approval_ids:
            try:
                approval_request = db.query(ApprovalRequest).filter(
                    ApprovalRequest.id == approval_id
                ).first()
                
                if not approval_request:
                    self._logger.warning("Approval request %s not found during bulk reject", approval_id)
                    results["errors"].append({
                        "id": str(approval_id),
                        "error": "Not found",
                    })
                    continue
                
                if approval_request.status in [
                    ApprovalStatus.Approved,
                    ApprovalStatus.Rejected,
                    ApprovalStatus.Expired,
                ]:
                    continue
                
                # Reject all pending steps
                pending_steps = db.query(ApprovalStep).filter(
                    ApprovalStep.approval_request_id == approval_id,
                    ApprovalStep.status == ApprovalStatus.Pending,
                ).all()
                
                for step in pending_steps:
                    step.status = ApprovalStatus.Rejected
                    step.approver_id = approver_id
                    step.comments = comment
                    step.approved_at = datetime.now(timezone.utc)
                
                approval_request.status = ApprovalStatus.Rejected
                approval_request.completed_at = datetime.now(timezone.utc)
                
                results["rejected_ids"].append(str(approval_id))
                self._logger.info("Bulk rejected approval %s", approval_id)
                
            except Exception:
                self._logger.exception("Error bulk rejecting approval %s", approval_id)
                results["errors"].append({
                    "id": str(approval_id),
                    "error": "Internal error during rejection",
                })
        
        try:
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Error committing bulk rejection changes")
            raise
        
        self._logger.info("Bulk reject complete: %d rejected, %d errors",
                         len(results["rejected_ids"]), len(results["errors"]))
        
        return results

    def escalate_approval(
        self,
        db: Session,
        approval_id: UUID,
        approver_id: UUID,
        new_approver_role: ApprovalRole,
        reason: str = "",
    ) -> ApprovalRequest:
        """Escalate an approval request to a higher role/priority.
        
        Creates a new approval step with the escalated role and marks the
        previous step as skipped if still pending.
        
        Args:
            db: SQLAlchemy database session.
            approval_id: UUID of the approval request to escalate.
            approver_id: UUID of the user performing the escalation.
            new_approver_role: The role to escalate to.
            reason: Reason for escalation.
        
        Returns:
            The updated ApprovalRequest object.
        
        Raises:
            ValueError: If approval not found or already in terminal state.
        """
        self._logger.info("escalate_approval called for approval %s to role %s",
                          approval_id, new_approver_role)
        
        approval_request = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id
        ).first()
        
        if not approval_request:
            msg = f"Approval request {approval_id} not found"
            self._logger.warning(msg)
            raise ValueError(msg)
        
        if approval_request.status in [
            ApprovalStatus.Approved,
            ApprovalStatus.Rejected,
            ApprovalStatus.Expired,
        ]:
            msg = f"Approval request {approval_id} is in terminal state: {approval_request.status}"
            raise ValueError(msg)
        
        # Create new escalated step
        escalated_step = ApprovalStep(
            approval_request_id=approval_id,
            approver_role=new_approver_role,
            status=ApprovalStatus.Pending,
            comments=f"Escalated (reason: {reason})" if reason else "Escalated",
        )
        db.add(escalated_step)
        
        self._logger.info("Created escalated step %s for approval %s",
                          escalated_step.id, approval_id)
        
        # Send escalation notification
        notification_service = NotificationService()
        notification_service.send_escalation_notification(
            db=db,
            approval_request=approval_request,
            original_approver_id=approver_id,
            escalated_to_role=new_approver_role,
            reason=reason,
        )
        
        try:
            db.commit()
            db.refresh(approval_request)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to commit escalation for approval %s", approval_id)
            raise
        
        return approval_request

    def handle_timeout_escalation(
        self,
        db: Session,
        timeout_hours: Optional[int] = None,
        escalate_to_role: Optional[ApprovalRole] = None,
    ) -> dict:
        """Handle timeouts for all pending approval requests.
        
        Expires all approval requests that have exceeded their timeout,
        optionally escalating them to a higher role.
        
        Args:
            db: SQLAlchemy database session.
            timeout_hours: Override timeout in hours. Uses default if None.
            escalate_to_role: Role to escalate to if timeouts are handled.
        
        Returns:
            Dictionary with expired_count, escalated_count, and details.
        """
        timeout = timeout_hours if timeout_hours is not None else self._default_timeout_hours
        self._logger.info("handle_timeout_escalation called with timeout=%dh", timeout)
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=timeout)
        
        # Find all pending requests that have timed out
        timed_out_requests = db.query(ApprovalRequest).filter(
            ApprovalRequest.status == ApprovalStatus.Pending,
            ApprovalRequest.created_at < cutoff_time,
        ).all()
        
        expired_count = 0
        escalated_count = 0
        details = []
        
        for request in timed_out_requests:
            try:
                request.status = ApprovalStatus.Expired
                request.completed_at = datetime.now(timezone.utc)
                expired_count += 1
                
                detail = {
                    "id": str(request.id),
                    "change_type": request.change_type,
                    "created_at": request.created_at.isoformat() if request.created_at else None,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
                
                # Escalate if role specified
                if escalate_to_role:
                    escalated_step = ApprovalStep(
                        approval_request_id=request.id,
                        approver_role=escalate_to_role,
                        status=ApprovalStatus.Pending,
                        comments=f"Auto-escalated after {timeout}h timeout",
                    )
                    db.add(escalated_step)
                    escalated_count += 1
                    detail["escalated_to"] = escalate_to_role.value
                    detail["escalated"] = True
                
                details.append(detail)
                self._logger.info("Timed out approval %s", request.id)
                
            except Exception:
                self._logger.exception("Error handling timeout for approval %s", request.id)
        
        try:
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Error committing timeout escalations")
            raise
        
        # Send notifications for expired requests
        if expired_count > 0:
            notification_service = NotificationService()
            expired_ids = [d["id"] for d in details]
            notification_service.send_bulk_approval_notification(
                db=db,
                approval_ids=[UUID(id_str) for id_str in expired_ids if all(c in "0123456789abcdef-" for c in id_str.replace("-", ""))],
                notification_type=NotificationType.APPROVAL_EXPIRED,
            )
        
        self._logger.info(
            "Timeout handling complete: %d expired, %d escalated",
            expired_count, escalated_count,
        )
        
        return {
            "expired_count": expired_count,
            "escalated_count": escalated_count,
            "details": details,
        }

    def get_pending_approval_count(
        self,
        db: Session,
        user_id: Optional[UUID] = None,
    ) -> int:
        """Get count of pending approval requests for a user.
        
        Args:
            db: SQLAlchemy database session.
            user_id: UUID of the user to check.
        
        Returns:
            Count of pending approval requests.
        """
        query = db.query(ApprovalRequest).filter(
            ApprovalRequest.status == ApprovalStatus.Pending
        )
        
        if user_id:
            query = query.filter(
                (ApprovalRequest.current_user_id == user_id) |
                (ApprovalRequest.workload_id == user_id)
            )
        
        return query.count()

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
