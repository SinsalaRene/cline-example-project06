"""
Pytest configuration for backend tests.

This module provides shared fixtures and hooks for all tests.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID
import tempfile
import os
import shutil

# ============================================================
# Rate limit cleanup
# ============================================================
@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Clear rate limit store before each test."""
    try:
        from app.auth.auth_service import _rate_limit_store
        _rate_limit_store.clear()
    except ImportError:
        pass


# ============================================================
# Database & Session Fixtures
# ============================================================
# Module-scoped: each test module gets one temp directory + engine
_module_db_dir = None
_module_engine = None


@pytest.fixture(scope="module", autouse=True)
def _module_db_setup():
    """Set up module-scoped test database directory and engine.

    Drops all tables first to handle repeated test runs on the same
    SQLite file (SQLite auto-commits DDL so CREATE INDEX can fail
    with "already exists" if tables were created by a previous run).
    """
    global _module_db_dir, _module_engine
    from sqlalchemy import create_engine
    from app.models import Base

    _module_db_dir = tempfile.mkdtemp(prefix="test_db_")
    db_path = os.path.join(_module_db_dir, "test.db")
    _module_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.drop_all(_module_engine)
    Base.metadata.create_all(_module_engine)
    yield
    # Teardown
    if _module_engine is not None:
        try:
            _module_engine.dispose()
        except Exception:
            pass
        _module_engine = None
    if _module_db_dir is not None:
        try:
            shutil.rmtree(_module_db_dir)
        except Exception:
            pass
        _module_db_dir = None


@pytest.fixture
def db_session(_module_db_setup):
    """Provide a transactional database session.

    Each test gets its own connection with an outer-level transaction.
    SQLite auto-commits DDL so we use SAVEPOINTs carefully - only for
    INSERT/UPDATE/DELETE, not for table-level operations.
    """
    from sqlalchemy.orm import sessionmaker

    conn = _module_engine.connect()
    txn = conn.begin()
    Session = sessionmaker()
    session = Session(bind=conn)

    yield session

    # Cleanup - just rollback the outer transaction
    try:
        session.close()
    except Exception:
        pass
    try:
        txn.rollback()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture
def client(db_session):
    """Provide a FastAPI test client."""
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app
    from app.database import SessionLocal, get_db
    from app.config import get_settings

    def override_get_db():
        yield db_session

    def override_get_settings():
        return Settings(_env_file=None)

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_settings] = override_get_settings
    yield TestClient(fastapi_app)
    # Clean up
    fastapi_app.dependency_overrides.clear()


# ============================================================
# Settings Fixtures
# ============================================================
@pytest.fixture
def settings():
    """Provide a Settings instance."""
    from app.config import Settings
    s = Settings(_env_file=None)
    return s


@pytest.fixture
def test_settings():
    """Provide test settings with SQLite."""
    from app.config import Settings
    s = Settings(_env_file=None)
    # Ensure we're using SQLite for tests
    s.database_type = "sqlite"
    s.database_url = "sqlite:///./test_backend.db"
    return s


