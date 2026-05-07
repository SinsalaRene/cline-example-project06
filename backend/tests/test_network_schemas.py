"""
Tests for Network Pydantic Schemas.

Tests serialization and validation for all network-related Pydantic schemas
including VirtualNetwork, Subnet, NetworkSecurityGroup, NSGRule,
ExternalNetworkDevice, NetworkConnection, and TopologyGraph.
"""

import pytest
from pydantic import ValidationError


# ============================================================================
# VirtualNetworkSchema Tests
# ============================================================================

def test_virtual_network_create_schema():
    """VirtualNetworkCreate accepts valid data."""
    from app.schemas.network import VirtualNetworkCreate

    data = VirtualNetworkCreate(
        name="my-vnet",
        address_space="10.0.0.0/16",
        location="eastus2",
        resource_group="my-rg",
    )
    assert data.name == "my-vnet"
    assert data.address_space == "10.0.0.0/16"


def test_virtual_network_update_schema():
    """VirtualNetworkUpdate accepts partial data."""
    from app.schemas.network import VirtualNetworkUpdate

    data = VirtualNetworkUpdate(address_space="10.1.0.0/16")
    assert data.address_space == "10.1.0.0/16"


def test_virtual_network_create_invalid_cidr():
    """VirtualNetworkCreate rejects CIDR without slash."""
    from app.schemas.network import VirtualNetworkCreate

    with pytest.raises(ValidationError):
        VirtualNetworkCreate(
            name="bad-cidr",
            address_space="10.0.0.0",
            location="eastus2",
            resource_group="my-rg",
        )


# ============================================================================
# SubnetSchema Tests
# ============================================================================

def test_subnet_create_schema():
    """SubnetCreate accepts valid data."""
    from app.schemas.network import SubnetCreate
    from uuid import uuid4

    data = SubnetCreate(
        name="my-subnet",
        address_prefix="10.0.1.0/24",
        vnet_id=uuid4(),
    )
    assert data.name == "my-subnet"


def test_subnet_update_schema():
    """SubnetUpdate accepts partial data."""
    from app.schemas.network import SubnetUpdate

    data = SubnetUpdate(is_active=False)
    assert data.is_active is False


def test_subnet_create_invalid_cidr():
    """SubnetCreate rejects prefix without slash."""
    from app.schemas.network import SubnetCreate
    from uuid import uuid4

    with pytest.raises(ValidationError):
        SubnetCreate(
            name="bad-prefix",
            address_prefix="10.0.1.0",
            vnet_id=uuid4(),
        )


# ============================================================================
# NetworkSecurityGroupSchema Tests
# ============================================================================

def test_nsg_create_schema():
    """NSGCreate accepts valid data."""
    from app.schemas.network import NSGCreate
    from uuid import uuid4

    data = NSGCreate(
        name="my-nsg",
        location="eastus2",
        vnet_id=uuid4(),
        resource_group="my-rg",
    )
    assert data.name == "my-nsg"


def test_nsg_update_schema():
    """NSGUpdate accepts partial data."""
    from app.schemas.network import NSGUpdate

    data = NSGUpdate(location="westus2")
    assert data.location == "westus2"


# ============================================================================
# NSGRuleSchema Tests
# ============================================================================

def test_nsg_rule_create_schema():
    """NSGRuleCreate accepts valid data."""
    from app.schemas.network import NSGRuleCreate, Direction, Protocol, Access

    data = NSGRuleCreate(
        name="my-rule",
        priority=100,
        direction=Direction.INBOUND,
        protocol=Protocol.TCP,
        access=Access.ALLOW,
    )
    assert data.name == "my-rule"
    assert data.priority == 100


def test_nsg_rule_update_schema():
    """NSGRuleUpdate accepts partial data."""
    from app.schemas.network import NSGRuleUpdate

    data = NSGRuleUpdate(priority=200)
    assert data.priority == 200


def test_nsg_rule_priority_min_validation():
    """NSGRuleCreate rejects priority below 100."""
    from app.schemas.network import NSGRuleCreate, Direction, Protocol, Access

    with pytest.raises(ValidationError):
        NSGRuleCreate(
            name="low-priority-rule",
            priority=99,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
        )


