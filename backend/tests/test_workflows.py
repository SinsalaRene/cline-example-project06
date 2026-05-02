"""
Tests for cross-module workflow integration (Task 7.2).

Tests cover:
- ApprovalWorkflow: approval-triggered rule changes
- AuditWorkflow: audit logging for all operations
- NotificationWorkflow: notification delivery
- Integration: workflows wired correctly in ApprovalService
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, ANY
from uuid import UUID, uuid4

import pytest

from app.models.approval import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalStatus,
    ApprovalRole,
    ChangeType,
)
from app.models.audit import AuditLog
from app.models.firewall_rule import FirewallRule, FirewallRuleStatus


# ============================================================================
# Fixtures
# ============================================================================

def _make_approval_request(
    change_type: ChangeType = ChangeType.Create,
    status: ApprovalStatus = ApprovalStatus.Pending,
    rule_ids: list = None,
    applied_from=None,
    applied_until=None,
):
    """Create a minimal ApprovalRequest mock."""
    ar = MagicMock(spec=ApprovalRequest)
    ar.id = uuid4()
    ar.change_type = change_type
    ar.status = status
    ar.description = "Test approval"
    ar.current_user_id = uuid4()
    ar.required_approvals = 2
    ar.workload_id = uuid4()
    ar.completed_at = None

    if rule_ids is None:
        rule_ids = [uuid4()]
    ar.rule_uuids = rule_ids
    ar.rule_ids_json = json.dumps([str(r) for r in rule_ids])
    ar.rule_ids = ar.rule_ids_json  # alias used by _parse_rule_ids

    now = datetime.now(timezone.utc)
    ar.created_at = now
    ar.applied_from = applied_from
    ar.applied_until = applied_until
    return ar


def _make_approval_step(approval_request, status=ApprovalStatus.Pending, role=ApprovalRole.WorkloadStakeholder):
    """Create a minimal ApprovalStep mock."""
    step = MagicMock(spec=ApprovalStep)
    step.id = uuid4()
    step.approval_request = approval_request
    step.approval_request_id = approval_request.id
    step.approver_role = role
    step.status = status
    step.comments = ""
    step.approved_at = None
    step.approver_id = None
    step.created_at = datetime.now(timezone.utc)
    step.updated_at = None
    return step


def _make_firewall_rule(rule_id=None, status=FirewallRuleStatus.Active):
    """Create a minimal FirewallRule mock."""
    rule = MagicMock(spec=FirewallRule)
    rule.id = rule_id or uuid4()
    rule.status = status
    rule.updated_at = None
    rule.created_at = datetime.now(timezone.utc)
    return rule


# ============================================================================
# ApprovalWorkflow Tests
# ============================================================================

class TestApprovalWorkflow:
    """Tests for ApprovalWorkflow."""

    def test_on_approval_completed_applies_rules(self):
        """on_approval_completed should update firewall rules when approval is approved."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        approval = _make_approval_request(
            change_type=ChangeType.Create,
            status=ApprovalStatus.Approved,
            rule_ids=[uuid4(), uuid4()],
        )

        mock_db = MagicMock()
        mock_rule_1 = _make_firewall_rule(
            rule_id=approval.rule_uuids[0], status=FirewallRuleStatus.Pending
        )
        mock_rule_2 = _make_firewall_rule(
            rule_id=approval.rule_uuids[1], status=FirewallRuleStatus.Pending
        )

        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.filter.return_value.first.side_effect = [mock_rule_1, mock_rule_2]
        mock_db.query.return_value = query_mock

        wf = ApprovalWorkflow()

        # Suppress notification
        wf._dispatch_approval_notification = MagicMock(return_value=0)
        # Suppress audit
        wf._audit_service = MagicMock()

        result = wf.on_approval_completed(mock_db, approval, uuid4())

        assert result["rules_applied"] == 2
        assert result["audit_logged"] is True
        assert mock_rule_1.status == FirewallRuleStatus.Active
        assert mock_rule_2.status == FirewallRuleStatus.Active

    def test_on_approval_completed_skips_for_rejected(self):
        """on_approval_completed should skip rule application for REJECTED."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        approval = _make_approval_request(
            change_type=ChangeType.Update,
            status=ApprovalStatus.Rejected,
        )

        mock_db = MagicMock()
        wf = ApprovalWorkflow()
        wf._dispatch_approval_notification = MagicMock(return_value=0)
        wf._audit_service = MagicMock()

        result = wf.on_approval_completed(mock_db, approval, uuid4())

        assert result["rules_applied"] == 0

    def test_on_approval_completed_no_rule_ids(self):
        """on_approval_completed should return immediately when no rule_ids present."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        approval = _make_approval_request(rule_ids=[])
        approval.rule_ids_json = "[]"
        approval.rule_ids = "[]"

        mock_db = MagicMock()
        wf = ApprovalWorkflow()
        wf._dispatch_approval_notification = MagicMock(return_value=0)
        wf._audit_service = MagicMock()

        result = wf.on_approval_completed(mock_db, approval, uuid4())

        assert result["rules_applied"] == 0

    def test_on_approval_completed_parsing_fails_gracefully(self):
        """_parse_rule_ids should return empty list on invalid JSON."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        wf = ApprovalWorkflow()
        result = wf._parse_rule_ids("not-json")
        assert result == []

    def test_on_approval_completed_uses_audit_service(self):
        """on_approval_completed should call audit_service.log_action."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        approval = _make_approval_request(
            change_type=ChangeType.Create,
            status=ApprovalStatus.Approved,
        )

        mock_db = MagicMock()
        mock_audit = MagicMock()
        mock_audit.log_action.return_value = True

        wf = ApprovalWorkflow(audit_service=mock_audit)
        wf._dispatch_approval_notification = MagicMock(return_value=0)

        result = wf.on_approval_completed(mock_db, approval, uuid4())

        mock_audit.log_action.assert_called_once()
        assert result["audit_logged"] is True

    def test_on_approval_completed_sends_notification(self):
        """on_approval_completed should send notification for approved status."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        approval = _make_approval_request(
            change_type=ChangeType.Create,
            status=ApprovalStatus.Approved,
        )

        mock_db = MagicMock()
        wf = ApprovalWorkflow()
        wf._audit_service = MagicMock()

        call_count = [0]

        def capture_notification(*args, **kwargs):
            call_count[0] += 1
            return 1

        wf._dispatch_approval_notification = capture_notification

        result = wf.on_approval_completed(mock_db, approval, uuid4())

        assert call_count[0] == 1

    def test_on_approval_created(self):
        """on_approval_created should send notification and audit."""
        from app.workflows.approval_workflow import ApprovalWorkflow

        approval = _make_approval_request(change_type=ChangeType.Create)

        mock_db = MagicMock()
        mock_audit = MagicMock()
        mock_audit.log_action.return_value = True

        wf = ApprovalWorkflow(audit_service=mock_audit)
        wf._dispatch_notification_for_creation = MagicMock(return_value=1)

        result = wf.on_approval_created(mock_db, approval, uuid4())

        assert result["notifications_sent"] == 1
        assert result["audit_logged"] is True


# ============================================================================
# AuditWorkflow Tests
# ============================================================================

class TestAuditWorkflow:
    """Tests for AuditWorkflow."""

    def test_log_api_operation_success(self):
        """log_api_operation should call audit_service.log_action."""
        from app.workflows.audit_workflow import AuditWorkflow

        mock_audit_service = MagicMock()
        mock_audit_service.log_action.return_value = True
        workflow = AuditWorkflow(audit_service=mock_audit_service)

        mock_db = MagicMock()
        user_id = uuid4()
        resource_id = str(uuid4())

        result = workflow.log_api_operation(
            db=mock_db,
            user_id=user_id,
            action="test_action",
            resource_type="test_type",
            resource_id=resource_id,
            old_value={"old": "data"},
            new_value={"new": "data"},
        )

        assert result is True
        mock_audit_service.log_action.assert_called_once()

    def test_log_api_operation_failure(self):
        """log_api_operation should return False on audit_service failure."""
        from app.workflows.audit_workflow import AuditWorkflow

        mock_audit_service = MagicMock()
        mock_audit_service.log_action.side_effect = Exception("DB error")
        workflow = AuditWorkflow(audit_service=mock_audit_service)

        mock_db = MagicMock()
        user_id = uuid4()
        resource_id = str(uuid4())

        result = workflow.log_api_operation(
            db=mock_db,
            user_id=user_id,
            action="test_action",
            resource_type="test_type",
            resource_id=resource_id,
        )

        assert result is False

    def test_log_firewall_rule_created(self):
        from app.workflows.audit_workflow import AuditWorkflow
        workflow = AuditWorkflow()
        mock_db = MagicMock()
        user_id = uuid4()
        rule_id = uuid4()

        with patch.object(workflow, "log_api_operation", return_value=True) as mock_log:
            result = workflow.log_firewall_rule_created(
                db=mock_db,
                user_id=user_id,
                rule_id=rule_id,
                rule_data={"name": "test-rule"},
            )
            assert result is True
            call_args = mock_log.call_args
            assert call_args[1]["action"] == "create"

    def test_log_firewall_rule_updated(self):
        from app.workflows.audit_workflow import AuditWorkflow
        workflow = AuditWorkflow()
        mock_db = MagicMock()
        user_id = uuid4()
        rule_id = uuid4()

        with patch.object(workflow, "log_api_operation", return_value=True) as mock_log:
            result = workflow.log_firewall_rule_updated(
                db=mock_db,
                user_id=user_id,
                rule_id=rule_id,
                old_data={"name": "old"},
                new_data={"name": "new"},
            )
            assert result is True
            call_args = mock_log.call_args
            assert call_args[1]["action"] == "update"

    def test_log_firewall_rule_deleted(self):
        from app.workflows.audit_workflow import AuditWorkflow
        workflow = AuditWorkflow()
        mock_db = MagicMock()
        user_id = uuid4()
        rule_id = uuid4()

        with patch.object(workflow, "log_api_operation", return_value=True) as mock_log:
            result = workflow.log_firewall_rule_deleted(
                db=mock_db,
                user_id=user_id,
                rule_id=rule_id,
                old_data={"name": "old-rule"},
            )
            assert result is True
            call_args = mock_log.call_args
            assert call_args[1]["action"] == "delete"

    def test_log_approval_approved(self):
        from app.workflows.audit_workflow import AuditWorkflow
        workflow = AuditWorkflow()
        mock_db = MagicMock()
        user_id = uuid4()
        approval_id = uuid4()

        with patch.object(workflow, "log_api_operation", return_value=True) as mock_log:
            result = workflow.log_approval_approved(
                db=mock_db,
                user_id=user_id,
                approval_id=approval_id,
                comment="Approved",
            )
            assert result is True
            call_args = mock_log.call_args
            assert call_args[1]["action"] == "approve"

    def test_log_approval_rejected(self):
        from app.workflows.audit_workflow import AuditWorkflow
        workflow = AuditWorkflow()
        mock_db = MagicMock()
        user_id = uuid4()
        approval_id = uuid4()

        with patch.object(workflow, "log_api_operation", return_value=True) as mock_log:
            result = workflow.log_approval_rejected(
                db=mock_db,
                user_id=user_id,
                approval_id=approval_id,
                comment="Rejected",
            )
            assert result is True
            call_args = mock_log.call_args
            assert call_args[1]["action"] == "reject"

    def test_log_bulk_operation(self):
        from app.workflows.audit_workflow import AuditWorkflow
        workflow = AuditWorkflow()
        mock_db = MagicMock()
        user_id = uuid4()

        with patch.object(workflow, "log_api_operation", return_value=True) as mock_log:
            result = workflow.log_bulk_operation(
                db=mock_db,
                user_id=user_id,
                action="bulk_update",
                resource_type="firewall_rule",
                resource_ids=[str(uuid4()) for _ in range(5)],
                count=5,
            )
            assert result is True
            call_args = mock_log.call_args
            assert call_args[1]["action"] == "bulk_update"


# ============================================================================
# NotificationWorkflow Tests
# ============================================================================

class TestNotificationWorkflow:
    """Tests for NotificationWorkflow."""

    def test_send_approval_notification_success(self):
        """send_approval_notification should deliver via the specified channel."""
        from app.workflows.notification_workflow import NotificationWorkflow
        from app.workflows.notification_workflow import NotificationResult

        mock_service = MagicMock()
        mock_service.send_approval_notification.return_value = True

        workflow = NotificationWorkflow(notification_service=mock_service)
        mock_db = MagicMock()
        approval = _make_approval_request()

        result = workflow.send_approval_notification(
            db=mock_db,
            approval_request=approval,
            notification_type="approval_approved",
            channel="email",
            recipient_email="user@example.com",
            recipient_name="Test User",
        )

        assert result.success is True

    def test_send_approval_notification_failure(self):
        """send_approval_notification should return False on error."""
        from app.workflows.notification_workflow import NotificationWorkflow

        mock_service = MagicMock()
        mock_service.send_approval_notification.side_effect = Exception("SMTP error")

        workflow = NotificationWorkflow(notification_service=mock_service)
        mock_db = MagicMock()
        approval = _make_approval_request()

        result = workflow.send_approval_notification(
            db=mock_db,
            approval_request=approval,
            notification_type="approval_approved",
            channel="email",
            recipient_email="user@example.com",
            recipient_name="Test User",
        )

        assert result.success is False

    def test_send_bulk_approval_notifications(self):
        """send_bulk_approval_notifications should send to all recipients."""
        from app.workflows.notification_workflow import NotificationWorkflow

        mock_service = MagicMock()
        mock_service.send_approval_notification.return_value = True

        workflow = NotificationWorkflow(notification_service=mock_service)
        mock_db = MagicMock()
        approval = _make_approval_request()

        recipients = [
            {"email": "user1@example.com", "name": "User One"},
            {"email": "user2@example.com", "name": "User Two"},
        ]

        results = workflow.send_bulk_approval_notifications(
            db=mock_db,
            approval_request=approval,
            notification_type="approval_approved",
            recipients=recipients,
        )

        assert len(results) == 2
        assert all(r.success is True for r in results)

    def test_send_azure_sync_notification(self):
        """send_azure_sync_notification should call the underlying send_notification."""
        from app.workflows.notification_workflow import NotificationWorkflow

        mock_service = MagicMock()
        mock_service.send_notification.return_value = True

        workflow = NotificationWorkflow(notification_service=mock_service)
        mock_db = MagicMock()

        result = workflow.send_azure_sync_notification(
            db=mock_db,
            sync_type="full",
            rules_synced=10,
            rules_updated=2,
            rules_created=3,
            rules_deleted=1,
            errors=["Timeout on rule 5"],
            user_id=uuid4(),
        )

        assert result.success is True

    def test_send_system_notification(self):
        """send_system_notification should call the underlying send_notification."""
        from app.workflows.notification_workflow import NotificationWorkflow

        mock_service = MagicMock()
        mock_service.send_notification.return_value = True

        workflow = NotificationWorkflow(notification_service=mock_service)
        mock_db = MagicMock()

        result = workflow.send_system_notification(
            db=mock_db,
            title="System Update",
            body="Maintenance scheduled",
            recipient_email="admin@example.com",
            recipient_name="Admin",
            severity="info",
        )

        assert result.success is True


# ============================================================================
# Integration Tests: ApprovalService -> Workflows
# ============================================================================

class TestApprovalServiceWorkflowIntegration:
    """Tests for ApprovalService integration with workflows."""

    def test_init_accepts_workflows(self):
        """ApprovalService.__init__ should accept workflow instances."""
        from app.services.approval_service import ApprovalService
        from app.workflows.approval_workflow import ApprovalWorkflow
        from app.workflows.audit_workflow import AuditWorkflow
        from app.workflows.notification_workflow import NotificationWorkflow

        approval_wf = ApprovalWorkflow()
        audit_wf = AuditWorkflow()
        notify_wf = NotificationWorkflow()

        service = ApprovalService(
            approval_workflow=approval_wf,
            audit_workflow=audit_wf,
            notification_workflow=notify_wf,
        )

        assert service._approval_workflow is approval_wf
        assert service._audit_workflow is audit_wf
        assert service._notification_workflow is notify_wf

    def test_create_approval_request_logs_to_audit(self):
        """create_approval_request should create in DB and trigger audit."""
        from app.services.approval_service import ApprovalService
        from app.workflows.audit_workflow import AuditWorkflow
        from app.models.approval import ChangeType

        mock_db = MagicMock()
        mock_db.query = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        audit_wf = AuditWorkflow()
        service = ApprovalService(audit_workflow=audit_wf)

        mock_step_instance = MagicMock()
        mock_step_instance.id = uuid4()

        mock_step_query = MagicMock()
        mock_step_query.filter.return_value = mock_step_query
        mock_step_query.order_by.return_value = mock_step_query
        mock_step_query.first.return_value = mock_step_instance

        mock_request_query = MagicMock()
        mock_request_query.filter.return_value = mock_request_query
        mock_request_query.first.return_value = None

        mock_db.query.side_effect = [
            mock_request_query,
            mock_step_query,
        ]

        approval = service.create_approval_request(
            db=mock_db,
            rule_ids=[uuid4()],
            change_type=ChangeType.Create,
            description="Test approval",
            user_id=uuid4(),
        )

        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_approve_step_applies_rules_when_all_done(self):
        """When all approval steps are done, approve_step should trigger workflows."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus, ApprovalRole

        mock_db = MagicMock()
        mock_db.query = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.flush = MagicMock()
        mock_db.refresh = MagicMock()

        approval = _make_approval_request()
        approval.status = ApprovalStatus.Pending

        step1 = _make_approval_step(approval, status=ApprovalStatus.Approved)
        step2 = _make_approval_step(approval, status=ApprovalStatus.Pending)

        step_query = MagicMock()
        step_query.filter.return_value = step_query
        step_query.first.return_value = step2
        mock_db.query.return_value = step_query

        pending_query = MagicMock()
        pending_query.filter.return_value = pending_query
        pending_query.order_by.return_value = pending_query
        pending_query.all.side_effect = [[step2], []]
        mock_db.query.side_effect = [
            step_query,
            step_query,
            pending_query,
            pending_query,
        ]

        from app.workflows.approval_workflow import ApprovalWorkflow
        from app.workflows.audit_workflow import AuditWorkflow
        from app.workflows.notification_workflow import NotificationWorkflow

        approval_wf = ApprovalWorkflow()
        audit_wf = AuditWorkflow()
        notify_wf = NotificationWorkflow()

        service = ApprovalService(
            approval_workflow=approval_wf,
            audit_workflow=audit_wf,
            notification_workflow=notify_wf,
        )

        result = service.approve_step(
            db=mock_db,
            step_id=step2.id,
            approver_id=uuid4(),
            comment="All steps done",
        )

        assert result is not None
        assert step2.status == ApprovalStatus.Approved

    def test_bulk_approve_sends_notifications(self):
        """bulk_approve should send notifications after successful approvals."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus

        mock_db = MagicMock()
        mock_db.query = MagicMock()
        mock_db.commit = MagicMock()

        approval = _make_approval_request()
        approval.status = ApprovalStatus.Pending

        step = _make_approval_step(approval)
        step.status = ApprovalStatus.Pending

        query = MagicMock()
        query.filter.return_value = query
        query.first.return_value = approval
        query.all.return_value = [step]
        mock_db.query.return_value = query

        service = ApprovalService()

        result = service.bulk_approve(
            db=mock_db,
            approval_ids=[approval.id],
            approver_id=uuid4(),
            comment="Bulk approved",
        )

        assert "approved_ids" in result
        assert len(result["approved_ids"]) == 1

    def test_bulk_reject(self):
        """bulk_reject should reject multiple approvals."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus

        mock_db = MagicMock()
        mock_db.query = MagicMock()
        mock_db.commit = MagicMock()

        approval = _make_approval_request()
        approval.status = ApprovalStatus.Pending

        step = _make_approval_step(approval)
        step.status = ApprovalStatus.Pending

        query = MagicMock()
        query.filter.return_value = query
        query.first.return_value = approval
        query.all.return_value = [step]
        mock_db.query.return_value = query

        service = ApprovalService()

        result = service.bulk_reject(
            db=mock_db,
            approval_ids=[approval.id],
            approver_id=uuid4(),
            comment="Bulk rejected",
        )

        assert "rejected_ids" in result
        assert len(result["rejected_ids"]) == 1

    def test_handle_timeout_escalation(self):
        """handle_timeout_escalation should expire timed-out requests."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus

        mock_db = MagicMock()
        mock_db.query = MagicMock()
        mock_db.commit = MagicMock()

        approval = _make_approval_request()
        approval.status = ApprovalStatus.Pending
        approval.created_at = datetime.now(timezone.utc) - timedelta(hours=72)

        query = MagicMock()
        query.filter.return_value = query
        query.all.return_value = [approval]
        mock_db.query.return_value = query

        service = ApprovalService(default_timeout_hours=48)

        result = service.handle_timeout_escalation(
            db=mock_db,
            timeout_hours=48,
        )

        assert "expired_count" in result
        assert "details" in result