# ============================================================
# User Fixtures
# ============================================================
@pytest.fixture
def user_obj(db_session):
    """Create a test user in the database."""
    from app.models.user import User
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.auth.auth_service import AuthService

    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password=AuthService._hash_password("testpassword"),
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_obj_no_admin(db_session):
    """Create a non-admin test user."""
    from app.models.user import User
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.auth.auth_service import AuthService

    user = User(
        id=uuid4(),
        username="regularuser",
        email="regular@example.com",
        hashed_password=AuthService._hash_password("testpassword"),
        first_name="Regular",
        last_name="User",
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================
# Workload Fixtures
# ============================================================
@pytest.fixture
def workload_obj(db_session, user_obj):
    """Create a test workload."""
    from app.models.firewall_rule import Workload
    from uuid import uuid4
    from datetime import datetime, timezone
    import json

    workload = Workload(
        id=uuid4(),
        name="test-workload",
        description="Test workload for unit tests",
        owner_id=user_obj.id,
        resource_groups=json.dumps(["rg-test"]),
        subscriptions=json.dumps(["sub-test"]),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(workload)
    db_session.commit()
    db_session.refresh(workload)
    return workload


# ============================================================
# FirewallRule Fixtures
# ============================================================
@pytest.fixture
def firewall_rule_obj(db_session, workload_obj):
    """Create a test firewall rule."""
    from app.models.firewall_rule import FirewallRule, FirewallRuleAction, FirewallProtocol, FirewallRuleStatus
    from uuid import uuid4
    from datetime import datetime, timezone
    import json

    rule = FirewallRule(
        id=uuid4(),
        rule_collection_name="test-collection",
        priority=100,
        action=FirewallRuleAction.Allow.value,
        protocol=FirewallProtocol.Any.value,
        source_addresses=json.dumps(["10.0.0.0/24"]),
        destination_fqdns=json.dumps(["example.com"]),
        source_ip_groups=json.dumps(["ipg-test"]),
        destination_ports=json.dumps([443]),
        description="Test firewall rule",
        status=FirewallRuleStatus.Active.value,
        workload_id=workload_obj.id,
        azure_resource_id="azure-resource-id-test",
        created_by=user_obj.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


@pytest.fixture
def firewall_rules_obj(db_session, workload_obj, user_obj):
    """Create multiple test firewall rules."""
    from app.models.firewall_rule import FirewallRule, FirewallRuleAction, FirewallProtocol, FirewallRuleStatus
    from uuid import uuid4
    from datetime import datetime, timezone
    import json

    rules = []
    for i in range(3):
        rule = FirewallRule(
            id=uuid4(),
            rule_collection_name=f"test-collection-{i}",
            priority=100 + i * 10,
            action=FirewallRuleAction.Allow.value,
            protocol=FirewallProtocol.Tcp.value,
            source_addresses=json.dumps([f"10.0.{i}.0/24"]),
            destination_fqdns=json.dumps([f"example{i}.com"]),
            source_ip_groups=None,
            destination_ports=json.dumps([443]),
            description=f"Test firewall rule {i}",
            status=FirewallRuleStatus.Active.value,
            workload_id=workload_obj.id,
            azure_resource_id=f"azure-resource-id-test-{i}",
            created_by=user_obj.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(rule)
        rules.append(rule)

    db_session.commit()
    # Refresh all rules
    for rule in rules:
        db_session.refresh(rule)
    return rules


# ============================================================
# Approval Fixtures
# ============================================================
@pytest.fixture
def approval_request_obj(db_session, firewall_rule_obj, user_obj):
    """Create a test approval request."""
    from app.models.approval import ApprovalRequest, ChangeType, ApprovalStatus
    from uuid import uuid4
    from datetime import datetime, timezone
    import json

    rule_id = firewall_rule_obj.id if hasattr(firewall_rule_obj, 'id') else firewall_rule_obj
    user_id = user_obj.id if hasattr(user_obj, 'id') else uuid4()

    approval = ApprovalRequest(
        id=uuid4(),
        rule_ids=json.dumps([str(rule_id)]),
        change_type=ChangeType.Create.value,
        description="Test approval request",
        current_user_id=user_id,
        status=ApprovalStatus.Pending.value,
        required_approvals=2,
        current_approval_stage=1,
        approval_flow="multi_level",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)
    return approval


@pytest.fixture
def approval_step_obj(db_session, approval_request_obj):
    """Create a test approval step."""
    from app.models.approval import ApprovalStep, ApprovalStatus, ApprovalRole
    from uuid import uuid4
    from datetime import datetime, timezone

    step = ApprovalStep(
        id=uuid4(),
        approval_request_id=approval_request_obj.id,
        approver_role=ApprovalRole.WorkloadStakeholder.value,
        status=ApprovalStatus.Pending.value,
        comments="Initial step",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(step)
    db_session.commit()
    db_session.refresh(step)
    return step


@pytest.fixture
def workflow_definition_obj(db_session):
    """Create a test workflow definition."""
    from app.models.approval import ApprovalWorkflowDefinition
    from uuid import uuid4
    from datetime import datetime, timezone
    import json

    definition = ApprovalWorkflowDefinition(
        id=uuid4(),
        name="Standard Approval Workflow",
        description="Standard approval workflow",
        trigger_conditions=json.dumps({"min_priority": 100}),
        required_roles=json.dumps(["workload_stakeholder", "security_stakeholder"]),
        timeout_hours=48,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(definition)
    db_session.commit()
    db_session.refresh(definition)
    return definition


# ============================================================
# Audit Log Fixtures
# ============================================================
@pytest.fixture
def audit_log_obj(db_session, user_obj):
    """Create a test audit log entry."""
    from app.models.audit import AuditLog, AuditAction, ResourceType
    from uuid import uuid4
    from datetime import datetime, timezone
    import json

    user_id = user_obj.id if hasattr(user_obj, 'id') else None

    log = AuditLog(
        id=uuid4(),
        user_id=user_id,
        action=AuditAction.Create.value,
        resource_type=ResourceType.FirewallRule.value,
        resource_id=str(uuid4()),
        details=json.dumps({"action": "create", "priority": 100}),
        ip_address="127.0.0.1",
        correlation_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


# ============================================================
# Mock Fixtures
# ============================================================
@pytest.fixture
def mock_azure_client():
    """Mock Azure client."""
    with patch('app.integrations.azure_client.AzureClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    with patch('app.services.notification_service.NotificationService') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance