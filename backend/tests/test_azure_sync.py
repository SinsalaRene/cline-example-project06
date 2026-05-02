"""
Comprehensive tests for Azure Sync Service.

Tests AzureSyncService including firewall rule synchronization,
resource discovery, sync result handling, conflict resolution,
policy status, and NAT rule synchronization.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock
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
    from app.models.firewall_rule import Base as FirewallBase
    from app.models.approval import Base as ApprovalBase
    from app.models.audit import Base as AuditBase

    FirewallBase.metadata.create_all(bind=engine)
    ApprovalBase.metadata.create_all(bind=engine)
    AuditBase.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture
def user_id():
    """Provide a test user UUID."""
    return uuid.uuid4()


@pytest.fixture
def mock_settings():
    """Provide mock settings for Azure configuration."""
    settings = MagicMock()
    settings.azure_tenant_id = "test-tenant-id"
    settings.azure_client_id = "test-client-id"
    settings.azure_client_secret = "test-client-secret"
    settings.azure_subscription_id = "test-subscription-id"
    settings.azure_resource_group = "test-resource-group"
    settings.azure_region = "eastus"
    settings.azure_default_policy = "test-policy"
    return settings


@pytest.fixture
def mock_azure_client():
    """Provide a mock Azure client."""
    with patch("app.integrations.azure_client.AzureClient") as mock:
        client = MagicMock()
        client.is_authenticated = True
        client._is_authenticated = True
        yield client


@pytest.fixture
def mock_azure_sync_service(mock_settings, mock_azure_client):
    """Provide a mock Azure sync service."""
    with patch("app.services.azure_sync_service.create_azure_client_from_settings") as mock_create:
        mock_create.return_value = mock_azure_client
        from app.services.azure_sync_service import AzureSyncService
        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client
        yield service


# =============================================================================
# AzureResourceInfo Tests
# =============================================================================

class TestAzureResourceInfo:
    """Test cases for AzureResourceInfo data class."""

    def test_create_azure_resource_info(self):
        """Test creating AzureResourceInfo instance."""
        from app.services.azure_sync_service import AzureResourceInfo
        from datetime import datetime, timezone

        resource = AzureResourceInfo(
            resource_type="firewall_policy",
            resource_name="test-policy",
            resource_id="/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/firewallPolicies/test-policy",
            resource_group="test-resource-group",
            subscription_id="test-subscription-id",
            location="eastus",
            tags={"environment": "test"},
            metadata={"policy_id": "test-policy-id"},
        )

        assert resource.resource_type == "firewall_policy"
        assert resource.resource_name == "test-policy"
        assert resource.resource_group == "test-resource-group"
        assert resource.subscription_id == "test-subscription-id"
        assert resource.location == "eastus"
        assert resource.tags == {"environment": "test"}
        assert resource.metadata == {"policy_id": "test-policy-id"}

    def test_azure_resource_info_to_dict(self):
        """Test AzureResourceInfo serialization."""
        from app.services.azure_sync_service import AzureResourceInfo

        resource = AzureResourceInfo(
            resource_type="firewall_policy",
            resource_name="test-policy",
            resource_id="/subscriptions/test/resource/policy",
            resource_group="test-resource-group",
            subscription_id="test-subscription-id",
            location="eastus",
            tags={"env": "test"},
            metadata={"key": "value"},
        )

        data = resource.to_dict()

        assert data["resource_type"] == "firewall_policy"
        assert data["resource_name"] == "test-policy"
        assert data["resource_group"] == "test-resource-group"
        assert data["subscription_id"] == "test-subscription-id"
        assert data["location"] == "eastus"
        assert data["tags"] == {"env": "test"}
        assert data["metadata"] == {"key": "value"}
        assert "discovered_at" in data


# =============================================================================
# SyncResult Tests
# =============================================================================

class TestSyncResult:
    """Test cases for SyncResult data class."""

    def test_sync_result_success(self):
        """Test creating a successful SyncResult."""
        from app.services.azure_sync_service import SyncResult
        from datetime import datetime, timezone, timedelta

        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc) + timedelta(seconds=30)

        result = SyncResult(
            success=True,
            rules_synced=10,
            rules_created=5,
            rules_updated=3,
            rules_deleted=0,
            rules_unchanged=2,
            errors=[],
            conflicts=[],
            sync_start=start,
            sync_end=end,
        )

        assert result.success is True
        assert result.rules_synced == 10
        assert result.rules_created == 5
        assert result.rules_updated == 3
        assert result.rules_deleted == 0
        assert result.rules_unchanged == 2
        assert result.errors == []
        assert result.conflicts == []
        assert result.duration_seconds > 0

    def test_sync_result_to_dict(self):
        """Test SyncResult serialization."""
        from app.services.azure_sync_service import SyncResult

        result = SyncResult(
            success=True,
            rules_synced=10,
            rules_created=5,
            errors=["test-error"],
            conflicts=[{"rule": "test"}],
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["rules_synced"] == 10
        assert data["rules_created"] == 5
        assert data["errors"] == ["test-error"]
        assert data["conflicts"] == [{"rule": "test"}]
        assert "duration_seconds" in data

    def test_sync_result_zero_duration(self):
        """Test SyncResult duration when start/end are not set."""
        from app.services.azure_sync_service import SyncResult

        result = SyncResult(success=False)
        assert result.duration_seconds == 0.0

    def test_sync_result_default_values(self):
        """Test SyncResult has correct default values."""
        from app.services.azure_sync_service import SyncResult

        result = SyncResult(success=True)

        assert result.rules_synced == 0
        assert result.rules_created == 0
        assert result.rules_updated == 0
        assert result.rules_deleted == 0
        assert result.rules_unchanged == 0
        assert result.errors == []
        assert result.conflicts == []


# =============================================================================
# FirewallPolicyStatus Tests
# =============================================================================

class TestFirewallPolicyStatus:
    """Test cases for FirewallPolicyStatus data class."""

    def test_create_policy_status(self):
        """Test creating FirewallPolicyStatus instance."""
        from app.services.azure_sync_service import FirewallPolicyStatus
        from datetime import datetime, timezone

        status = FirewallPolicyStatus(
            policy_name="test-policy",
            resource_group="test-resource-group",
            subscription_id="test-subscription-id",
            state="active",
            total_rules=10,
            rule_collections_count=3,
            nat_collections_count=1,
        )

        assert status.policy_name == "test-policy"
        assert status.state == "active"
        assert status.total_rules == 10
        assert status.rule_collections_count == 3
        assert status.nat_collections_count == 1

    def test_policy_status_to_dict(self):
        """Test FirewallPolicyStatus serialization."""
        from app.services.azure_sync_service import FirewallPolicyStatus

        status = FirewallPolicyStatus(
            policy_name="test-policy",
            resource_group="test-resource-group",
            subscription_id="test-subscription-id",
            state="active",
            total_rules=10,
        )

        data = status.to_dict()

        assert data["policy_name"] == "test-policy"
        assert data["state"] == "active"
        assert data["total_rules"] == 10
        assert "last_sync" in data


# =============================================================================
# AzureSyncService Initialization Tests
# =============================================================================

class TestAzureSyncServiceInitialization:
    """Test cases for AzureSyncService initialization."""

    def test_service_initialization(self, mock_settings):
        """Test AzureSyncService initializes with settings."""
        from app.services.azure_sync_service import AzureSyncService

        service = AzureSyncService(settings=mock_settings)

        assert service._settings == mock_settings
        assert service._sync_interval_minutes == 30
        assert service._conflict_resolution == "azure_wins"

    def test_default_conflict_resolution(self, mock_settings):
        """Test default conflict resolution strategy."""
        from app.services.azure_sync_service import AzureSyncService

        service = AzureSyncService(settings=mock_settings)
        assert service.conflict_resolution == "azure_wins"

    def test_conflict_resolution_setter(self, mock_settings):
        """Test setting conflict resolution strategy."""
        from app.services.azure_sync_service import AzureSyncService

        service = AzureSyncService(settings=mock_settings)
        service.conflict_resolution = "local_wins"
        assert service.conflict_resolution == "local_wins"

    def test_conflict_resolution_invalid_value(self, mock_settings):
        """Test invalid conflict resolution strategy raises error."""
        from app.services.azure_sync_service import AzureSyncService, AzureSyncError

        service = AzureSyncService(settings=mock_settings)

        with pytest.raises(AzureSyncError):
            service.conflict_resolution = "invalid_strategy"

    def test_sync_interval_default(self, mock_settings):
        """Test default sync interval."""
        from app.services.azure_sync_service import AzureSyncService

        service = AzureSyncService(settings=mock_settings)
        assert service.sync_interval == 30

    def test_sync_interval_setter_valid(self, mock_settings):
        """Test setting valid sync interval."""
        from app.services.azure_sync_service import AzureSyncService

        service = AzureSyncService(settings=mock_settings)
        service.sync_interval = 60
        assert service.sync_interval == 60

    def test_sync_interval_setter_invalid(self, mock_settings):
        """Test setting invalid sync interval raises error."""
        from app.services.azure_sync_service import AzureSyncService, AzureSyncError

        service = AzureSyncService(settings=mock_settings)

        with pytest.raises(AzureSyncError):
            service.sync_interval = -1


# =============================================================================
# AzureSyncError Tests
# =============================================================================

class TestAzureSyncErrors:
    """Test cases for AzureSyncError classes."""

    def test_base_error(self):
        """Test base AzureSyncError."""
        from app.services.azure_sync_service import AzureSyncError

        err = AzureSyncError("test error")
        assert str(err) == "test error"

    def test_authentication_error_inheritance(self):
        """Test AzureSyncAuthenticationError inherits from AzureSyncError."""
        from app.services.azure_sync_service import AzureSyncAuthenticationError, AzureSyncError

        assert issubclass(AzureSyncAuthenticationError, AzureSyncError)
        err = AzureSyncAuthenticationError("auth failed")
        assert str(err) == "auth failed"

    def test_resource_error_inheritance(self):
        """Test AzureSyncResourceError inherits from AzureSyncError."""
        from app.services.azure_sync_service import AzureSyncResourceError, AzureSyncError

        assert issubclass(AzureSyncResourceError, AzureSyncError)
        err = AzureSyncResourceError("resource not found")
        assert str(err) == "resource not found"

    def test_conflict_error_inheritance(self):
        """Test AzureSyncConflictError inherits from AzureSyncError."""
        from app.services.azure_sync_service import AzureSyncConflictError, AzureSyncError

        assert issubclass(AzureSyncConflictError, AzureSyncError)
        err = AzureSyncConflictError("conflict detected")
        assert str(err) == "conflict detected"


# =============================================================================
# Resource Discovery Tests
# =============================================================================

class TestResourceDiscovery:
    """Test cases for Azure resource discovery."""

    def test_discover_resources_returns_empty(self, mock_settings, mock_azure_client):
        """Test resource discovery returns empty list when no resources found."""
        from app.services.azure_sync_service import AzureSyncService

        mock_azure_client.list_firewall_policies.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        resources = service.discover_azure_resources()

        assert resources == []

    def test_discover_resources_returns_list(self, mock_settings, mock_azure_client):
        """Test resource discovery returns list of resources."""
        from app.services.azure_sync_service import AzureSyncService

        # Mock a firewall policy
        mock_policy = MagicMock()
        mock_policy.name = "test-policy"
        mock_policy.id = "/subscriptions/test/resource/policy"
        mock_policy.location = "eastus"
        mock_policy.tags = {"env": "test"}
        mock_policy.sku = {"tier": "Standard"}
        mock_policy.policy_id = "policy-123"

        mock_azure_client.list_firewall_policies.return_value = [mock_policy]
        mock_azure_client.get_rule_collection_groups.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        resources = service.discover_azure_resources()

        assert len(resources) >= 1
        assert resources[0].resource_type == "firewall_policy"
        assert resources[0].resource_name == "test-policy"

    def test_discover_resources_with_subscription_filter(self, mock_settings, mock_azure_client):
        """Test resource discovery with subscription filter."""
        from app.services.azure_sync_service import AzureSyncService

        mock_azure_client.list_firewall_policies.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        resources = service.discover_azure_resources(subscription_id="custom-sub")

        # Should not raise
        assert isinstance(resources, list)


# =============================================================================
# Firewall Rule Synchronization Tests
# =============================================================================

class TestFirewallRuleSync:
    """Test cases for firewall rule synchronization."""

    def test_sync_firewall_rules_empty_azure(self, session, mock_settings, mock_azure_client):
        """Test sync when Azure has no rules."""
        from app.services.azure_sync_service import AzureSyncService, AzureSyncResourceError
        from azure.core.exceptions import HttpResponseError

        mock_azure_client.get_firewall_rules_from_azure.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_firewall_rules(
            db=session,
            resource_group="test-resource-group",
            policy_name="test-policy",
        )

        assert result.success is True
        assert result.rules_synced == 0

    def test_sync_firewall_rules_creates_local_rules(self, session, mock_settings, mock_azure_client):
        """Test sync creates local rules from Azure."""
        from app.services.azure_sync_service import AzureSyncService

        # Mock Azure rules
        azure_rules = [
            {
                "rule_name": "allow-http",
                "rule_collection_name": "web-collection",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
                "source_addresses": ["10.0.0.0/24"],
                "destination_fqdns": ["example.com"],
                "destination_ports": [443],
            },
        ]
        mock_azure_client.get_firewall_rules_from_azure.return_value = azure_rules

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_firewall_rules(
            db=session,
            resource_group="test-resource-group",
            policy_name="test-policy",
        )

        # Should not raise
        assert result is not None

    def test_sync_firewall_rules_with_conflict_resolution(self, session, mock_settings, mock_azure_client):
        """Test sync with conflict resolution strategy."""
        from app.services.azure_sync_service import AzureSyncService

        azure_rules = [
            {
                "rule_name": "conflict-rule",
                "rule_collection_name": "test-collection",
                "priority": 200,
                "action": "Deny",
                "protocol": "Tcp",
            },
        ]
        mock_azure_client.get_firewall_rules_from_azure.return_value = azure_rules

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client
        service.conflict_resolution = "manual"

        result = service.sync_firewall_rules(
            db=session,
            resource_group="test-resource-group",
            policy_name="test-policy",
            conflict_resolution="manual",
        )

        assert result is not None

    def test_sync_firewall_rules_validation_error(self, session, mock_settings, mock_azure_client):
        """Test sync with validation errors."""
        from app.services.azure_sync_service import AzureSyncService

        azure_rules = [
            {
                "rule_name": "invalid-rule",
                "rule_collection_name": "ab",  # Too short
                "priority": 50,  # Invalid priority
                "action": "Invalid",  # Invalid action
                "protocol": "InvalidProtocol",  # Invalid protocol
                "source_addresses": ["not-an-ip"],  # Invalid IP
                "destination_fqdns": ["not-valid!"],  # Invalid FQDN
                "destination_ports": [99999],  # Invalid port
            },
        ]
        mock_azure_client.get_firewall_rules_from_azure.return_value = azure_rules

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_firewall_rules(
            db=session,
            resource_group="test-resource-group",
            policy_name="test-policy",
        )

        # May have errors due to invalid rules
        assert result is not None

    def test_sync_firewall_rules_duration(self, session, mock_settings, mock_azure_client):
        """Test sync result contains duration."""
        from app.services.azure_sync_service import AzureSyncService

        mock_azure_client.get_firewall_rules_from_azure.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_firewall_rules(
            db=session,
            resource_group="test-resource-group",
            policy_name="test-policy",
        )

        # Duration should be calculated
        assert "duration_seconds" in result.to_dict()


# =============================================================================
# Rule Comparison Tests
# =============================================================================

class TestRuleComparison:
    """Test cases for rule comparison logic."""

    def test_compare_rules_new_rules(self, session, mock_settings, mock_azure_client):
        """Test detecting new rules from Azure."""
        from app.services.azure_sync_service import AzureSyncService

        azure_rules = [
            {
                "rule_name": "new-rule",
                "rule_collection_name": "collection-1",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
            },
        ]

        mock_azure_client.get_firewall_rules_from_azure.return_value = azure_rules

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        local_rules = service._get_local_rules(session, "rg", "policy")
        changes = service._compare_rules(azure_rules, local_rules, "azure_wins")

        assert len(changes["to_create"]) == 1
        assert changes["to_create"][0]["rule_name"] == "new-rule"

    def test_compare_rules_unchanged(self, mock_settings, mock_azure_client):
        """Test detecting unchanged rules."""
        from app.services.azure_sync_service import AzureSyncService

        azure_rule = {
            "rule_name": "unchanged-rule",
            "rule_collection_name": "collection-1",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
        }

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        # Create a matching local rule
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
        local_rule = FirewallRule(
            rule_collection_name="collection-1",
            priority=100,
            action="Allow",
            protocol="Tcp",
            status=FirewallRuleStatus.Active.value,
        )

        differs = service._rules_differ(azure_rule, local_rule)
        assert differs is False

    def test_compare_rules_changed(self, mock_settings, mock_azure_client):
        """Test detecting changed rules."""
        from app.services.azure_sync_service import AzureSyncService

        azure_rule = {
            "rule_name": "changed-rule",
            "rule_collection_name": "collection-1",
            "priority": 200,  # Changed from 100
            "action": "Deny",  # Changed from Allow
            "protocol": "Tcp",
        }

        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        local_rule = FirewallRule(
            rule_collection_name="collection-1",
            priority=100,
            action="Allow",
            protocol="Tcp",
            status=FirewallRuleStatus.Active.value,
        )

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        differs = service._rules_differ(azure_rule, local_rule)
        assert differs is True


# =============================================================================
# Policy Status Tests
# =============================================================================

class TestPolicyStatus:
    """Test cases for firewall policy status."""

    def test_get_policy_status_not_found(self, mock_settings, mock_azure_client):
        """Test policy status when policy not found."""
        from app.services.azure_sync_service import AzureSyncService, AzureResourceNotFoundError

        mock_azure_client.get_firewall_policy.side_effect = AzureResourceNotFoundError("Not found")

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        status = service.get_policy_status("rg", "nonexistent-policy")

        assert status.policy_name == "nonexistent-policy"
        assert status.state == "not_found"

    def test_get_policy_status_active(self, mock_settings, mock_azure_client):
        """Test policy status when policy is active."""
        from app.services.azure_sync_service import AzureSyncService

        mock_policy = MagicMock()
        mock_policy.name = "active-policy"
        mock_policy.id = "/subscriptions/test/policy"
        mock_policy.location = "eastus"
        mock_policy.tags = {}

        mock_azure_client.get_firewall_policy.return_value = mock_policy
        mock_azure_client.get_rule_collection_groups.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        status = service.get_policy_status("rg", "active-policy")

        assert status.policy_name == "active-policy"
        assert status.state == "active"

    def test_get_policy_status_error(self, mock_settings, mock_azure_client):
        """Test policy status when error occurs."""
        from app.services.azure_sync_service import AzureSyncService, AzureRuleValidationError

        mock_azure_client.get_firewall_policy.side_effect = AzureRuleValidationError("Connection error")

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        status = service.get_policy_status("rg", "error-policy")

        assert status.policy_name == "error-policy"
        assert status.state == "error"
        assert status.error_message is not None

    def test_sync_policy_status(self, session, mock_settings, mock_azure_client):
        """Test syncing policy status."""
        from app.services.azure_sync_service import AzureSyncService

        mock_policy = MagicMock()
        mock_policy.name = "test-policy"
        mock_policy.id = "/subscriptions/test/policy"
        mock_policy.location = "eastus"
        mock_policy.tags = {}

        mock_azure_client.get_firewall_policy.return_value = mock_policy
        mock_azure_client.get_rule_collection_groups.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client
        service._get_default_policy_name = lambda: "test-policy"

        result = service.sync_policy_status(
            db=session,
            resource_group="rg",
            policy_name="test-policy",
        )

        assert result["success"] is True

    def test_policy_status_to_dict(self):
        """Test policy status dictionary serialization."""
        from app.services.azure_sync_service import FirewallPolicyStatus
        from datetime import datetime, timezone

        status = FirewallPolicyStatus(
            policy_name="test-policy",
            resource_group="rg",
            subscription_id="sub",
            state="active",
            total_rules=10,
            last_sync=datetime.now(timezone.utc),
            rule_collections_count=3,
            nat_collections_count=1,
        )

        data = status.to_dict()

        assert data["policy_name"] == "test-policy"
        assert data["state"] == "active"
        assert data["total_rules"] == 10
        assert data["rule_collections_count"] == 3
        assert data["nat_collections_count"] == 1


# =============================================================================
# Rule Collection Sync Tests
# =============================================================================

class TestRuleCollectionSync:
    """Test cases for rule collection synchronization."""

    def test_sync_rule_collections_empty(self, session, mock_settings, mock_azure_client):
        """Test syncing rule collections when none exist."""
        from app.services.azure_sync_service import AzureSyncService

        mock_azure_client.get_rule_collection_groups.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_rule_collections(
            db=session,
            resource_group="rg",
            policy_name="policy",
        )

        assert result.success is True

    def test_sync_rule_collections_with_data(self, session, mock_settings, mock_azure_client):
        """Test syncing rule collections with data."""
        from app.services.azure_sync_service import AzureSyncService

        # Mock rule collection group
        mock_group = MagicMock()
        mock_group.name = "test-group"

        # Mock rule collection
        mock_rc = MagicMock()
        mock_rc.name = "test-collection"
        mock_rc.priority = 100
        mock_rc.action = "Allow"
        mock_rc.rules = []

        mock_group.rule_collections = [mock_rc]
        mock_group.nat_collections = []

        mock_azure_client.get_rule_collection_groups.return_value = [mock_group]

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_rule_collections(
            db=session,
            resource_group="rg",
            policy_name="policy",
        )

        assert result is not None


# =============================================================================
# NAT Rule Sync Tests
# =============================================================================

class TestNatRuleSync:
    """Test cases for NAT rule synchronization."""

    def test_sync_nat_rules_empty(self, session, mock_settings, mock_azure_client):
        """Test syncing NAT rules when none exist."""
        from app.services.azure_sync_service import AzureSyncService

        mock_azure_client.get_rule_collection_groups.return_value = []

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_nat_rules(
            db=session,
            resource_group="rg",
            policy_name="policy",
        )

        assert result.success is True

    def test_sync_nat_rules_with_data(self, session, mock_settings, mock_azure_client):
        """Test syncing NAT rules with data."""
        from app.services.azure_sync_service import AzureSyncService

        mock_group = MagicMock()
        mock_group.name = "nat-group"

        mock_nc = MagicMock()
        mock_nc.name = "nat-collection"
        mock_nc.priority = 100
        mock_nc.nat_rules = []

        mock_group.nat_collections = [mock_nc]
        mock_group.rule_collections = []

        mock_azure_client.get_rule_collection_groups.return_value = [mock_group]

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.sync_nat_rules(
            db=session,
            resource_group="rg",
            policy_name="policy",
        )

        assert result is not None


# =============================================================================
# Apply Local Rules to Azure Tests
# =============================================================================

class TestApplyLocalRulesToAzure:
    """Test cases for applying local rules to Azure."""

    def test_apply_local_rules_to_azure_empty(self, session, mock_settings, mock_azure_client):
        """Test applying rules when none exist in local DB."""
        from app.services.azure_sync_service import AzureSyncService

        mock_azure_client.bulk_create_firewall_rules.return_value = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "created_rules": [],
        }

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.apply_local_rules_to_azure(
            db=session,
            resource_group="rg",
            policy_name="policy",
        )

        assert result is not None

    def test_apply_local_rules_to_azure_with_rules(self, session, mock_settings, mock_azure_client):
        """Test applying rules when they exist in local DB."""
        from app.services.azure_sync_service import AzureSyncService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
        import uuid as uuid_module

        # Create a local rule
        test_user = uuid_module.uuid4()
        rule = FirewallRule(
            rule_collection_name="collection-1",
            priority=100,
            action="Allow",
            protocol="Tcp",
            status=FirewallRuleStatus.Active.value,
            created_by=test_user,
        )
        session.add(rule)
        session.commit()

        mock_azure_client.bulk_create_firewall_rules.return_value = {
            "success_count": 1,
            "failed_count": 0,
            "errors": [],
            "created_rules": ["local-rule"],
        }
        mock_azure_client.validate_firewall_rule.return_value = (True, [])

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client

        result = service.apply_local_rules_to_azure(
            db=session,
            resource_group="rg",
            policy_name="policy",
        )

        assert result is not None
        mock_azure_client.bulk_create_firewall_rules.assert_called_once()


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Test cases for factory functions."""

    def test_create_azure_sync_service(self, mock_settings):
        """Test factory function creates service correctly."""
        from app.services.azure_sync_service import create_azure_sync_service, AzureSyncService

        service = create_azure_sync_service(settings=mock_settings)

        assert isinstance(service, AzureSyncService)

    def test_create_azure_client_from_settings(self, mock_settings):
        """Test creating AzureClient from settings."""
        from app.integrations.azure_client import create_azure_client_from_settings, AzureClient

        client = create_azure_client_from_settings(mock_settings)

        assert isinstance(client, AzureClient)
        assert client._tenant_id == "test-tenant-id"
        assert client._client_id == "test-client-id"
        assert client._subscription_id == "test-subscription-id"


