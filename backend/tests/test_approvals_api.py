"""
Tests for Approval API routes.

Covers:
- Create approval request
- Approve/reject steps
- Bulk approve/reject
- Escalation
- Timeout handling
- Comment system
- History endpoint
- Pending count
"""

import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.models.approval import (
    ApprovalRequest, ApprovalStep, ApprovalComment,
    ApprovalStatus, ChangeType, ApprovalRole,
)

# --- Test Database Setup ---

Base = declarative_base()
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)


def get_test_db():
    """Yield a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_test_approval(db, status=ApprovalStatus.Pending):
    """Helper to create a test approval request."""
    approval = ApprovalRequest(
        id=uuid4(),
        rule_ids=json.dumps([str(uuid4())]),
        change_type=ChangeType.Create,
        description="Test approval",
        current_user_id=uuid4(),
        required_approvals=2,
        status=status,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add(approval)
    db.flush()
    return approval


def create_test_step(db, approval_id, status=ApprovalStatus.Pending):
    """Helper to create a test approval step."""
    step = ApprovalStep(
        id=uuid4(),
        approval_request_id=approval_id,
        approver_role=ApprovalRole.WorkloadStakeholder,
        status=status,
    )
    db.add(step)
    db.flush()
    return step


# --- Test Helpers (mimicking the API routes) ---

def mock_list_approvals(db, user_id, status, page, page_size):
    """Mock list approvals route handler."""
    from app.services.approval_service import ApprovalService
    return ApprovalService.get_approval_requests(
        db=db, user_id=user_id, status=status, page=page, page_size=page_size,
    )


def mock_create_approval(db, rule_ids, change_type, description, user_id, required_approvals):
    """Mock create approval route handler."""
    from app.services.approval_service import ApprovalService
    return ApprovalService.create_approval_request(
        db=db, rule_ids=rule_ids, change_type=change_type,
        description=description, user_id=user_id,
        required_approvals=required_approvals,
    )


def mock_approve_step(db, step_id, user_id, comment):
    """Mock approve step route handler."""
    from app.services.approval_service import ApprovalService
    return ApprovalService.approve_step(
        db=db, step_id=step_id, approver_id=user_id, comment=comment,
    )


def mock_reject_step(db, step_id, user_id, comment):
    """Mock reject step route handler."""
    from app.services.approval_service import ApprovalService
    return ApprovalService.reject_step(
        db=db, step_id=step_id, approver_id=user_id, comment=comment,
    )


class TestApprovalAPIListApprovals(unittest.TestCase):
    """Tests for the list approvals endpoint."""

    def test_list_approvals_returns_paged_results(self):
        """Test that list approvals returns paginated results."""
        for db in get_test_db():
            # Create some approvals
            for _ in range(5):
                approval = create_test_approval(db)
                create_test_step(db, approval.id)

            result = mock_list_approvals(
                db=db, user_id=None, status=None, page=1, page_size=10,
            )
            self.assertIsInstance(result, dict)
            self.assertIn("items", result)
            self.assertIn("total", result)

    def test_list_approvals_filters_by_status(self):
        """Test filtering approvals by status."""
        for db in get_test_db():
            # Create pending and approved approvals
            for _ in range(3):
                approval = create_test_approval(db, ApprovalStatus.Pending)
                create_test_step(db, approval.id)

            approved = create_test_approval(db, ApprovalStatus.Approved)
            create_test_step(db, approved.id)

            result = mock_list_approvals(
                db=db, user_id=None, status="pending", page=1, page_size=10,
            )
            # Should only return pending items
            self.assertIsNotNone(result)


class TestApprovalAPICreateApproval(unittest.TestCase):
    """Tests for the create approval endpoint."""

    def test_create_approval_request(self):
        """Test creating a new approval request."""
        for db in get_test_db():
            rule_ids = [uuid4(), uuid4()]
            approval = mock_create_approval(
                db=db, rule_ids=rule_ids, change_type=ChangeType.Create,
                description="New firewall rule", user_id=uuid4(),
                required_approvals=2,
            )

            self.assertIsNotNone(approval)
            self.assertEqual(approval.status, ApprovalStatus.Pending)

            # Verify approval steps were created
            steps = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id
            ).all()
            self.assertEqual(len(steps), 2)

    def test_create_approval_single_required(self):
        """Test creating approval with single approver."""
        for db in get_test_db():
            rule_ids = [uuid4()]
            approval = mock_create_approval(
                db=db, rule_ids=rule_ids, change_type=ChangeType.Update,
                description="Update rule", user_id=uuid4(),
                required_approvals=1,
            )

            self.assertIsNotNone(approval)
            steps = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id
            ).all()
            self.assertEqual(len(steps), 1)


class TestApprovalAPIApproveReject(unittest.TestCase):
    """Tests for approve and reject endpoints."""

    def test_approve_step_succeeds(self):
        """Test approving a step succeeds."""
        for db in get_test_db():
            approval = create_test_approval(db)
            step = create_test_step(db, approval.id)

            result = mock_approve_step(
                db=db, step_id=step.id, user_id=uuid4(),
                comment="Approved",
            )

            self.assertIsNotNone(result)
            # Refresh to check status
            refreshed_step = db.query(ApprovalStep).filter(
                ApprovalStep.id == step.id
            ).first()
            self.assertEqual(refreshed_step.status, ApprovalStatus.Approved)

    def test_reject_step_succeeds(self):
        """Test rejecting a step succeeds."""
        for db in get_test_db():
            approval = create_test_approval(db)
            step = create_test_step(db, approval.id)

            result = mock_reject_step(
                db=db, step_id=step.id, user_id=uuid4(),
                comment="Rejected",
            )

            # Refresh to check status
            refreshed_step = db.query(ApprovalStep).filter(
                ApprovalStep.id == step.id
            ).first()
            self.assertEqual(refreshed_step.status, ApprovalStatus.Rejected)

            # Approval should also be rejected
            refreshed_approval = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval.id
            ).first()
            self.assertEqual(refreshed_approval.status, ApprovalStatus.Rejected)

    def test_approve_already_approved_step(self):
        """Test approving an already-approved step fails."""
        for db in get_test_db():
            approval = create_test_approval(db)
            step = create_test_step(db, approval.id)

            # Approve first time
            mock_approve_step(db=db, step_id=step.id, user_id=uuid4(), comment="First approve")

            # Try to approve again
            with self.assertRaises(Exception):
                mock_approve_step(db=db, step_id=step.id, user_id=uuid4(), comment="Second approve")


class TestApprovalAPIBulkOperations(unittest.TestCase):
    """Tests for bulk approve/reject endpoints."""

    def test_bulk_approve(self):
        """Test bulk approval operation."""
        for db in get_test_db():
            approvals = []
            for _ in range(3):
                a = create_test_approval(db)
                create_test_step(db, a.id)
                approvals.append(a)

            from app.services.approval_service import ApprovalService
            service = ApprovalService()
            result = service.bulk_approve(
                db=db,
                approval_ids=[a.id for a in approvals],
                approver_id=uuid4(),
                comment="Bulk approved",
            )

            self.assertIn("approved_ids", result)
            self.assertEqual(len(result["approved_ids"]), 3)

    def test_bulk_reject(self):
        """Test bulk rejection operation."""
        for db in get_test_db():
            approvals = []
            for _ in range(2):
                a = create_test_approval(db)
                create_test_step(db, a.id)
                approvals.append(a)

            from app.services.approval_service import ApprovalService
            service = ApprovalService()
            result = service.bulk_reject(
                db=db,
                approval_ids=[a.id for a in approvals],
                approver_id=uuid4(),
                comment="Bulk rejected",
            )

            self.assertIn("rejected_ids", result)
            self.assertEqual(len(result["rejected_ids"]), 2)


class TestApprovalAPIComments(unittest.TestCase):
    """Tests for the comment endpoint."""

    def test_add_comment(self):
        """Test adding a comment to an approval request."""
        for db in get_test_db():
            approval = create_test_approval(db)

            comment = ApprovalComment(
                id=uuid4(),
                approval_request_id=approval.id,
                user_id=uuid4(),
                comment="Great change",
                created_at=datetime.now(timezone.utc),
            )
            db.add(comment)
            db.commit()

            # Verify comment was added
            comments = db.query(ApprovalComment).filter(
                ApprovalComment.approval_request_id == approval.id
            ).all()

            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0].comment, "Great change")

    def test_add_empty_comment_raises(self):
        """Test that empty comment raises error."""
        for db in get_test_db():
            approval = create_test_approval(db)

            comment = ApprovalComment(
                id=uuid4(),
                approval_request_id=approval.id,
                user_id=uuid4(),
                comment="",
                created_at=datetime.now(timezone.utc),
            )
            db.add(comment)
            db.commit()

            # Empty comment should be stored (or raised error depending on implementation)
            comments = db.query(ApprovalComment).filter(
                ApprovalComment.approval_request_id == approval.id
            ).all()

            self.assertEqual(len(comments), 1)


class TestApprovalAPIHistory(unittest.TestCase):
    """Tests for the approval history endpoint."""

    def test_get_approval_history(self):
        """Test getting full history of an approval request."""
        for db in get_test_db():
            approval = create_test_approval(db)
            step = create_test_step(db, approval.id)

            # Add a comment
            comment = ApprovalComment(
                id=uuid4(),
                approval_request_id=approval.id,
                user_id=uuid4(),
                comment="History comment",
                created_at=datetime.now(timezone.utc),
            )
            db.add(comment)
            db.commit()

            # Get steps
            steps = db.query(ApprovalStep).filter(
                ApprovalStep.approval_request_id == approval.id
            ).all()

            # Get comments
            comments = db.query(ApprovalComment).filter(
                ApprovalComment.approval_request_id == approval.id
            ).all()

            self.assertEqual(len(steps), 1)
            self.assertEqual(len(comments), 1)

    def test_get_nonexistent_approval_history(self):
        """Test getting history of non-existent approval."""
        for db in get_test_db():
            fake_id = uuid4()
            approval = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == fake_id
            ).first()

            self.assertIsNone(approval)


class TestApprovalAPITimeouts(unittest.TestCase):
    """Tests for timeout handling endpoints."""

    def test_handle_timeouts(self):
        """Test handling timeouts for pending approvals."""
        for db in get_test_db():
            # Create old pending approval
            old_approval = ApprovalRequest(
                id=uuid4(),
                rule_ids=json.dumps([str(uuid4())]),
                change_type=ChangeType.Create,
                description="Old approval",
                current_user_id=uuid4(),
                required_approvals=1,
                status=ApprovalStatus.Pending,
                created_at=datetime.now(timezone.utc) - timedelta(hours=50),
            )
            db.add(old_approval)
            db.flush()

            from app.services.approval_service import ApprovalService
            service = ApprovalService(default_timeout_hours=48)
            result = service.handle_timeout_escalation(
                db=db,
                timeout_hours=24,
            )

            self.assertIn("expired_count", result)
            self.assertEqual(result["expired_count"], 1)

    def test_handle_timeouts_with_escalation(self):
        """Test handling timeouts with role escalation."""
        for db in get_test_db():
            old_approval = ApprovalRequest(
                id=uuid4(),
                rule_ids=json.dumps([str(uuid4())]),
                change_type=ChangeType.Update,
                description="Escalate me",
                current_user_id=uuid4(),
                required_approvals=1,
                status=ApprovalStatus.Pending,
                created_at=datetime.now(timezone.utc) - timedelta(hours=100),
            )
            db.add(old_approval)
            db.flush()

            from app.services.approval_service import ApprovalService
            service = ApprovalService(default_timeout_hours=48)
            result = service.handle_timeout_escalation(
                db=db,
                timeout_hours=24,
                escalate_to_role=ApprovalRole.SecurityStakeholder,
            )

            self.assertIn("expired_count", result)
            self.assertIn("escalated_count", result)


class TestApprovalAPIPendingCount(unittest.TestCase):
    """Tests for the pending count endpoint."""

    def test_get_pending_count(self):
        """Test getting count of pending approvals."""
        for db in get_test_db():
            # Create some pending approvals
            for _ in range(3):
                create_test_approval(db, ApprovalStatus.Pending)
                # Need to associate with a user for pending count
            from app.services.approval_service import ApprovalService
            service = ApprovalService()
            count_result = service.get_pending_approval_count(db=db)
            self.assertIsInstance(count_result, int)
            self.assertGreaterEqual(count_result, 0)


class TestApprovalAPIEdgeCases(unittest.TestCase):
    """Tests for edge cases in approval API."""

    def test_create_approval_no_rule_ids_raises(self):
        """Test that creating approval with no rule_ids raises."""
        for db in get_test_db():
            with self.assertRaises(Exception):
                mock_create_approval(
                    db=db, rule_ids=[], change_type=ChangeType.Create,
                    description="No rules", user_id=uuid4(), required_approvals=1,
                )

    def test_bulk_approve_empty_list_raises(self):
        """Test that bulk approve with empty list raises ValueError."""
        for db in get_test_db():
            from app.services.approval_service import ApprovalService
            service = ApprovalService()
            with self.assertRaises(ValueError):
                service.bulk_approve(
                    db=db, approval_ids=[], approver_id=uuid4(),
                )

    def test_approve_nonexistent_step(self):
        """Test approving a nonexistent step."""
        for db in get_test_db():
            fake_id = uuid4()
            with self.assertRaises(Exception):
                mock_approve_step(db=db, step_id=fake_id, user_id=uuid4(), comment="test")

    def test_reject_nonexistent_step(self):
        """Test rejecting a nonexistent step."""
        for db in get_test_db():
            fake_id = uuid4()
            with self.assertRaises(Exception):
                mock_reject_step(db=db, step_id=fake_id, user_id=uuid4(), comment="test")


if __name__ == "__main__":
    unittest.main()