def test_nsg_rule_priority_max_validation():
    """NSGRuleCreate rejects priority above 4096."""
    from app.schemas.network import NSGRuleCreate, Direction, Protocol, Access

    with pytest.raises(ValidationError):
        NSGRuleCreate(
            name="high-priority-rule",
            priority=4097,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
        )


# ============================================================================
# ExternalNetworkDeviceSchema Tests
# ============================================================================

def test_external_device_create_schema():
    """ExternalDeviceCreate accepts valid data."""
    from app.schemas.network import ExternalDeviceCreate, DeviceType

    data = ExternalDeviceCreate(
        name="my-router",
        ip_address="192.168.1.1",
        device_type=DeviceType.ROUTER,
        vendor="Cisco",
    )
    assert data.name == "my-router"
    assert data.device_type == DeviceType.ROUTER


def test_external_device_update_schema():
    """ExternalDeviceUpdate accepts partial data."""
    from app.schemas.network import ExternalDeviceUpdate

    data = ExternalDeviceUpdate(vendor="Juniper")
    assert data.vendor == "Juniper"


def test_external_device_invalid_email():
    """ExternalDeviceCreate rejects invalid email."""
    from app.schemas.network import ExternalDeviceCreate, DeviceType

    with pytest.raises(ValidationError):
        ExternalDeviceCreate(
            name="bad-email-device",
            device_type=DeviceType.ROUTER,
            contact_email="not-an-email",
        )


# ============================================================================
# NetworkConnectionSchema Tests
# ============================================================================

def test_connection_create_schema():
    """NetworkConnectionCreate accepts valid data."""
    from app.schemas.network import NetworkConnectionCreate, ConnectionType
    from uuid import uuid4

    data = NetworkConnectionCreate(
        source_id=uuid4(),
        source_type="subnet",
        destination_id=uuid4(),
        destination_type="external_device",
        connection_type=ConnectionType.DIRECT,
    )
    assert data.source_type == "subnet"


def test_connection_create_default_direct():
    """NetworkConnectionCreate defaults to DIRECT connection type."""
    from app.schemas.network import NetworkConnectionCreate, ConnectionType
    from uuid import uuid4

    data = NetworkConnectionCreate(
        source_id=uuid4(),
        source_type="subnet",
        destination_id=uuid4(),
        destination_type="external_device",
    )
    assert data.connection_type == ConnectionType.DIRECT


# ============================================================================
# TopologyGraphSchema Tests
# ============================================================================

def test_topology_graph_schema_defaults():
    """TopologyGraphSchema defaults to empty lists."""
    from app.schemas.network import TopologyGraphSchema

    schema = TopologyGraphSchema()
    assert len(schema.virtual_networks) == 0
    assert len(schema.subnets) == 0
    assert len(schema.nsgs) == 0
    assert len(schema.external_devices) == 0
    assert len(schema.connections) == 0


# ============================================================================
# ImpactAnalysisSchema Tests
# ============================================================================

def test_impact_analysis_schema_defaults():
    """ImpactAnalysisSchema defaults to empty lists."""
    from app.schemas.network import ImpactAnalysisSchema
    from uuid import uuid4

    schema = ImpactAnalysisSchema(
        nsg_id=uuid4(),
        nsg_name="test-nsg",
    )
    assert len(schema.before_rules) == 0
    assert len(schema.after_rules) == 0
    assert len(schema.affected_subnets) == 0
    assert len(schema.affected_external_devices) == 0


# ============================================================================
# NSGSyncSchema Tests
# ============================================================================

def test_nsg_sync_request_schema():
    """NSGSyncRequest has no required fields."""
    from app.schemas.network import NSGSyncRequest

    data = NSGSyncRequest()
    assert data is not None


def test_nsg_sync_response_schema():
    """NSGSyncResponse serializes correctly."""
    from app.schemas.network import NSGSyncResponse

    data = NSGSyncResponse(
        success=True,
        message="Synced successfully",
        sync_status="applied",
    )
    assert data.success is True
    assert data.sync_status == "applied"