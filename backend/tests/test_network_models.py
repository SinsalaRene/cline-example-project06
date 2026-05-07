"""
Tests for Network Topology Models.

Tests database models for VirtualNetwork, Subnet, NetworkSecurityGroup,
NSGRule, ExternalNetworkDevice, and NetworkConnection including
relationships, constraints, and serialization.
"""

import pytest
from datetime import datetime, timezone

from tests.conftest import db_session  # noqa: F401 - re-exported


# ============================================================================
# VirtualNetwork Tests
# ============================================================================

class TestVirtualNetwork:
    """Tests for the VirtualNetwork model."""

    def test_create_virtual_network(self, db_session):
        """Create a VirtualNetwork instance."""
        from app.models.network import VirtualNetwork
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
            subscription_id="sub-123",
        )
        db_session.add(vnet)
        db_session.commit()
        db_session.refresh(vnet)
        assert vnet.name == "test-vnet"
        assert vnet.address_space == "10.0.0.0/16"
        assert vnet.location == "eastus2"
        assert vnet.resource_group == "test-rg"
        assert vnet.subscription_id == "sub-123"
        assert vnet.is_synced is False
        assert vnet.created_at is not None

    def test_virtual_network_unique_name(self, db_session):
        """VirtualNetwork name must be unique."""
        from app.models.network import VirtualNetwork

        vnet1 = VirtualNetwork(
            name="shared-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        vnet2 = VirtualNetwork(
            name="shared-vnet",
            address_space="10.1.0.0/16",
            location="westus",
            resource_group="test-rg",
        )
        db_session.add_all([vnet1, vnet2])
        with pytest.raises(Exception):
            db_session.commit()

    def test_virtual_network_subnets_relationship(self, db_session):
        """VirtualNetwork has many Subnets."""
        from app.models.network import VirtualNetwork, Subnet
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        subnet1 = Subnet(name="subnet-a", address_prefix="10.0.1.0/24", vnet_id=vnet.id)
        subnet2 = Subnet(name="subnet-b", address_prefix="10.0.2.0/24", vnet_id=vnet.id)
        db_session.add_all([subnet1, subnet2])
        db_session.commit()

        db_session.refresh(vnet)
        assert len(vnet.subnets) == 2
        names = {s.name for s in vnet.subnets}
        assert "subnet-a" in names
        assert "subnet-b" in names

    def test_virtual_network_nsgs_relationship(self, db_session):
        """VirtualNetwork has many NetworkSecurityGroups."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg1 = NetworkSecurityGroup(
            name="nsg-a",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        nsg2 = NetworkSecurityGroup(
            name="nsg-b",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add_all([nsg1, nsg2])
        db_session.commit()

        db_session.refresh(vnet)
        assert len(vnet.nsgs) == 2

    def test_virtual_network_cascade_delete_subnets(self, db_session):
        """Deleting a VirtualNetwork cascades to Subnets."""
        from app.models.network import VirtualNetwork, Subnet
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        subnet = Subnet(name="subnet-a", address_prefix="10.0.1.0/24", vnet_id=vnet.id)
        db_session.add(subnet)
        db_session.commit()

        db_session.delete(vnet)
        db_session.commit()

        remaining = db_session.query(Subnet).filter(Subnet.vnet_id == vnet.id).all()
        assert len(remaining) == 0

    def test_virtual_network_cascade_delete_nsgs(self, db_session):
        """Deleting a VirtualNetwork cascades to NSGs."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="nsg-a",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        db_session.delete(vnet)
        db_session.commit()

        remaining = db_session.query(NetworkSecurityGroup).filter(
            NetworkSecurityGroup.vnet_id == vnet.id
        ).all()
        assert len(remaining) == 0


# ============================================================================
# Subnet Tests
# ============================================================================

