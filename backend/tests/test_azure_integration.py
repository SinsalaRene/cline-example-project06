"""
Comprehensive tests for Azure integration in firewall service.

Tests AzureClient, firewall rule validation, duplicate detection,
bulk operations, and synchronization with Azure Firewall.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
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
        AuditBase.metadata.drop_all(bind=engine)
        ApprovalBase.metadata.drop_all(bind=engine)
        FirewallBase.metadata.drop_all(bind=engine)


@pytest.fixture
def user_id():
    """Provide a test user UUID."""
    return uuid.uuid4()


@pytest.fixture
def azure_mock_client():
    """Provide a mock Azure client for testing."""
    with patch("app.integrations.azure_client.AzureClient") as mock:
        client = MagicMock()
        client.is_authenticated = True
        client.network_client = MagicMock()
        yield client


# =============================================================================
# AzureClient Tests
# =============================================================================

class TestAzureClient:
    """Test cases for AzureClient."""

    def test_client_initialization(self):
        """Test AzureClient initializes with correct parameters."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            subscription_id="test-sub",
            location="eastus",
        )

        assert client._tenant_id == "test-tenant"
        assert client._client_id == "test-client"
        assert client._client_secret == "test-secret"
        assert client._subscription_id == "test-sub"
        assert client._location == "eastus"
        assert client._is_authenticated is False

    def test_client_default_location(self):
        """Test AzureClient has default location."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        assert client._location == "eastus"

    def test_is_authenticated_property(self):
        """Test is_authenticated property."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        assert client.is_authenticated is False

    def test_client_error_classes(self):
        """Test custom exception classes."""
        from app.integrations.azure_client import (
            AzureClientError,
            AzureAuthenticationError,
            AzureResourceNotFoundError,
            AzureRuleValidationError,
            AzureRateLimitExceededError,
        )

        # Verify inheritance
        assert issubclass(AzureAuthenticationError, AzureClientError)
        assert issubclass(AzureResourceNotFoundError, AzureClientError)
        assert issubclass(AzureRuleValidationError, AzureClientError)
        assert issubclass(AzureRateLimitExceededError, AzureClientError)

        # Test instantiation
        err = AzureClientError("test error")
        assert str(err) == "test error"


class TestAzureClientRuleValidation:
    """Test Azure client rule validation."""

    def test_validate_rule_valid(self):
        """Test valid rule passes validation."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        valid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["10.0.0.1"],
            "destination_fqdns": ["example.com"],
            "destination_ports": [443],
        }

        is_valid, errors = client.validate_firewall_rule(valid_rule)
        assert is_valid is True
        assert errors == []

    def test_validate_rule_missing_collection_name(self):
        """Test rule validation fails without collection name."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_rule_invalid_priority(self):
        """Test rule validation fails with invalid priority."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 50,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Priority must be between" in e for e in errors)

    def test_validate_rule_invalid_action(self):
        """Test rule validation fails with invalid action."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "InvalidAction",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Action must be" in e for e in errors)

    def test_validate_rule_invalid_protocol(self):
        """Test rule validation fails with invalid protocol."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "InvalidProtocol",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Protocol must be" in e for e in errors)

    def test_validate_rule_invalid_fqdn(self):
        """Test rule validation fails with invalid FQDN."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "destination_fqdns": ["not a valid fqdn!"],
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Invalid FQDN" in e for e in errors)

    def test_validate_rule_invalid_ip(self):
        """Test rule validation fails with invalid IP address."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["not an ip address"],
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Invalid IP address" in e for e in errors)

    def test_validate_rule_invalid_port(self):
        """Test rule validation fails with invalid port."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "destination_ports": [99999],
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Port must be between" in e for e in errors)

    def test_validate_rule_collection_name_too_short(self):
        """Test rule validation fails with short collection name."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "ab",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("at least 3 characters" in e for e in errors)

    def test_validate_rule_collection_name_too_long(self):
        """Test rule validation fails with long collection name."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "a" * 81,
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("not exceed 80 characters" in e for e in errors)

    def test_validate_rule_priority_too_low(self):
        """Test rule validation fails with priority below minimum."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 50,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Priority must be between" in e for e in errors)

    def test_validate_rule_priority_too_high(self):
        """Test rule validation fails with priority above maximum."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 5000,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = client.validate_firewall_rule(invalid_rule)
        assert is_valid is False
        assert any("Priority must be between" in e for e in errors)

    def test_validate_rule_valid_cidr(self):
        """Test rule validation passes with valid CIDR notation."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        valid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["10.0.0.0/24"],
        }

        is_valid, errors = client.validate_firewall_rule(valid_rule)
        assert is_valid is True
        assert errors == []

    def test_validate_rule_valid_fqdn(self):
        """Test rule validation passes with valid FQDN."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        valid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "destination_fqdns": ["example.com", "test.example.org"],
        }

        is_valid, errors = client.validate_firewall_rule(valid_rule)
        assert is_valid is True
        assert errors == []


