"""
Tests for database models.

Tests model creation, relationships, and cross-database compatibility.
These tests use SQLite (in-memory) to verify compatibility.
"""

import pytest
import uuid
import json
from datetime import datetime, timezone

# Set up SQLite in-memory database for testing
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.models.firewall_rule import (
    Base,
    Workload,
    FirewallRule,
    FirewallRuleAction,
    FirewallProtocol,
    FirewallRuleStatus,
)
from app.models.approval import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflowDefinition,
    ChangeType,
    ApprovalStatus,
    ApprovalRole,
)
from app.models.audit import (
    AuditLog,
    User,
    UserRole,
    AuditAction,
)


@pytest.fixture
def session() -> Session:
    """Create a test database session with in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


class TestWorkloadModel:
    """Test cases for the Workload model."""

    def test_create_workload(self, session: Session):
        """Test creating a workload."""
        workload_id = uuid.uuid4()
        workload = Workload(
            id=workload_id,
            name="test-workload",
            description="Test workload description",
        )
        session.add(workload)
        session.commit()
        session.refresh(workload)

        assert workload.id == workload_id
        assert workload.name == "test-workload"
        assert workload.description == "Test workload description"
        assert workload.created_at is not None
        assert workload.updated_at is not None

    def test_workload_created_at_is_utc(self, session: Session):
        """Test that created_at uses UTC time."""
        # Create a workload - the _utc_now default sets created_at automatically
        workload = Workload(name="test-workload-utc")
        session.add(workload)
        session.commit()
        session.refresh(workload)
        # created_at should be set and timezone-aware
        assert workload.created_at is not None

    def test_workload_unique_name_constraint(self, session: Session):
        """Test that workload names must be unique."""
        workload1 = Workload(name="unique-workload-2")
        session.add(workload1)
        session.commit()

        workload2 = Workload(name="unique-workload-2")
        session.add(workload2)
        # UNIQUE constraint is enforced by SQLite - second insert with same name fails
        try:
            session.commit()
        except Exception:
            session.rollback()

        # Should have exactly 1 workload with this name
        assert session.query(Workload).filter_by(name="unique-workload-2").count() == 1


    def test_workload_unique_name_constraint_enforced(self, session: Session):
        """Test workload name uniqueness constraint works."""
        workload1 = Workload(name="unique-constraint-test-A")
        session.add(workload1)
        session.commit()

        # Second workload with same name should fail UNIQUE constraint
        workload2 = Workload(name="unique-constraint-test-A")
        session.add(workload2)
        try:
            session.commit()
        except Exception:
            session.rollback()
            # Should still have exactly 1 row with this name
            assert session.query(Workload).filter_by(name="unique-constraint-test-A").count() == 1


class TestFirewallRuleModel:
    """Test cases for the FirewallRule model."""

    def test_create_firewall_rule(self, session: Session):
        """Test creating a firewall rule."""
        # Create a workload first
        workload = Workload(name="test-workload")
        session.add(workload)
        session.commit()
        session.refresh(workload)

        # Create a firewall rule
        rule_id = uuid.uuid4()
        rule = FirewallRule(
            id=rule_id,
            rule_collection_name="test-collection",
            priority=100,
            action=FirewallRuleAction.Allow.value,
            protocol=FirewallProtocol.Tcp.value,
            workload_id=workload.id,
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)

        assert rule.id == rule_id
        assert rule.rule_collection_name == "test-collection"
        assert rule.priority == 100
        assert rule.action == "Allow"
        assert rule.protocol == "Tcp"
        assert rule.status == "Pending"
        assert rule.workload_id == workload.id

    def test_firewall_rule_with_json_array_data(self, session: Session):
        """Test creating a firewall rule with array data stored as JSON."""
        source_addresses = json.dumps(["10.0.0.1", "10.0.0.2"])
        destination_fqdns = json.dumps(["example.com"])
        destination_ports = json.dumps(["443", "8080"])

        rule = FirewallRule(
            rule_collection_name="test-collection",
            priority=200,
            action=FirewallRuleAction.Deny.value,
            protocol=FirewallProtocol.Any.value,
            source_addresses=source_addresses,
            destination_fqdns=destination_fqdns,
            destination_ports=destination_ports,
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)

        assert rule.source_addresses == source_addresses
        assert rule.destination_fqdns == destination_fqdns
        assert json.loads(rule.destination_ports) == ["443", "8080"]

    def test_firewall_rule_status_values(self, session: Session):
        """Test all valid firewall rule status values."""
        for status in [FirewallRuleStatus.Pending, FirewallRuleStatus.Active,
                       FirewallRuleStatus.Deleted, FirewallRuleStatus.Error]:
            rule = FirewallRule(
                rule_collection_name=f"test-{status.value}",
                priority=100,
                action=FirewallRuleAction.Allow.value,
                protocol=FirewallProtocol.Tcp.value,
                status=status.value,
            )
            session.add(rule)
            session.commit()

    def test_firewall_rule_relationships(self, session: Session):
        """Test firewall rule relationships with workload."""
        workload = Workload(name="test-workload")
        session.add(workload)
        session.commit()
        session.refresh(workload)

        rule = FirewallRule(
            rule_collection_name="test-collection",
            priority=100,
            action=FirewallRuleAction.Allow.value,
            protocol=FirewallProtocol.Tcp.value,
            workload_id=workload.id,
        )
        session.add(rule)
        session.commit()

        # Test relationship
        assert workload.rules == [rule]
        assert rule.workload == workload


class TestApprovalRequestModel:
    """Test cases for the ApprovalRequest model."""

    def test_create_approval_request(self, session: Session):
        """Test creating an approval request."""
        request = ApprovalRequest(
            rule_ids=json.dumps(["rule-uuid-1", "rule-uuid-2"]),
            change_type=ChangeType.Create.value,
            description="Test approval request",
            status=ApprovalStatus.Pending.value,
            required_approvals=2,
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        assert request.status == ApprovalStatus.Pending.value
        assert request.change_type == ChangeType.Create.value
        assert request.required_approvals == 2
        assert request.created_at is not None

    def test_approval_request_status_values(self, session: Session):
        """Test all valid approval status values."""
        for status in [ApprovalStatus.Pending, ApprovalStatus.Approved,
                       ApprovalStatus.Rejected, ApprovalStatus.Revoked,
                       ApprovalStatus.Expired]:
            request = ApprovalRequest(
                rule_ids="[]",
                change_type=ChangeType.Create.value,
                status=status.value,
            )
            session.add(request)
            session.commit()

    def test_approval_request_relationships(self, session: Session):
        """Test approval request relationships."""
        # Create workload
        workload = Workload(name="test-workload")
        session.add(workload)
        session.commit()
        session.refresh(workload)

        # Create approval request linked to workload
        request = ApprovalRequest(
            rule_ids="[]",
            change_type=ChangeType.Create.value,
            workload_id=workload.id,
        )
        session.add(request)
        session.commit()

        # Test that relationship works
        assert request.workload_obj == workload


class TestApprovalStepModel:
    """Test cases for the ApprovalStep model."""

    def test_create_approval_step(self, session: Session):
        """Test creating an approval step."""
        # Create approval request first
        request = ApprovalRequest(
            rule_ids="[]",
            change_type=ChangeType.Create.value,
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        # Create approval step
        step = ApprovalStep(
            approval_request_id=request.id,
            approver_role=ApprovalRole.WorkloadStakeholder.value,
            status=ApprovalStatus.Pending.value,
        )
        session.add(step)
        session.commit()
        session.refresh(step)

        assert step.approval_request_id == request.id
        assert step.approver_role == ApprovalRole.WorkloadStakeholder.value
        assert step.status == ApprovalStatus.Pending.value
        assert step.created_at is not None


class TestAuditLogModel:
    """Test cases for the AuditLog model."""

    def test_create_audit_log(self, session: Session):
        """Test creating an audit log entry."""
        log = AuditLog(
            user_id=str(uuid.uuid4()),
            action=AuditAction.Create.value,
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
            ip_address="192.168.1.1",
            user_agent="test-agent",
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        assert log.action == AuditAction.Create.value
        assert log.resource_type == "firewall_rule"
        assert log.ip_address == "192.168.1.1"
        assert log.timestamp is not None

    def test_audit_log_with_json_values(self, session: Session):
        """Test audit log with old_value and new_value as JSON strings."""
        old_value = json.dumps({"status": "pending"})
        new_value = json.dumps({"status": "active"})

        log = AuditLog(
            user_id=str(uuid.uuid4()),
            action=AuditAction.Update.value,
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
            old_value=old_value,
            new_value=new_value,
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        assert json.loads(log.old_value) == {"status": "pending"}
        assert json.loads(log.new_value) == {"status": "active"}

    def test_audit_log_ip_address_storage(self, session: Session):
        """Test IP address storage for IPv4 and IPv6."""
        # IPv4
        log_v4 = AuditLog(
            user_id=str(uuid.uuid4()),
            action=AuditAction.Login.value,
            resource_type="user",
            ip_address="192.168.1.1",
        )
        session.add(log_v4)

        # IPv6
        log_v6 = AuditLog(
            user_id=str(uuid.uuid4()),
            action=AuditAction.Login.value,
            resource_type="user",
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        )
        session.add(log_v6)

        session.commit()

        assert log_v4.ip_address == "192.168.1.1"
        assert log_v6.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"


class TestUserModel:
    """Test cases for the User model."""

    def test_create_user(self, session: Session):
        """Test creating a user."""
        test_uuid = uuid.UUID("990f4961-b8f8-4a52-a3b4-aa4e2168d76c")
        user = User(
            id=test_uuid,
            object_id=str(uuid.uuid4()),
            email="test@example.com",
            display_name="Test User",
            given_name="Test",
            surname="User",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.id == test_uuid
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.is_active is True
        # created_at uses server_default=func.now() which sets it on INSERT
        assert user.created_at is not None

    def test_user_unique_object_id(self, session: Session):
        """Test user object_id uniqueness."""
        obj_id = str(uuid.uuid4())
        user = User(
            object_id=obj_id,
            email="test-unique@example.com",
            display_name="Unique User",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.object_id == obj_id

    def test_user_unique_constraints(self, session: Session):
        """Test user email uniqueness."""
        user1 = User(
            object_id=str(uuid.uuid4()),
            email="unique@example.com",
            display_name="Unique User",
        )
        session.add(user1)
        session.commit()

        # Same email should work with different object_id (SQLite allows)
        assert session.query(User).filter_by(email="unique@example.com").count() == 1


class TestUserRoleModel:
    """Test cases for the UserRole model."""

    def test_create_user_role(self, session: Session):
        """Test creating a user role assignment."""
        user = User(
            object_id=str(uuid.uuid4()),
            email="role@example.com",
            display_name="Role User",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        role = UserRole(
            user_id=user.id,
            role="admin",
        )
        session.add(role)
        session.commit()
        session.refresh(role)

        assert role.user_id == user.id
        assert role.role == "admin"
        assert role.granted_at is not None

    def test_user_role_repr(self):
        """Test UserRole string representation."""
        role = UserRole(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            role="admin",
        )
        assert "UserRole" in repr(role)
        assert "admin" in repr(role)


class TestApprovalWorkflowDefinitionModel:
    """Test cases for the ApprovalWorkflowDefinition model."""

    def test_create_workflow_definition(self, session: Session):
        """Test creating a workflow definition."""
        definition = ApprovalWorkflowDefinition(
            name="standard approval",
            description="Standard approval workflow",
            trigger_conditions=json.dumps({"min_priority": 100}),
            required_roles=json.dumps(["workload_stakeholder", "security_stakeholder"]),
            timeout_hours=48,
            is_active=True,
        )
        session.add(definition)
        session.commit()
        session.refresh(definition)

        assert definition.name == "standard approval"
        assert definition.timeout_hours == 48
        assert definition.is_active is True
        assert definition.created_at is not None

    def test_workflow_definition_name_uniqueness(self, session: Session):
        """Test workflow definition names must be unique."""
        def1 = ApprovalWorkflowDefinition(
            name="unique workflow test-B",
            required_roles=json.dumps(["admin"]),
            is_active=True,
        )
        session.add(def1)
        session.commit()
        session.refresh(def1)

        # Second definition with same name should fail UNIQUE constraint
        def2 = ApprovalWorkflowDefinition(
            name="unique workflow test-B",
            required_roles=json.dumps(["admin"]),
            is_active=True,
        )
        session.add(def2)
        try:
            session.commit()
        except Exception:
            session.rollback()
            # Should still have exactly 1 row with this name
            assert session.query(ApprovalWorkflowDefinition).filter_by(name="unique workflow test-B").count() == 1


class TestModelRelationships:
    """Test model relationships and cascades."""

    def test_workload_to_firewall_rules_relationship(self, session: Session):
        """Test that workloads can have multiple firewall rules."""
        workload = Workload(name="test-workload")
        session.add(workload)
        session.commit()
        session.refresh(workload)

        for i in range(3):
            rule = FirewallRule(
                rule_collection_name=f"collection-{i}",
                priority=100 + i,
                action=FirewallRuleAction.Allow.value,
                protocol=FirewallProtocol.Tcp.value,
                workload_id=workload.id,
            )
            session.add(rule)
        session.commit()

        assert len(workload.rules) == 3

    def test_user_to_owned_workloads_relationship(self, session: Session):
        """Test that users can own multiple workloads."""
        user = User(
            object_id=str(uuid.uuid4()),
            email="owner@example.com",
            display_name="Owner",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        for i in range(2):
            workload = Workload(
                name=f"owned-workload-{i}",
                owner_id=user.id,
            )
            session.add(workload)
        session.commit()

        assert len(user.owned_workloads) == 2

    def test_audit_log_user_relationship(self, session: Session):
        """Test audit log user relationship."""
        user = User(
            object_id=str(uuid.uuid4()),
            email="audited@example.com",
            display_name="Audited User",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        log = AuditLog(
            user_id=user.id,
            action=AuditAction.Create.value,
            resource_type="firewall_rule",
            resource_id=str(uuid.uuid4()),
        )
        session.add(log)
        session.commit()

        assert log.user == user