class TestSubnet:
    """Tests for the Subnet model."""

    def test_create_subnet(self, db_session):
        """Create a Subnet instance."""
        from app.models.network import VirtualNetwork, Subnet
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        subnet = Subnet(
            name="subnet-a",
            address_prefix="10.0.1.0/24",
            vnet_id=vnet.id,
        )
        db_session.add(subnet)
        db_session.commit()
        db_session.refresh(subnet)

        assert subnet.name == "subnet-a"
        assert subnet.address_prefix == "10.0.1.0/24"
        assert subnet.vnet_id == vnet.id
        assert subnet.is_active is True

    def test_subnet_unique_name(self, db_session):
        """Subnet name must be unique."""
        from app.models.network import VirtualNetwork, Subnet

        vnet1 = VirtualNetwork(
            name="vnet-1",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        vnet2 = VirtualNetwork(
            name="vnet-2",
            address_space="10.1.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add_all([vnet1, vnet2])
        db_session.commit()

        s1 = Subnet(name="shared-subnet", address_prefix="10.0.1.0/24", vnet_id=vnet1.id)
        s2 = Subnet(name="shared-subnet", address_prefix="10.1.1.0/24", vnet_id=vnet2.id)
        db_session.add_all([s1, s2])

        with pytest.raises(Exception):
            db_session.commit()

    def test_subnet_nsg_relationship(self, db_session):
        """Subnet can be associated with an NSG."""
        from app.models.network import VirtualNetwork, Subnet, NetworkSecurityGroup
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        subnet = Subnet(
            name="subnet-a",
            address_prefix="10.0.1.0/24",
            vnet_id=vnet.id,
            nsg_id=nsg.id,
        )
        db_session.add(subnet)
        db_session.commit()

        db_session.refresh(subnet)
        assert subnet.nsg is not None
        assert subnet.nsg.name == "test-nsg"


# ============================================================================
# NetworkSecurityGroup Tests
# ============================================================================

class TestNetworkSecurityGroup:
    """Tests for the NetworkSecurityGroup model."""

    def test_create_nsg(self, db_session):
        """Create an NSG instance."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, SyncStatus
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
            sync_status=SyncStatus.PENDING,
        )
        db_session.add(nsg)
        db_session.commit()
        db_session.refresh(nsg)

        assert nsg.name == "test-nsg"
        assert nsg.sync_status == SyncStatus.PENDING
        assert nsg.vnet_id == vnet.id

    def test_nsg_unique_name(self, db_session):
        """NSG name must be unique."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup

        vnet = VirtualNetwork(
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg1 = NetworkSecurityGroup(
            name="shared-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        nsg2 = NetworkSecurityGroup(
            name="shared-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add_all([nsg1, nsg2])
        with pytest.raises(Exception):
            db_session.commit()

    def test_nsg_rules_relationship(self, db_session):
        """NSG has many NSGRules."""
        from app.models.network import (
            VirtualNetwork, NetworkSecurityGroup, NSGRule,
            Direction, Protocol, Access,
        )
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        rule1 = NSGRule(
            name="rule-a",
            priority=100,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
            source_address_prefix="10.0.0.0/8",
            destination_address_prefix="10.0.1.0/24",
            nsg_id=nsg.id,
        )
        rule2 = NSGRule(
            name="rule-b",
            priority=200,
            direction=Direction.OUTBOUND,
            protocol=Protocol.UDP,
            access=Access.DENY,
            source_address_prefix="0.0.0.0/0",
            destination_address_prefix="10.0.2.0/24",
            nsg_id=nsg.id,
        )
        db_session.add_all([rule1, rule2])
        db_session.commit()

        db_session.refresh(nsg)
        assert len(nsg.rules) == 2

    def test_nsg_sync_status(self, db_session):
        """NSG sync_status values."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, SyncStatus
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        for status in [SyncStatus.PENDING, SyncStatus.APPLIED, SyncStatus.FAILED]:
            nsg = NetworkSecurityGroup(
                name=f"nsg-{status}",
                location="eastus2",
                vnet_id=vnet.id,
                resource_group="test-rg",
                sync_status=status,
            )
            db_session.add(nsg)
        db_session.commit()

        for status in [SyncStatus.PENDING, SyncStatus.APPLIED, SyncStatus.FAILED]:
            count = db_session.query(NetworkSecurityGroup).filter(
                NetworkSecurityGroup.sync_status == status
            ).count()
            assert count == 1

    def test_nsg_delete_cascades_rules(self, db_session):
        """Deleting NSG cascades to NSGRules."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, NSGRule, Direction, Protocol, Access
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        rule = NSGRule(
            name="test-rule",
            priority=100,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
            nsg_id=nsg.id,
        )
        db_session.add(rule)
        db_session.commit()

        db_session.delete(nsg)
        db_session.commit()

        remaining = db_session.query(NSGRule).filter(NSGRule.nsg_id == nsg.id).all()
        assert len(remaining) == 0


# ============================================================================
# NSGRule Tests
# ============================================================================

class TestNSGRule:
    """Tests for the NSGRule model."""

    def test_create_nsg_rule(self, db_session):
        """Create an NSGRule instance."""
        from app.models.network import (
            VirtualNetwork, NetworkSecurityGroup, NSGRule,
            Direction, Protocol, Access,
        )
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        rule = NSGRule(
            name="test-rule",
            priority=100,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
            source_address_prefix="10.0.0.0/8",
            destination_address_prefix="10.0.1.0/24",
            nsg_id=nsg.id,
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        assert rule.name == "test-rule"
        assert rule.priority == 100
        assert rule.direction == Direction.INBOUND
        assert rule.protocol == Protocol.TCP
        assert rule.access == Access.ALLOW

    def test_nsg_rule_priority_range(self, db_session):
        """NSG rule priority must be 100-4096."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, NSGRule, Direction, Protocol, Access
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        # Priority 99 (below minimum)
        rule_low = NSGRule(
            name="rule-low",
            priority=99,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
            nsg_id=nsg.id,
        )
        db_session.add(rule_low)
        with pytest.raises(Exception):
            db_session.commit()

    def test_nsg_rule_direction_values(self, db_session):
        """NSG rule direction must be inbound or outbound."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, NSGRule, Direction, Protocol, Access
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        rule_in = NSGRule(
            name="rule-in",
            priority=100,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
            nsg_id=nsg.id,
        )
        rule_out = NSGRule(
            name="rule-out",
            priority=200,
            direction=Direction.OUTBOUND,
            protocol=Protocol.UDP,
            access=Access.DENY,
            nsg_id=nsg.id,
        )
        db_session.add_all([rule_in, rule_out])
        db_session.commit()

        assert db_session.query(NSGRule).filter(NSGRule.direction == Direction.INBOUND).count() == 1
        assert db_session.query(NSGRule).filter(NSGRule.direction == Direction.OUTBOUND).count() == 1

    def test_nsg_rule_access_values(self, db_session):
        """NSG rule access must be allow or deny."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, NSGRule, Direction, Protocol, Access
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        rule_allow = NSGRule(
            name="rule-allow",
            priority=100,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.ALLOW,
            nsg_id=nsg.id,
        )
        rule_deny = NSGRule(
            name="rule-deny",
            priority=200,
            direction=Direction.INBOUND,
            protocol=Protocol.TCP,
            access=Access.DENY,
            nsg_id=nsg.id,
        )
        db_session.add_all([rule_allow, rule_deny])
        db_session.commit()

        assert db_session.query(NSGRule).filter(NSGRule.access == Access.ALLOW).count() == 1
        assert db_session.query(NSGRule).filter(NSGRule.access == Access.DENY).count() == 1

    def test_nsg_rule_order_by_priority(self, db_session):
        """NSG rules are ordered by priority."""
        from app.models.network import VirtualNetwork, NetworkSecurityGroup, NSGRule, Direction, Protocol, Access
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        for priority in [300, 100, 200]:
            rule = NSGRule(
                name=f"rule-{priority}",
                priority=priority,
                direction=Direction.INBOUND,
                protocol=Protocol.TCP,
                access=Access.ALLOW,
                nsg_id=nsg.id,
            )
            db_session.add(rule)
        db_session.commit()

        db_session.refresh(nsg)
        priorities = [r.priority for r in nsg.rules]
        assert priorities == sorted(priorities)


# ============================================================================
# ExternalNetworkDevice Tests
# ============================================================================

class TestExternalNetworkDevice:
    """Tests for the ExternalNetworkDevice model."""

    def test_create_external_device(self, db_session):
        """Create an ExternalNetworkDevice instance."""
        from app.models.network import ExternalNetworkDevice, DeviceType
        from uuid import uuid4

        device = ExternalNetworkDevice(
            id=uuid4(),
            name="test-router",
            ip_address="192.168.1.1",
            device_type=DeviceType.ROUTER,
            vendor="Cisco",
            model="ISR4451",
            contact_name="John Doe",
            contact_email="john@example.com",
        )
        db_session.add(device)
        db_session.commit()
        db_session.refresh(device)

        assert device.name == "test-router"
        assert device.ip_address == "192.168.1.1"
        assert device.device_type == DeviceType.ROUTER
        assert device.vendor == "Cisco"
        assert device.model == "ISR4451"
        assert device.contact_name == "John Doe"

    def test_external_device_unique_name(self, db_session):
        """ExternalNetworkDevice name must be unique."""
        from app.models.network import ExternalNetworkDevice, DeviceType

        d1 = ExternalNetworkDevice(
            name="shared-device",
            device_type=DeviceType.ROUTER,
        )
        d2 = ExternalNetworkDevice(
            name="shared-device",
            device_type=DeviceType.SWITCH,
        )
        db_session.add_all([d1, d2])
        with pytest.raises(Exception):
            db_session.commit()

    def test_external_device_device_types(self, db_session):
        """ExternalNetworkDevice device_type values."""
        from app.models.network import ExternalNetworkDevice, DeviceType

        for dtype in [DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.FIREWALL, DeviceType.OTHER]:
            device = ExternalNetworkDevice(
                name=f"device-{dtype}",
                device_type=dtype,
            )
            db_session.add(device)
        db_session.commit()

        for dtype in [DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.FIREWALL, DeviceType.OTHER]:
            count = db_session.query(ExternalNetworkDevice).filter(
                ExternalNetworkDevice.device_type == dtype
            ).count()
            assert count == 1

    def test_external_device_subnets_relationship(self, db_session):
        """ExternalNetworkDevice connects to Subnets."""
        from app.models.network import (
            VirtualNetwork, Subnet, ExternalNetworkDevice,
            DeviceType, subnet_device_connections,
        )
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        subnet = Subnet(
            name="subnet-a",
            address_prefix="10.0.1.0/24",
            vnet_id=vnet.id,
        )
        db_session.add(subnet)
        db_session.commit()

        device = ExternalNetworkDevice(
            name="test-router",
            device_type=DeviceType.ROUTER,
        )
        db_session.add(device)
        db_session.commit()

        # Connect device to subnet via association table
        db_session.execute(
            subnet_device_connections.insert().values(
                subnet_id=subnet.id,
                device_id=device.id,
            )
        )
        db_session.commit()

        db_session.refresh(device)
        assert len(device.subnets) == 1
        assert device.subnets[0].name == "subnet-a"


# ============================================================================
# NetworkConnection Tests
# ============================================================================

class TestNetworkConnection:
    """Tests for the NetworkConnection model."""

    def test_create_connection(self, db_session):
        """Create a NetworkConnection instance."""
        from app.models.network import (
            VirtualNetwork, Subnet, ExternalNetworkDevice,
            NetworkConnection, DeviceType, ConnectionType,
        )
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        subnet = Subnet(
            name="subnet-a",
            address_prefix="10.0.1.0/24",
            vnet_id=vnet.id,
        )
        db_session.add(subnet)
        db_session.commit()

        device = ExternalNetworkDevice(
            name="test-router",
            device_type=DeviceType.ROUTER,
        )
        db_session.add(device)
        db_session.commit()

        conn = NetworkConnection(
            source_id=subnet.id,
            source_type="subnet",
            destination_id=device.id,
            destination_type="external_device",
            connection_type=ConnectionType.DIRECT,
            description="Direct connection",
        )
        db_session.add(conn)
        db_session.commit()
        db_session.refresh(conn)

        assert conn.source_id == subnet.id
        assert conn.source_type == "subnet"
        assert conn.destination_id == device.id
        assert conn.destination_type == "external_device"
        assert conn.connection_type == ConnectionType.DIRECT

    def test_connection_type_values(self, db_session):
        """NetworkConnection connection_type values."""
        from app.models.network import (
            VirtualNetwork, Subnet, ExternalNetworkDevice,
            NetworkConnection, DeviceType, ConnectionType,
        )
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        subnet = Subnet(
            name="subnet-a",
            address_prefix="10.0.1.0/24",
            vnet_id=vnet.id,
        )
        db_session.add(subnet)
        db_session.commit()

        device = ExternalNetworkDevice(
            name="test-router",
            device_type=DeviceType.ROUTER,
        )
        db_session.add(device)
        db_session.commit()

        for ctype in [ConnectionType.DIRECT, ConnectionType.VPN, ConnectionType.VPN_GATEWAY]:
            conn = NetworkConnection(
                source_id=subnet.id,
                source_type="subnet",
                destination_id=device.id,
                destination_type="external_device",
                connection_type=ctype,
            )
            db_session.add(conn)

        db_session.commit()

        for ctype in [ConnectionType.DIRECT, ConnectionType.VPN, ConnectionType.VPN_GATEWAY]:
            count = db_session.query(NetworkConnection).filter(
                NetworkConnection.connection_type == ctype
            ).count()
            assert count == 1

    def test_connection_nsg_to_subnet(self, db_session):
        """NetworkConnection between NSG and Subnet."""
        from app.models.network import (
            VirtualNetwork, NetworkSecurityGroup, Subnet,
            NetworkConnection, ConnectionType,
        )
        from uuid import uuid4

        vnet = VirtualNetwork(
            id=uuid4(),
            name="test-vnet",
            address_space="10.0.0.0/16",
            location="eastus2",
            resource_group="test-rg",
        )
        db_session.add(vnet)
        db_session.commit()

        nsg = NetworkSecurityGroup(
            name="test-nsg",
            location="eastus2",
            vnet_id=vnet.id,
            resource_group="test-rg",
        )
        db_session.add(nsg)
        db_session.commit()

        subnet = Subnet(
            name="subnet-a",
            address_prefix="10.0.1.0/24",
            vnet_id=vnet.id,
        )
        db_session.add(subnet)
        db_session.commit()

        conn = NetworkConnection(
            source_id=nsg.id,
            source_type="nsg",
            destination_id=subnet.id,
            destination_type="subnet",
            connection_type=ConnectionType.DIRECT,
        )
        db_session.add(conn)
        db_session.commit()

        assert conn.source_type == "nsg"
        assert conn.destination_type == "subnet"

    def test_connection_unique_constraint(self, db_session):
        """NetworkConnection has unique source/dest/type/connection_type pairs.

        Uses two separate database sessions to ensure the unique constraint
        fires correctly without session state interference.
        """
        from app.models.network import VirtualNetwork, Subnet, NetworkConnection, ConnectionType
        from app.database import get_engine
        from uuid import uuid4
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Create an isolated test engine to avoid polluting the module-scoped
        # test database and to ensure a clean slate for constraint testing
        import tempfile
        import os
        test_dir = tempfile.mkdtemp(prefix="conn_test_")
        test_db_path = os.path.join(test_dir, "conn_test.db")
        test_engine = create_engine(f"sqlite:///{test_db_path}")

        # Create all tables
        from app.models import Base
        Base.metadata.create_all(test_engine)

        Session = sessionmaker(bind=test_engine)
        ts = Session()

        try:
            # Create supporting entities
            vnet = VirtualNetwork(
                id=uuid4(),
                name="test-vnet-constraint",
                address_space="10.0.0.0/16",
                location="eastus2",
                resource_group="test-rg",
            )
            ts.add(vnet)
            ts.commit()

            subnet1 = Subnet(
                name="subnet-x",
                address_prefix="10.0.3.0/24",
                vnet_id=vnet.id,
            )
            subnet2 = Subnet(
                name="subnet-y",
                address_prefix="10.0.4.0/24",
                vnet_id=vnet.id,
            )
            ts.add_all([subnet1, subnet2])
            ts.commit()
            ts.refresh(subnet1)
            ts.refresh(subnet2)

            # Same connection_type with same source/dest should fail
            conn1 = NetworkConnection(
                source_id=subnet1.id,
                source_type="subnet",
                destination_id=subnet2.id,
                destination_type="subnet",
                connection_type=ConnectionType.DIRECT,
            )
            ts.add(conn1)
            ts.commit()

            # Try to create a duplicate with the same connection_type
            conn2 = NetworkConnection(
                source_id=subnet1.id,
                source_type="subnet",
                destination_id=subnet2.id,
                destination_type="subnet",
                connection_type=ConnectionType.DIRECT,
            )
            ts.add(conn2)
            with pytest.raises(Exception):
                ts.commit()

            # Clean up - different connection types should succeed
            ts.rollback()

            conn3 = NetworkConnection(
                source_id=subnet1.id,
                source_type="subnet",
                destination_id=subnet2.id,
                destination_type="subnet",
                connection_type=ConnectionType.VPN,
            )
            ts.add(conn3)
            ts.commit()
            ts.refresh(conn3)
            assert conn3.id is not None
        finally:
            ts.close()
            import shutil
            try:
                shutil.rmtree(test_dir)
            except FileNotFoundError:
                pass
