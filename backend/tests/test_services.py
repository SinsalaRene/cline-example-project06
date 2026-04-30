"""
Comprehensive tests for service layer refactoring.

Tests FirewallService, ApprovalService, and AuditService after conversion
to class-based dependency injection pattern.
"""

import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def session():
    """Create a test database session with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import models locally to avoid circular imports
    from app.models.firewall_rule import Base as FirewallBase
    from app.models.approval import Base as ApprovalBase
    from app.models.audit import Base as AuditBase

    # Create all tables
    FirewallBase.metadata.create_all(bind=engine)
    ApprovalBase.metadata.create_all(bind=engine)
    AuditBase.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        AuditBase.metadata.drop_all(bind=engine)
        ApprovalBase.metadata.drop_all(bind=engine)
        FirewallBase.metadata.drop_all(bind=engine)


@pytest.fixture
def user_id():
    """Provide a test user UUID."""
    return uuid.uuid4()


@pytest.fixture
def test_firewall_data():
    """Provide test firewall rule data."""
    return {
        "rule_collection_name": "test-collection",
        "priority": 100,
        "action": "Allow",
        "protocol": "Tcp",
        "source_addresses": ["10.0.0.1"],
        "destination_fqdns": ["example.com"],
        "description": "Test firewall rule",
    }


@pytest.fixture
def test_azure_rules_data():
    """Provide test Azure rules data."""
    return [
        {
            "rule_collection_name": f"azure-collection-{i}",
            "priority": 100 + i * 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["10.0.0.1"],
            "destination_fqdns": ["example.com"],
            "description": f"Azure rule {i}",
        }
        for i in range(3)
    ]


# =============================================================================
# Helper functions to get models
# =============================================================================

def _get_firewall_models():
    """Get firewall-related models."""
    from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
    from app.models.firewall_rule import Workload
    return FirewallRule, FirewallRuleStatus, Workload


def _get_approval_models():
    """Get approval-related models."""
    from app.models.approval import (
        ApprovalRequest, ApprovalStep, ApprovalStatus, ApprovalRole, ChangeType
    )
    return ApprovalRequest, ApprovalStep, ApprovalStatus, ApprovalRole, ChangeType


def _get_audit_model():
    """Get audit model."""
    from app.models.audit import AuditLog
    return AuditLog


# =============================================================================
# FirewallService Tests
# =============================================================================

class TestFirewallService:
    """Test cases for FirewallService DI refactoring."""

    def test_service_initialization(self):
        """Test that FirewallService initializes correctly."""
        from app.services.firewall_service import FirewallService
        service = FirewallService()
        assert service._logger is not None
        assert service._logger.name == "app.services.firewall_service"

    def test_service_custom_logger_name(self):
        """Test custom logger name."""
        from app.services.firewall_service import FirewallService
        service = FirewallService(logger_name="custom.logger.name")
        assert service._logger.name == "custom.logger.name"

    def test_get_firewall_rules(self, session, user_id, test_firewall_data):
        """Test get_firewall_rules returns paginated results."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        # Create a test rule
        rule = FirewallRule(
            rule_collection_name=test_firewall_data["rule_collection_name"],
            priority=test_firewall_data["priority"],
            action=test_firewall_data["action"],
            protocol=test_firewall_data["protocol"],
            source_addresses=json.dumps(test_firewall_data.get("source_addresses")),
            destination_fqdns=json.dumps(test_firewall_data.get("destination_fqdns")),
            description=test_firewall_data.get("description"),
            created_by=user_id,
            status=FirewallRuleStatus.Pending.value,
        )
        session.add(rule)
        session.commit()

        result = service.get_firewall_rules(session, user_id)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 50
        assert len(result["items"]) == 1
        assert result["items"][0].id == rule.id

    def test_get_firewall_rules_filter_by_status(self, session, user_id, test_firewall_data):
        """Test get_firewall_rules with status filter."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        rule = FirewallRule(
            rule_collection_name="test-collection",
            priority=100,
            action="Allow",
            protocol="Tcp",
            source_addresses=json.dumps(["10.0.0.1"]),
            destination_fqdns=json.dumps(["example.com"]),
            created_by=user_id,
            status=FirewallRuleStatus.Active.value,
        )
        session.add(rule)
        session.commit()

        result = service.get_firewall_rules(session, user_id, status="Active")
        assert result["total"] == 1
        assert len(result["items"]) == 1

        result_inactive = service.get_firewall_rules(session, user_id, status="Pending")
        assert result_inactive["total"] == 0

    def test_get_firewall_rules_pagination(self, session, user_id):
        """Test get_firewall_rules pagination."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        for i in range(5):
            rule = FirewallRule(
                rule_collection_name=f"collection-{i}",
                priority=100 + i,
                action="Allow",
                protocol="Tcp",
                source_addresses=json.dumps(["10.0.0.1"]),
                destination_fqdns=json.dumps(["example.com"]),
                created_by=user_id,
                status=FirewallRuleStatus.Pending.value,
            )
            session.add(rule)
        session.commit()

        result = service.get_firewall_rules(session, user_id, page=1, page_size=2)
        assert result["total"] == 5
        assert result["page"] == 1
        assert len(result["items"]) == 2
        assert result["total_pages"] == 3

    def test_get_firewall_rules_invalid_params(self, session, user_id):
        """Test get_firewall_rules with invalid parameters."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        with pytest.raises(ValueError, match="page must be >= 1"):
            service.get_firewall_rules(session, user_id, page=0)

        with pytest.raises(ValueError, match="page_size must be >= 1"):
            service.get_firewall_rules(session, user_id, page=1, page_size=0)

    def test_get_firewall_rule_not_found(self, session, user_id):
        """Test get_firewall_rule raises ValueError for missing rule."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            service.get_firewall_rule(session, fake_id)

    def test_create_firewall_rule(self, session, user_id, test_firewall_data):
        """Test create_firewall_rule creates and returns a rule."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        rule = service.create_firewall_rule(
            db=session,
            rule_collection_name=test_firewall_data["rule_collection_name"],
            priority=test_firewall_data["priority"],
            action=test_firewall_data["action"],
            protocol=test_firewall_data["protocol"],
            source_addresses=test_firewall_data.get("source_addresses"),
            destination_fqdns=test_firewall_data.get("destination_fqdns"),
            description=test_firewall_data.get("description"),
            user_id=user_id,
        )

        assert rule.id is not None
        assert rule.rule_collection_name == test_firewall_data["rule_collection_name"]
        assert rule.priority == test_firewall_data["priority"]
        assert rule.action == test_firewall_data["action"]
        assert rule.protocol == test_firewall_data["protocol"]
        assert rule.created_by == user_id

    def test_create_firewall_rule_validation_empty_name(self):
        """Test create_firewall_rule raises ValueError for empty name."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        with pytest.raises(ValueError, match="rule_collection_name is required"):
            service.create_firewall_rule(
                db=session,
                rule_collection_name="",
                priority=100,
                action="Allow",
                protocol="Tcp",
                user_id=user_id,
            )

    def test_create_firewall_rule_validation_invalid_action(self):
        """Test create_firewall_rule raises ValueError for invalid action."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        with pytest.raises(ValueError, match="action must be"):
            service.create_firewall_rule(
                db=session,
                rule_collection_name="test",
                priority=100,
                action="InvalidAction",
                protocol="Tcp",
                user_id=user_id,
            )

    def test_create_firewall_rule_validation_invalid_protocol(self):
        """Test create_firewall_rule raises ValueError for invalid protocol."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        with pytest.raises(ValueError, match="protocol must be"):
            service.create_firewall_rule(
                db=session,
                rule_collection_name="test",
                priority=100,
                action="Allow",
                protocol="Icmp",
                user_id=user_id,
            )

    def test_create_firewall_rule_validation_priority_range(self):
        """Test create_firewall_rule raises ValueError for priority out of range."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        with pytest.raises(ValueError, match="priority must be between"):
            service.create_firewall_rule(
                db=session,
                rule_collection_name="test",
                priority=50,
                action="Allow",
                protocol="Tcp",
                user_id=user_id,
            )

    def test_update_firewall_rule(self, session, user_id):
        """Test update_firewall_rule updates and returns the rule."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        rule = service.create_firewall_rule(
            db=session,
            rule_collection_name="original-name",
            priority=100,
            action="Allow",
            protocol="Tcp",
            user_id=user_id,
        )

        updated = service.update_firewall_rule(
            db=session,
            rule_id=rule.id,
            user_id=user_id,
            description="Updated description",
            priority=200,
        )

        assert updated.description == "Updated description"
        assert updated.priority == 200
        assert updated.updated_at is not None

    def test_update_firewall_rule_not_found(self, session, user_id):
        """Test update_firewall_rule raises ValueError for missing rule."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            service.update_firewall_rule(db=session, rule_id=fake_id, user_id=user_id)

    def test_delete_firewall_rule(self, session, user_id):
        """Test delete_firewall_rule deletes and returns True."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule

        service = FirewallService()

        rule = service.create_firewall_rule(
            db=session,
            rule_collection_name="to-delete",
            priority=100,
            action="Allow",
            protocol="Tcp",
            user_id=user_id,
        )

        result = service.delete_firewall_rule(session, rule.id)
        assert result is True

        remaining = session.query(FirewallRule).filter(FirewallRule.id == rule.id).first()
        assert remaining is None

    def test_delete_firewall_rule_not_found(self, session):
        """Test delete_firewall_rule raises ValueError for missing rule."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            service.delete_firewall_rule(session, fake_id)

    def test_import_firewall_rules_from_azure(self, session, test_azure_rules_data):
        """Test import_firewall_rules_from_azure imports multiple rules."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        imported = service.import_firewall_rules_from_azure(session, test_azure_rules_data)

        assert len(imported) == 3
        for rule in imported:
            assert rule.id is not None
            assert rule.rule_collection_name is not None
            assert rule.priority is not None

    def test_import_firewall_rules_from_azure_with_errors(self, session):
        """Test import handles rules with missing required fields."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        rules_data = [
            {
                "rule_collection_name": "valid-rule",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
            },
            {
                "priority": 200,  # Missing rule_collection_name
                "action": "Deny",
                "protocol": "Udp",
            },
            {
                "rule_collection_name": "another-valid",
                "priority": 300,
                "action": "Allow",
                "protocol": "Tcp",
            },
        ]

        imported = service.import_firewall_rules_from_azure(session, rules_data)
        assert len(imported) == 2

    def test_import_firewall_rules_from_azure_empty_list(self, session):
        """Test import with empty list."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        imported = service.import_firewall_rules_from_azure(session, [])
        assert imported == []