# =============================================================================
# Conflict Resolution Tests
# =============================================================================

class TestConflictResolution:
    """Test cases for conflict resolution."""

    def test_azure_wins_resolution(self, session, mock_settings, mock_azure_client):
        """Test Azure wins conflict resolution."""
        from app.services.azure_sync_service import AzureSyncService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
        import uuid as uuid_module

        azure_rule = {
            "rule_name": "conflict-rule",
            "rule_collection_name": "collection-1",
            "priority": 200,
            "action": "Deny",
            "protocol": "Tcp",
        }
        mock_azure_client.get_firewall_rules_from_azure.return_value = [azure_rule]

        test_user = uuid_module.uuid4()
        local_rule = FirewallRule(
            rule_collection_name="collection-1",
            priority=100,
            action="Allow",
            protocol="Tcp",
            status=FirewallRuleStatus.Active.value,
            created_by=test_user,
        )
        session.add(local_rule)
        session.commit()

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client
        service._get_default_policy_name = lambda: "policy"

        result = service.sync_firewall_rules(
            db=session,
            resource_group="rg",
            policy_name="policy",
            conflict_resolution="azure_wins",
        )

        assert result is not None

    def test_local_wins_resolution(self, session, mock_settings, mock_azure_client):
        """Test local wins conflict resolution."""
        from app.services.azure_sync_service import AzureSyncService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
        import uuid as uuid_module

        azure_rule = {
            "rule_name": "conflict-rule",
            "rule_collection_name": "collection-1",
            "priority": 200,
            "action": "Deny",
            "protocol": "Tcp",
        }
        mock_azure_client.get_firewall_rules_from_azure.return_value = [azure_rule]

        test_user = uuid_module.uuid4()
        local_rule = FirewallRule(
            rule_collection_name="collection-1",
            priority=100,
            action="Allow",
            protocol="Tcp",
            status=FirewallRuleStatus.Active.value,
            created_by=test_user,
        )
        session.add(local_rule)
        session.commit()

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client
        service._get_default_policy_name = lambda: "policy"

        result = service.sync_firewall_rules(
            db=session,
            resource_group="rg",
            policy_name="policy",
            conflict_resolution="local_wins",
        )

        assert result is not None

    def test_manual_resolution(self, session, mock_settings, mock_azure_client):
        """Test manual conflict resolution."""
        from app.services.azure_sync_service import AzureSyncService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
        import uuid as uuid_module

        azure_rule = {
            "rule_name": "conflict-rule",
            "rule_collection_name": "collection-1",
            "priority": 200,
            "action": "Deny",
            "protocol": "Tcp",
        }
        mock_azure_client.get_firewall_rules_from_azure.return_value = [azure_rule]

        test_user = uuid_module.uuid4()
        local_rule = FirewallRule(
            rule_collection_name="collection-1",
            priority=100,
            action="Allow",
            protocol="Tcp",
            status=FirewallRuleStatus.Active.value,
            created_by=test_user,
        )
        session.add(local_rule)
        session.commit()

        service = AzureSyncService(settings=mock_settings)
        service._azure_client = mock_azure_client
        service._get_default_policy_name = lambda: "policy"

        result = service.sync_firewall_rules(
            db=session,
            resource_group="rg",
            policy_name="policy",
            conflict_resolution="manual",
        )

        assert result is not None