class TestAzureClientDuplicateDetection:
    """Test Azure client duplicate detection."""

    def test_check_duplicates_no_duplicates(self):
        """Test no duplicates detected when rules are unique."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        new_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "rule_name": "rule-1",
            }
        ]

        existing_rules = [
            {
                "rule_collection_name": "collection-2",
                "priority": 200,
                "rule_name": "rule-2",
            }
        ]

        duplicates = client.check_duplicate_rules(new_rules, existing_rules)
        assert len(duplicates) == 0

    def test_check_duplicates_priority_collision(self):
        """Test priority collision detected."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        new_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "rule_name": "rule-3",
            }
        ]

        existing_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "rule_name": "rule-1",
            }
        ]

        duplicates = client.check_duplicate_rules(new_rules, existing_rules)
        assert len(duplicates) == 1
        assert duplicates[0]["conflict_type"] == "priority_collision"

    def test_check_duplicates_name_collision(self):
        """Test name collision detected."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        new_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 200,
                "rule_name": "existing-rule",
            }
        ]

        existing_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "rule_name": "existing-rule",
            }
        ]

        duplicates = client.check_duplicate_rules(new_rules, existing_rules)
        assert len(duplicates) == 1
        assert duplicates[0]["conflict_type"] == "name_collision"

    def test_check_duplicates_multiple(self):
        """Test multiple duplicates detected."""
        from app.integrations.azure_client import AzureClient

        client = AzureClient(
            tenant_id="test",
            client_id="test",
            client_secret="test",
            subscription_id="test",
        )

        new_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "rule_name": "rule-1",
            },
            {
                "rule_collection_name": "collection-2",
                "priority": 200,
                "rule_name": "rule-2",
            },
        ]

        existing_rules = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "rule_name": "existing-rule",
            },
            {
                "rule_collection_name": "collection-2",
                "priority": 200,
                "rule_name": "existing-rule",
            },
        ]

        duplicates = client.check_duplicate_rules(new_rules, existing_rules)
        assert len(duplicates) == 2


# =============================================================================
# FirewallService Tests (Azure Integration)
# =============================================================================

class TestFirewallServiceAzureIntegration:
    """Test cases for FirewallService Azure integration."""

    def test_service_initialization(self):
        """Test FirewallService initializes correctly."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()
        assert service._logger is not None

    def test_validate_rule_valid(self, session, user_id):
        """Test rule validation passes for valid rule."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        valid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["10.0.0.1"],
            "destination_fqdns": ["example.com"],
        }

        is_valid, errors = service.validate_rule(valid_rule)
        assert is_valid is True
        assert errors == []

    def test_validate_rule_invalid_action(self, session, user_id):
        """Test rule validation fails for invalid action."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Invalid",
            "protocol": "Tcp",
        }

        is_valid, errors = service.validate_rule(invalid_rule)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_rule_invalid_priority(self, session, user_id):
        """Test rule validation fails for invalid priority."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 50,
            "action": "Allow",
            "protocol": "Tcp",
        }

        is_valid, errors = service.validate_rule(invalid_rule)
        assert is_valid is False
        assert any("Priority must be between" in e for e in errors)

    def test_validate_rule_invalid_protocol(self, session, user_id):
        """Test rule validation fails for invalid protocol."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Invalid",
        }

        is_valid, errors = service.validate_rule(invalid_rule)
        assert is_valid is False
        assert any("Protocol must be" in e for e in errors)

    def test_validate_rule_invalid_fqdn(self, session, user_id):
        """Test rule validation fails for invalid FQDN."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "destination_fqdns": ["not-valid-fqdn!"],
        }

        is_valid, errors = service.validate_rule(invalid_rule)
        assert is_valid is False
        assert any("Invalid FQDN" in e for e in errors)

    def test_validate_rule_invalid_ip(self, session, user_id):
        """Test rule validation fails for invalid IP."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["not-an-ip"],
        }

        is_valid, errors = service.validate_rule(invalid_rule)
        assert is_valid is False
        assert any("Invalid IP address" in e for e in errors)

    def test_validate_rule_invalid_port(self, session, user_id):
        """Test rule validation fails for invalid port."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        invalid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "destination_ports": [99999],
        }

        is_valid, errors = service.validate_rule(invalid_rule)
        assert is_valid is False
        assert any("Port must be between" in e for e in errors)

    def test_validate_rule_valid_cidr(self, session, user_id):
        """Test rule validation passes for valid CIDR."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        valid_rule = {
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Allow",
            "protocol": "Tcp",
            "source_addresses": ["192.168.1.0/24"],
        }

        is_valid, errors = service.validate_rule(valid_rule)
        assert is_valid is True
        assert errors == []

    def test_check_duplicates_finds_duplicates(self, session, user_id):
        """Test duplicate detection finds duplicates."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        # Create an existing rule
        existing_rule = FirewallRule(
            rule_collection_name="test-collection",
            priority=100,
            action="Allow",
            protocol="Tcp",
            created_by=user_id,
            status=FirewallRuleStatus.Pending.value,
        )
        session.add(existing_rule)
        session.commit()

        # Check for duplicates
        new_rules = [{
            "rule_collection_name": "test-collection",
            "priority": 100,
            "action": "Deny",
            "protocol": "Tcp",
        }]

        duplicates = service.check_duplicates(session, new_rules, user_id)
        assert len(duplicates) == 1
        assert duplicates[0]["conflict_type"] == "priority_collision"

    def test_check_duplicates_no_duplicates(self, session, user_id):
        """Test no duplicates when rules are unique."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        # Create an existing rule with different priority
        existing_rule = FirewallRule(
            rule_collection_name="test-collection",
            priority=100,
            action="Allow",
            protocol="Tcp",
            created_by=user_id,
            status=FirewallRuleStatus.Pending.value,
        )
        session.add(existing_rule)
        session.commit()

        # Check with unique rule
        new_rules = [{
            "rule_collection_name": "test-collection",
            "priority": 200,
            "action": "Deny",
            "protocol": "Tcp",
        }]

        duplicates = service.check_duplicates(session, new_rules, user_id)
        assert len(duplicates) == 0

    def test_create_firewall_rules_with_azure(self, session, user_id):
        """Test creating multiple rules with validation."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        rules_data = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
                "source_addresses": ["10.0.0.1"],
                "destination_fqdns": ["example.com"],
            },
            {
                "rule_collection_name": "collection-2",
                "priority": 200,
                "action": "Deny",
                "protocol": "Udp",
            },
        ]

        results = service.create_firewall_rules_with_azure(
            db=session,
            user_id=user_id,
            rules_data=rules_data,
        )

        assert results["summary"]["total"] == 2
        assert results["summary"]["created"] == 2
        assert results["summary"]["failed"] == 0
        assert results["summary"]["duplicates"] == 0
        assert len(results["created"]) == 2

    def test_create_firewall_rules_with_azure_validation_failure(self, session, user_id):
        """Test creating rules fails validation correctly."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        rules_data = [
            {
                "rule_collection_name": "collection-1",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
            },
            {
                "rule_collection_name": "collection-2",
                "priority": 50,  # Invalid priority
                "action": "Allow",
                "protocol": "Tcp",
            },
        ]

        results = service.create_firewall_rules_with_azure(
            db=session,
            user_id=user_id,
            rules_data=rules_data,
        )

        assert results["summary"]["total"] == 2
        assert results["summary"]["created"] == 1
        assert results["summary"]["failed"] == 1

    def test_create_firewall_rules_with_azure_duplicates(self, session, user_id):
        """Test duplicate detection in bulk creation."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        # Create an existing rule
        existing_rule = FirewallRule(
            rule_collection_name="existing-collection",
            priority=100,
            action="Allow",
            protocol="Tcp",
            created_by=user_id,
            status=FirewallRuleStatus.Pending.value,
        )
        session.add(existing_rule)
        session.commit()

        # Try to create rule with same collection/priority
        rules_data = [
            {
                "rule_collection_name": "existing-collection",
                "priority": 100,
                "action": "Deny",
                "protocol": "Tcp",
            },
            {
                "rule_collection_name": "new-collection",
                "priority": 200,
                "action": "Allow",
                "protocol": "Tcp",
            },
        ]

        results = service.create_firewall_rules_with_azure(
            db=session,
            user_id=user_id,
            rules_data=rules_data,
        )

        assert results["summary"]["total"] == 2
        assert results["summary"]["duplicates"] == 1
        assert results["summary"]["created"] == 1

    def test_bulk_delete_firewall_rules(self, session, user_id):
        """Test bulk delete of firewall rules."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        # Create multiple rules
        rule_ids = []
        for i in range(3):
            rule = FirewallRule(
                rule_collection_name=f"collection-{i}",
                priority=100 + i,
                action="Allow",
                protocol="Tcp",
                created_by=user_id,
                status=FirewallRuleStatus.Pending.value,
            )
            session.add(rule)
            rule_ids.append(rule.id)
        session.commit()

        # Delete all rules
        results = service.bulk_delete_firewall_rules(
            db=session,
            rule_ids=rule_ids,
            user_id=user_id,
        )

        assert results["summary"]["total"] == 3
        assert results["summary"]["deleted"] == 3
        assert results["summary"]["failed"] == 0
        assert len(results["deleted"]) == 3

    def test_bulk_update_firewall_rules(self, session, user_id):
        """Test bulk update of firewall rules."""
        from app.services.firewall_service import FirewallService
        from app.models.firewall_rule import FirewallRule, FirewallRuleStatus

        service = FirewallService()

        # Create rules
        rule_ids = []
        for i in range(3):
            rule = FirewallRule(
                rule_collection_name=f"collection-{i}",
                priority=100 + i,
                action="Allow",
                protocol="Tcp",
                created_by=user_id,
                status=FirewallRuleStatus.Pending.value,
            )
            session.add(rule)
            rule_ids.append(rule.id)
        session.commit()

        # Update all rules
        results = service.bulk_update_firewall_rules(
            db=session,
            rule_ids=rule_ids,
            updates={"action": "Deny", "status": "Active"},
            user_id=user_id,
        )

        assert results["summary"]["total"] == 3
        assert results["summary"]["updated"] == 3
        assert results["summary"]["failed"] == 0


class TestWorkloadService:
    """Test cases for WorkloadService."""

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
# Integration Tests
# =============================================================================

class TestAzureServiceIntegration:
    """Integration tests for Azure service interactions."""

    def test_firewall_service_import_from_azure(self, session):
        """Test importing rules from Azure format."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        azure_rules_data = [
            {
                "rule_collection_name": "azure-collection-1",
                "priority": 100,
                "action": "Allow",
                "protocol": "Tcp",
                "source_addresses": json.dumps(["10.0.0.1"]),
                "destination_fqdns": json.dumps(["example.com"]),
                "azure_resource_id": "/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/firewallPolicies/test-collection",
            },
        ]

        imported = service.import_firewall_rules_from_azure(session, azure_rules_data)
        assert len(imported) == 1
        assert imported[0].rule_collection_name == "azure-collection-1"

    def test_firewall_service_import_mixed(self, session):
        """Test importing mixed valid/invalid Azure rules."""
        from app.services.firewall_service import FirewallService

        service = FirewallService()

        azure_rules_data = [
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

        imported = service.import_firewall_rules_from_azure(session, azure_rules_data)
        assert len(imported) == 2