class TestWorkloadService:
    """Test cases for WorkloadService DI refactoring."""

    def test_service_initialization(self):
        """Test WorkloadService initializes correctly."""
        from app.services.firewall_service import WorkloadService

        service = WorkloadService()
        assert service._logger is not None

    def test_get_workloads_empty(self, session):
        """Test get_workloads returns empty list when none exist."""
        from app.services.firewall_service import WorkloadService

        service = WorkloadService()
        result = service.get_workloads(session)
        assert result == []

    def test_create_workload(self, session):
        """Test create_workload creates and returns a workload."""
        from app.services.firewall_service import WorkloadService

        service = WorkloadService()
        service_id = uuid.uuid4()

        workload = service.create_workload(
            db=session,
            name="test-workload",
            description="Test workload",
            owner_id=service_id,
        )

        assert workload.id is not None
        assert workload.name == "test-workload"
        assert workload.description == "Test workload"
        assert workload.owner_id == service_id

    def test_create_workload_empty_name(self, session):
        """Test create_workload raises ValueError for empty name."""
        from app.services.firewall_service import WorkloadService

        service = WorkloadService()
        with pytest.raises(ValueError, match="name is required"):
            service.create_workload(db=session, name="")

    def test_get_workload_not_found(self, session):
        """Test get_workload raises ValueError for missing workload."""
        from app.services.firewall_service import WorkloadService

        service = WorkloadService()
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            service.get_workload(session, fake_id)

    def test_update_workload(self, session):
        """Test update_workload updates and returns the workload."""
        from app.services.firewall_service import WorkloadService

        service = WorkloadService()

        workload = service.create_workload(
            db=session,
            name="original-name",
            description="Original description",
        )

        updated = service.update_workload(
            db=session,
            workload_id=workload.id,
            name="updated-name",
            description="Updated description",
        )

        assert updated.name == "updated-name"
        assert updated.description == "Updated description"

    def test_delete_workload(self, session):
        """Test delete_workload deletes and returns True."""
        from app.services.firewall_service import WorkloadService
        from app.models.firewall_rule import Workload

        service = WorkloadService()

        workload = service.create_workload(
            db=session,
            name="to-delete",
            description="Will be deleted",
        )

        result = service.delete_workload(session, workload.id)
        assert result is True

        # Reload and verify deletion
        session.expire_all()
        remaining = session.get(Workload, workload.id)
        assert remaining is None


