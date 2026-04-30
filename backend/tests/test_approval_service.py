"""
Tests for the Approval Service and Notification Service.

Covers:
- Timeout handling and expiration
- Escalation logic
- Bulk approval/rejection
- Notification sending
- Approval workflow lifecycle
"""

import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, mock_open
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.models.approval import (
    ApprovalRequest, ApprovalStep, ApprovalStatus,
    ApprovalRole, ChangeType,
)
from app.services.approval_service import ApprovalService
from app.services.notification_service import (
    NotificationService,
    NotificationType,
    NotificationChannel,
    NotificationMessage,
)

# --- Test Database Setup ---

Base = declarative_base()

# Use SQLite in-memory for testing
engine = create_engine("sqlite:///:memory:")

# Create tables
Base.metadata.create_all(engine)


def get_test_db():
    """Yield a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_approval_request(db, change_type=ChangeType.Create, status=ApprovalStatus.Pending):
    """Helper to create a test approval request."""
    approval = ApprovalRequest(
        id=uuid4(),
        rule_ids=json.dumps([str(uuid4()), str(uuid4())]),
        change_type=change_type,
        description="Test approval request",
        current_user_id=uuid4(),
        required_approvals=2,
        status=status,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.add(approval)
    db.flush()
    return approval


def create_test_approval_step(db, approval_request_id, role=ApprovalRole.WorkloadStakeholder, status=ApprovalStatus.Pending):
    """Helper to create a test approval step."""
    step = ApprovalStep(
        id=uuid4(),
        approval_request_id=approval_request_id,
        approver_role=role,
        status=status,
    )
    db.add(step)
    db.flush()
    return step


class TestApprovalServiceNotificationIntegration(unittest.TestCase):
    """Tests for notification service integration with approval service."""

    def test_notification_service_send_approval_notification(self):
        """Test that notification service builds and sends approval notification."""
        with patch("smtplib.SMTP"), patch("app.services.notification_service.requests"):
            service = NotificationService(enable_email=True, enable_in_app=True)
            mock_db = MagicMock()
            mock_request = MagicMock()
            mock_request.id = uuid4()
            mock_request.change_type = ChangeType.Create
            mock_request.description = "Test"
            mock_request.required_approvals = 2
            mock_request.created_at = datetime.now(timezone.utc)
            mock_request.completed_at = None
            mock_request.status = ApprovalStatus.Pending

            result = service.send_approval_notification(
                db=mock_db,
                approval_request=mock_request,
                notification_type=NotificationType.APPROVAL_REQUEST_CREATED,
                recipient_email="test@example.com",
                recipient_name="Test User",
            )

            self.assertTrue(result)

    def test_notification_service_types(self):
        """Test all notification types are available."""
        expected_types = [
            NotificationType.APPROVAL_REQUEST_CREATED,
            NotificationType.APPROVAL_PENDING,
            NotificationType.APPROVAL_APPROVED,
            NotificationType.APPROVAL_REJECTED,
            NotificationType.APPROVAL_EXPIRED,
            NotificationType.APPROVAL_ESCALATED,
            NotificationType.APPROVAL_BULK_COMPLETED,
            NotificationType.ESCALATION_TRIGGERED,
        ]
        for ntype in expected_types:
            self.assertIsNotNone(ntype)


class TestApprovalServiceTimeoutHandling(unittest.TestCase):
    """Tests for timeout handling and expiration."""

    def test_check_and_expire_pending_approvals(self):
        """Test that pending approvals are expired after timeout."""
        for db in get_test_db():
            # Create an approval that was created more than 48 hours ago
            old_request = ApprovalRequest(
                id=uuid4(),
                rule_ids=json.dumps([str(uuid4())]),
                change_type=ChangeType.Create,
                description="Expired test",
                current_user_id=uuid4(),
                required_approvals=1,
                status=ApprovalStatus.Pending,
                created_at=datetime.now(timezone.utc) - timedelta(hours=50),
            )
            db.add(old_request)
            db.flush()

            service = ApprovalService(default_timeout_hours=48)
            count = service.check_and_expire_pending_approvals(db)

            # Refresh the request
            expired_request = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == old_request.id
            ).first()

            self.assertEqual(count, 1)
            self.assertEqual(expired_request.status, ApprovalStatus.Expired)
            self.assertIsNotNone(expired_request.completed_at)

    def test_check_and_expire_recent_approvals(self):
        """Test that recent approvals are NOT expired."""
        for db in get_test_db():
            recent_request = ApprovalRequest(
                id=uuid4(),
                rule_ids=json.dumps([str(uuid4())]),
                change_type=ChangeType.Update,
                description="Recent test",
                current_user_id=uuid4(),
                required_approvals=1,
                status=ApprovalStatus.Pending,
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            db.add(recent_request)
            db.flush()

            service = ApprovalService(default_timeout_hours=48)
            count = service.check_and_expire_pending_approvals(db)

            refreshed = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == recent_request.id
            ).first()

            self.assertEqual(count, 0)
            self.assertEqual(refreshed.status, ApprovalStatus.Pending)

    def test_handle_timeout_escalation_expires(self):
        """Test handle_timeout_escalation expires timed-out requests."""
        for db in get_test_db():
            timed_out = ApprovalRequest(
                id=uuid4(),
                rule_ids=json.dumps([str(uuid4())]),
                change_type=ChangeType.Create,
                description="Escalation test",
                current_user_id=uuid4(),
                required_approvals=1,
                status=ApprovalStatus.Pending,
                created_at=datetime.now(timezone.utc) - timedelta(hours=100),
            )
            db.add(timed_out)
            db.flush()

            service = ApprovalService(default_timeout_hours=48)
            result = service.handle_timeout_escalation(
                db=db,
                timeout_hours=24,
                escalate_to_role=None,
            )

            self.assertEqual(result["expired_count"], 1)
            self.assertEqual(result["escalated_count"], 0)

    def test_handle_timeout_escalation_with_escalation(self):
        """Test handle_timeout_escalation with role escalation."""
        for db in get_test_db():
            timed_out = ApprovalRequest(
                id=uuid4(),
                rule_ids=json.dumps([str(uuid4())]),
                change_type=ChangeType.Update,
                description="Escalation with role",
                current_user_id=uuid4(),
                required_approvals=1,
                status=ApprovalStatus.Pending,
                created_at=datetime.now(timezone.utc) - timedelta(hours=100),
            )
            db.add(timed_out)
            db.flush()

            service = ApprovalService(default_timeout_hours=48)
            result = service.handle_timeout_escalation(
                db=db,
                timeout_hours=24,
                escalate_to_role=ApprovalRole.SecurityStakeholder,
            )

            self.assertEqual(result["expired_count"], 1)
            self.assertEqual(result["escalated_count"], 1)
            self.assertTrue(len(result["details"]) > 0)
            self.assertTrue(result["details"][0].get("escalated", False))


class TestApprovalServiceBulkOperations(unittest.TestCase):
    """Tests for bulk approval and rejection operations."""

    def test_bulk_approve_single(self):
        """Test bulk approving a single approval request."""
        for db in get_test_db():
            approval = create_test_approval_request(db)
            step = create_test_approval_step(db, approval.id)

            service = ApprovalService()
            result = service.bulk_approve(
                db=db,
                approval_ids=[approval.id],
                approver_id=uuid4(),
                comment="Bulk approved",
            )

            self.assertIn(str(approval.id), result["approved_ids"])
            self.assertEqual(len(result["errors"]), 0)

            # Verify status changed
            refreshed = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval.id
            ).first()
            self.assertEqual(refreshed.status, ApprovalStatus.Approved)

    def test_bulk_approve_multiple(self):
        """Test bulk approving multiple approval requests."""
        for db in get_test_db():
            approvals = []
            for _ in range(3):
                a = create_test_approval_request(db)
                create_test_approval_step(db, a.id)
                approvals.append(a)

            service = ApprovalService()
            ids = [a.id for a in approvals]
            result = service.bulk_approve(
                db=db,
                approval_ids=ids,
                approver_id=uuid4(),
                comment="Bulk approved all",
            )

            self.assertEqual(len(result["approved_ids"]), 3)
            self.assertEqual(len(result["errors"]), 0)

    def test_bulk_approve_mixed_statuses(self):
        """Test bulk approve with already approved/rejected items."""
        for db in get_test_db():
            # Pending
            pending = create_test_approval_request(db, status=ApprovalStatus.Pending)
            create_test_approval_step(db, pending.id)

            # Already approved
            approved = create_test_approval_request(db, status=ApprovalStatus.Approved)
            create_test_approval_step(db, approved.id)

            # Already rejected
            rejected = create_test_approval_request(db, status=ApprovalStatus.Rejected)
            create_test_approval_step(db, rejected.id)

            service = ApprovalService()
            result = service.bulk_approve(
                db=db,
                approval_ids=[pending.id, approved.id, rejected.id],
                approver_id=uuid4(),
                comment="Mixed bulk",
            )

            # Only pending should be approved
            self.assertIn(str(pending.id), result["approved_ids"])
            self.assertEqual(result["total_approved"], 1)

    def test_bulk_reject(self):
        """Test bulk rejection of approval requests."""
        for db in get_test_db():
            approval = create_test_approval_request(db)
            create_test_approval_step(db, approval.id)

            service = ApprovalService()
            result = service.bulk_reject(
                db=db,
                approval_ids=[approval.id],
                approver_id=uuid4(),
                comment="Bulk rejected",
            )

            self.assertIn(str(approval.id), result["rejected_ids"])

            refreshed = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval.id
            ).first()
            self.assertEqual(refreshed.status, ApprovalStatus.Rejected)

    def test_bulk_approve_empty_ids_raises(self):
        """Test that bulk approve with empty list raises ValueError."""
        for db in get_test_db():
            service = ApprovalService()
            with self.assertRaises(ValueError):
                service.bulk_approve(
                    db=db,
                    approval_ids=[],
                    approver_id=uuid4(),
                )

    def test_bulk_reject_empty_comment_raises(self):
        """Test that bulk reject with empty comment raises ValueError."""
        for db in get_test_db():
            service = ApprovalService()
            with self.assertRaises(ValueError):
                service.bulk_reject(
                    db=db,
                    approval_ids=[uuid4()],
                    approver_id=uuid4(),
                    comment="",
                )

    def test_bulk_approve_nonexistent_ids(self):
        """Test bulk approve with non-existent IDs."""
        for db in get_test_db():
            fake_id = uuid4()
            service = ApprovalService()
            result = service.bulk_approve(
                db=db,
                approval_ids=[fake_id],
                approver_id=uuid4(),
                comment="Test",
            )

            self.assertIn(str(fake_id), result["errors"][0]["id"] if result["errors"] else [])
            self.assertEqual(result["total_approved"], 0)


class TestApprovalServiceEscalation(unittest.TestCase):
    """Tests for approval escalation."""

    def test_escalate_approval(self):
        """Test escalating an approval request."""
        for db in get_test_db():
            approval = create_test_approval_request(db)
            create_test_approval_step(db, approval.id)

            service = ApprovalService()
            new_role = ApprovalRole.SecurityStakeholder
            result = service.escalate_approval(
                db=db,
                approval_id=approval.id,
                approver_id=uuid4(),
                new_approver_role=new_role,
                reason="Urgent change needed",
            )

            self.assertIsNotNone(result)

            # Check that a new escalated step was created
            new_steps = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id
            ).all()

            # Should have at least one escalated step
            escalated = [s for s in new_steps if "Escalated" in (s.comments or "")]
            self.assertTrue(len(escalated) > 0)

    def test_escalate_nonexistent_approval(self):
        """Test escalating a non-existent approval raises ValueError."""
        for db in get_test_db():
            service = ApprovalService()
            with self.assertRaises(ValueError):
                service.escalate_approval(
                    db=db,
                    approval_id=uuid4(),
                    approver_id=uuid4(),
                    new_approver_role=ApprovalRole.SecurityStakeholder,
                )

    def test_escalate_terminal_approval(self):
        """Test escalating an already-completed approval raises ValueError."""
        for db in get_test_db():
            approval = create_test_approval_request(
                db, status=ApprovalStatus.Approved
            )
            create_test_approval_step(db, approval.id)

            service = ApprovalService()
            with self.assertRaises(ValueError):
                service.escalate_approval(
                    db=db,
                    approval_id=approval.id,
                    approver_id=uuid4(),
                    new_approver_role=ApprovalRole.SecurityStakeholder,
                )

    def test_escalate_approval_no_escalated(self):
        """Test that escalated step has correct role."""
        for db in get_test_db():
            approval = create_test_approval_request(db)
            create_test_approval_step(db, approval.id)

            new_role = ApprovalRole.SecurityStakeholder
            service = ApprovalService()
            service.escalate_approval(
                db=db,
                approval_id=approval.id,
                approver_id=uuid4(),
                new_approver_role=new_role,
            )

            # Check the new step has the correct role
            new_step = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id,
                ApprovalStep.approver_role == new_role,
            ).first()

            self.assertIsNotNone(new_step)
            self.assertEqual(new_step.status, ApprovalStatus.Pending)


class TestApprovalServiceTimeoutWithNotifications(unittest.TestCase):
    """Tests for timeout handling with notification integration."""

    def test_timeout_triggers_notification(self):
        """Test that timeout handling triggers notifications."""
        with patch("smtplib.SMTP"), patch("app.services.notification_service.requests"):
            for db in get_test_db():
                approval = create_test_approval_request(db)
                create_test_approval_step(db, approval.id)

                service = ApprovalService(default_timeout_hours=48)
                with patch.object(
                    NotificationService, "send_bulk_approval_notification",
                    return_value=True,
                ) as mock_notify:
                    service.handle_timeout_escalation(
                        db=db,
                        timeout_hours=1,
                    )
                    mock_notify.assert_called()


class TestNotificationServiceDelivery(unittest.TestCase):
    """Tests for notification delivery channels."""

    def test_notification_message_creation(self):
        """Test that notification messages are created properly."""
        msg = NotificationMessage(
            notification_type=NotificationType.APPROVAL_REQUEST_CREATED,
            recipient_email="test@example.com",
            recipient_name="Test User",
            title="Test Title",
            body="Test Body",
        )

        self.assertEqual(msg.recipient_email, "test@example.com")
        self.assertIsNotNone(msg.timestamp)
        self.assertEqual(msg.channel, NotificationChannel.ALL)

    def test_notification_templates(self):
        """Test that notification templates are defined."""
        service = NotificationService()

        mock_request = MagicMock()
        mock_request.id = uuid4()
        mock_request.change_type = ChangeType.Create
        mock_request.description = "Test description"
        mock_request.required_approvals = 2
        mock_request.created_at = datetime.now(timezone.utc)
        mock_request.completed_at = None

        msg = service._build_notification_message(
            approval_request=mock_request,
            notification_type=NotificationType.APPROVAL_REQUEST_CREATED,
            recipient_email="test@example.com",
            recipient_name="Test User",
            additional_data={"extra": "data"},
        )

        self.assertEqual(msg.notification_type, NotificationType.APPROVAL_REQUEST_CREATED)
        self.assertIn("Test description", msg.body)
        self.assertIn("extra", msg.data)

    def test_notification_get_history(self):
        """Test that notification history returns correct pagination."""
        service = NotificationService()
        mock_db = MagicMock()

        result = service.get_notification_history(
            db=mock_db,
            approval_id=uuid4(),
            page=1,
            page_size=50,
        )

        self.assertEqual(result["page"], 1)
        self.assertEqual(result["page_size"], 50)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])

    def test_send_escalation_notification(self):
        """Test sending escalation notification."""
        with patch("smtplib.SMTP"), patch("app.services.notification_service.requests"):
            service = NotificationService(enable_email=True, enable_in_app=True)
            mock_db = MagicMock()
            mock_request = MagicMock()
            mock_request.id = uuid4()
            mock_request.change_type = ChangeType.Create
            mock_request.description = "Test"
            mock_request.required_approvals = 2
            mock_request.created_at = datetime.now(timezone.utc)

            result = service.send_escalation_notification(
                db=mock_db,
                approval_request=mock_request,
                original_approver_id=uuid4(),
                escalated_to_role=ApprovalRole.SecurityStakeholder,
                reason="Timeout exceeded",
            )

            self.assertTrue(result)


class TestApprovalServiceGetPendingCount(unittest.TestCase):
    """Tests for getting pending approval count."""

    def test_get_pending_approval_count(self):
        """Test getting count of pending approvals."""
        for db in get_test_db():
            # Create pending requests
            for _ in range(3):
                approval = create_test_approval_request(db, status=ApprovalStatus.Pending)
                create_test_approval_step(db, approval.id)

            # Create approved request
            approved = create_test_approval_request(db, status=ApprovalStatus.Approved)
            create_test_approval_step(db, approved.id)

            service = ApprovalService()
            count = service.get_pending_approval_count(db=db)

            self.assertEqual(count, 3)


class TestApprovalServiceLifecycle(unittest.TestCase):
    """Integration tests for the full approval lifecycle."""

    def test_full_approval_lifecycle(self):
        """Test creating, approving, rejecting, and expiring approvals."""
        for db in get_test_db():
            # Create
            service = ApprovalService()
            approval = service.create_approval_request(
                db=db,
                rule_ids=[uuid4(), uuid4()],
                change_type=ChangeType.Create,
                description="Full lifecycle test",
                user_id=uuid4(),
                required_approvals=2,
            )

            self.assertIsNotNone(approval)
            self.assertEqual(approval.status, ApprovalStatus.Pending)

            # Get steps
            steps = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id
            ).all()
            self.assertEqual(len(steps), 2)

            # Approve first step
            first_step = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id,
                ApprovalStep.status == ApprovalStatus.Pending,
            ).first()
            self.assertIsNotNone(first_step)

            service.approve_step(
                db=db,
                step_id=first_step.id,
                approver_id=uuid4(),
                comment="First step approved",
            )

            # Refresh and check
            refreshed = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval.id
            ).first()
            # Still pending because not all steps are approved yet
            self.assertEqual(refreshed.status, ApprovalStatus.Pending)

            # Approve second step
            second_step = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id,
                ApprovalStep.status == ApprovalStatus.Pending,
            ).first()
            self.assertIsNotNone(second_step)

            service.approve_step(
                db=db,
                step_id=second_step.id,
                approver_id=uuid4(),
                comment="Second step approved",
            )

            # Now fully approved
            final = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval.id
            ).first()
            self.assertEqual(final.status, ApprovalStatus.Approved)

    def test_full_reject_lifecycle(self):
        """Test creating and rejecting an approval."""
        for db in get_test_db():
            service = ApprovalService()
            approval = service.create_approval_request(
                db=db,
                rule_ids=[uuid4()],
                change_type=ChangeType.Update,
                description="Reject test",
                user_id=uuid4(),
                required_approvals=1,
            )

            step = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id
            ).first()

            service.reject_step(
                db=db,
                step_id=step.id,
                approver_id=uuid4(),
                comment="Rejected because reasons",
            )

            final = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval.id
            ).first()
            self.assertEqual(final.status, ApprovalStatus.Rejected)


if __name__ == "__main__":
    unittest.main()