# =============================================================================
# ApprovalService Tests
# =============================================================================

class TestApprovalService:
    """Test cases for ApprovalService DI refactoring."""

    def test_service_initialization(self):
        """Test ApprovalService initializes correctly."""
        from app.services.approval_service import ApprovalService

        service = ApprovalService()
        assert service._logger is not None
        assert service._default_timeout_hours == 48

    def test_service_custom_timeout(self):
        """Test ApprovalService with custom timeout."""
        from app.services.approval_service import ApprovalService

        service = ApprovalService(default_timeout_hours=24)
        assert service._default_timeout_hours == 24

    def test_create_approval_request(self, session, user_id):
        """Test create_approval_request creates request with steps."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ChangeType

        service = ApprovalService()
        rule_id_1 = uuid.uuid4()
        rule_id_2 = uuid.uuid4()

        request = service.create_approval_request(
            db=session,
            rule_ids=[rule_id_1, rule_id_2],
            change_type=ChangeType.Create,
            description="Test approval",
            user_id=user_id,
        )

        assert request.id is not None
        assert request.change_type == ChangeType.Create
        assert request.description == "Test approval"
        assert request.required_approvals == 2

        # Verify steps were created
        from app.models.approval import ApprovalStep, ApprovalRole
        steps = session.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == request.id
        ).all()
        assert len(steps) == 2
        assert steps[0].approver_role == ApprovalRole.WorkloadStakeholder
        assert steps[1].approver_role == ApprovalRole.SecurityStakeholder

    def test_create_approval_request_empty_rule_ids(self, session):
        """Test create_approval_request raises ValueError for empty rule_ids."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ChangeType

        service = ApprovalService()
        with pytest.raises(ValueError, match="At least one rule ID"):
            service.create_approval_request(
                db=session,
                rule_ids=[],
                change_type=ChangeType.Create,
                description="Test approval",
                user_id=user_id,
            )

    def test_create_approval_request_empty_description(self, session):
        """Test create_approval_request raises ValueError for empty description."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ChangeType

        service = ApprovalService()
        with pytest.raises(ValueError, match="description is required"):
            service.create_approval_request(
                db=session,
                rule_ids=[uuid.uuid4()],
                change_type=ChangeType.Create,
                description="",
                user_id=user_id,
            )

    def test_approve_step(self, session, user_id):
        """Test approve_step updates step status."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus, ChangeType

        service = ApprovalService()

        request = service.create_approval_request(
            db=session,
            rule_ids=[uuid.uuid4()],
            change_type=ChangeType.Create,
            description="Test approval",
            user_id=user_id,
        )

        from app.models.approval import ApprovalStep
        step = session.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == request.id
        ).first()

        assert step.status == ApprovalStatus.Pending
        approver_id = uuid.uuid4()
        approved = service.approve_step(
            db=session,
            step_id=step.id,
            approver_id=approver_id,
            comment="Looks good",
        )

        assert approved.status == ApprovalStatus.Approved
        # approver_id is stored as UUID in the model, compare directly
        assert approved.approver_id == approver_id
        assert approved.comments == "Looks good"
        assert approved.approved_at is not None

    def test_approve_step_not_found(self, session):
        """Test approve_step raises ValueError for missing step."""
        from app.services.approval_service import ApprovalService

        service = ApprovalService()
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            service.approve_step(db=session, step_id=fake_id, approver_id=uuid.uuid4())

    def test_approve_step_already_approved(self, session, user_id):
        """Test approve_step raises ValueError for already approved step."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus, ChangeType

        service = ApprovalService()

        request = service.create_approval_request(
            db=session,
            rule_ids=[uuid.uuid4()],
            change_type=ChangeType.Create,
            description="Test approval",
            user_id=user_id,
        )

        from app.models.approval import ApprovalStep
        step = session.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == request.id
        ).first()

        service.approve_step(db=session, step_id=step.id, approver_id=user_id)

        with pytest.raises(ValueError, match="already approved"):
            service.approve_step(db=session, step_id=step.id, approver_id=user_id)

    def test_reject_step(self, session, user_id):
        """Test reject_step updates step and request status."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus, ChangeType

        service = ApprovalService()

        request = service.create_approval_request(
            db=session,
            rule_ids=[uuid.uuid4()],
            change_type=ChangeType.Create,
            description="Test approval",
            user_id=user_id,
        )

        from app.models.approval import ApprovalStep, ApprovalRequest
        step = session.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == request.id
        ).first()

        rejected = service.reject_step(
            db=session,
            step_id=step.id,
            approver_id=user_id,
            comment="Not approved",
        )

        assert rejected.status == ApprovalStatus.Rejected
        assert rejected.comments == "Not approved"

        # Reload request
        session.refresh(request)
        assert request.status == ApprovalStatus.Rejected

    def test_reject_step_missing_comment(self, session, user_id):
        """Test reject_step raises ValueError for empty comment."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ChangeType

        service = ApprovalService()

        request = service.create_approval_request(
            db=session,
            rule_ids=[uuid.uuid4()],
            change_type=ChangeType.Create,
            description="Test approval",
            user_id=user_id,
        )

        from app.models.approval import ApprovalStep
        step = session.query(ApprovalStep).filter(
            ApprovalStep.approval_request_id == request.id
        ).first()

        with pytest.raises(ValueError, match="comment is required"):
            service.reject_step(db=session, step_id=step.id, approver_id=user_id, comment="")

    def test_get_approval_requests(self, session, user_id):
        """Test get_approval_requests returns paginated results."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ChangeType

        service = ApprovalService()

        for i in range(3):
            service.create_approval_request(
                db=session,
                rule_ids=[uuid.uuid4()],
                change_type=ChangeType.Create,
                description=f"Request {i}",
                user_id=user_id,
            )

        result = service.get_approval_requests(session, user_id)

        assert result["total"] == 3
        assert result["page"] == 1
        assert len(result["items"]) == 3

    def test_get_approval_requests_pagination(self, session, user_id):
        """Test get_approval_requests with pagination."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ChangeType

        service = ApprovalService()

        for i in range(5):
            service.create_approval_request(
                db=session,
                rule_ids=[uuid.uuid4()],
                change_type=ChangeType.Create,
                description=f"Request {i}",
                user_id=user_id,
            )

        result = service.get_approval_requests(session, user_id, page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["total_pages"] == 3

    def test_get_approval_requests_invalid_params(self, session, user_id):
        """Test get_approval_requests with invalid pagination params."""
        from app.services.approval_service import ApprovalService

        service = ApprovalService()
        with pytest.raises(ValueError, match="page must be >= 1"):
            service.get_approval_requests(session, user_id, page=0)

    def test_check_and_expire_pending_approvals(self, session):
        """Test check_and_expire_pending_approvals expires old requests."""
        from app.services.approval_service import ApprovalService
        from app.models.approval import ApprovalStatus, ChangeType, ApprovalRequest

        service = ApprovalService(default_timeout_hours=1)

        request = service.create_approval_request(
            db=session,
            rule_ids=[uuid.uuid4()],
            change_type=ChangeType.Create,
            description="Old request",
            user_id=uuid.uuid4(),
        )

        # Manually set created_at to 2 hours ago
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        session.query(ApprovalRequest).filter(
            ApprovalRequest.id == request.id
        ).update({
            ApprovalRequest.created_at: old_time,
        })
        session.commit()

        expired_count = service.check_and_expire_pending_approvals(session)
        assert expired_count == 1

        session.refresh(request)
        assert request.status == ApprovalStatus.Expired


# =============================================================================
# AuditService Tests
# =============================================================================

class TestAuditService:
    """Test cases for AuditService DI refactoring."""

    def test_service_initialization(self):
        """Test AuditService initializes correctly."""
        from app.services.audit_service import AuditService

        service = AuditService()
        assert service._logger is not None

    def test_log_action(self, session, user_id):
        """Test log_action creates an audit entry."""
        from app.services.audit_service import AuditService

        service = AuditService()
        rule_id = uuid.uuid4()

        entry = service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value=None,
            new_value={"priority": 100, "action": "Allow"},
            ip_address="192.168.1.1",
            correlation_id=rule_id,
        )

        assert entry.id is not None
        # user_id is stored as UUID in the model, compare directly
        assert entry.user_id == user_id
        assert entry.action == "CREATE"
        assert entry.resource_type == "firewall_rule"
        assert entry.resource_id == str(rule_id)
        assert entry.ip_address == "192.168.1.1"

    def test_log_action_with_json_values(self, session, user_id):
        """Test log_action serializes dict values to JSON."""
        from app.services.audit_service import AuditService

        service = AuditService()
        rule_id = uuid.uuid4()

        entry = service.log_action(
            db=session,
            user_id=user_id,
            action="UPDATE",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value={"priority": 100},
            new_value={"priority": 200},
        )

        # Verify JSON serialization
        assert json.loads(entry.old_value) == {"priority": 100}
        assert json.loads(entry.new_value) == {"priority": 200}

    def test_get_audit_logs(self, session, user_id):
        """Test get_audit_logs returns paginated results."""
        from app.services.audit_service import AuditService

        service = AuditService()

        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )
        service.log_action(
            db=session,
            user_id=user_id,
            action="UPDATE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )

        result = service.get_audit_logs(session, user_id=user_id)

        assert result["total"] == 2
        assert result["page"] == 1
        assert len(result["items"]) == 2

    def test_get_audit_logs_filter_by_action(self, session, user_id):
        """Test get_audit_logs filters by action."""
        from app.services.audit_service import AuditService

        service = AuditService()

        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )
        service.log_action(
            db=session,
            user_id=user_id,
            action="DELETE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )

        result = service.get_audit_logs(session, user_id=user_id, action="CREATE")
        assert result["total"] == 1
        assert result["items"][0].action == "CREATE"

    def test_get_audit_logs_filter_by_resource_type(self, session, user_id):
        """Test get_audit_logs filters by resource type."""
        from app.services.audit_service import AuditService

        service = AuditService()

        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )
        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="approval",
            resource_id=str(uuid.uuid4()),
        )

        result_fw = service.get_audit_logs(
            session, user_id=user_id, resource_type="firewall_rule"
        )
        assert result_fw["total"] == 1
        assert result_fw["items"][0].resource_type == "firewall_rule"

    def test_get_audit_for_resource(self, session, user_id):
        """Test get_audit_for_resource returns logs for specific resource."""
        from app.services.audit_service import AuditService

        service = AuditService()
        rule_id = uuid.uuid4()

        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
        )
        service.log_action(
            db=session,
            user_id=user_id,
            action="UPDATE",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
        )
        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="approval",
            resource_id=str(uuid.uuid4()),
        )

        logs = service.get_audit_for_resource(
            session, "firewall_rule", str(rule_id)
        )
        assert len(logs) == 2

    def test_get_audit_for_user(self, session, user_id):
        """Test get_audit_for_user returns logs for specific user."""
        from app.services.audit_service import AuditService

        service = AuditService()
        other_user = uuid.uuid4()

        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )
        service.log_action(
            db=session,
            user_id=other_user,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )

        logs = service.get_audit_for_user(session, user_id)
        assert len(logs) == 1
        assert str(logs[0].user_id) == str(user_id)

    def test_export_audit_logs(self, session, user_id):
        """Test export_audit_logs returns serializable dict list."""
        from app.services.audit_service import AuditService

        service = AuditService()

        rule_id = uuid.uuid4()
        service.log_action(
            db=session,
            user_id=user_id,
            action="CREATE",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value={"status": "pending"},
            new_value={"status": "active"},
        )

        exported = service.export_audit_logs(session)
        assert len(exported) == 1
        assert exported[0]["action"] == "CREATE"
        assert exported[0]["resource_type"] == "firewall_rule"
        assert exported[0]["old_value"] == {"status": "pending"}
        assert exported[0]["new_value"] == {"status": "active"}
        assert "timestamp" in exported[0]

    def test_log_firewall_rule_change(self, session, user_id):
        """Test log_firewall_rule_change convenience method."""
        from app.services.audit_service import AuditService

        service = AuditService()
        rule_id = uuid.uuid4()

        entry = service.log_firewall_rule_change(
            db=session,
            user_id=user_id,
            action="UPDATE",
            rule_id=rule_id,
            old_data={"priority": 100},
            new_data={"priority": 200},
            ip_address="10.0.0.1",
        )

        assert entry.resource_type == "firewall_rule"
        assert entry.action == "UPDATE"
        assert entry.resource_id == str(rule_id)

    def test_log_approval_change(self, session, user_id):
        """Test log_approval_change convenience method."""
        from app.services.audit_service import AuditService

        service = AuditService()
        approval_id = uuid.uuid4()

        entry = service.log_approval_change(
            db=session,
            user_id=user_id,
            action="APPROVE",
            approval_id=approval_id,
            old_data={"status": "pending"},
            new_data={"status": "approved"},
        )

        assert entry.resource_type == "approval"
        assert entry.action == "APPROVE"
        assert entry.resource_id == str(approval_id)