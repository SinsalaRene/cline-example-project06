"""
Network Topology Management Models.

This module defines SQLAlchemy ORM models for network topology management,
including Virtual Networks, Subnets, Network Security Groups (NSG),
NSG Rules, External Network Devices, and Network Connections.

These models support the network topology views and NSG management
features of the Azure Firewall Management application.

## Entity Relationships

- VirtualNetwork 1→* Subnet (via vnet_id FK)
- VirtualNetwork 1→* NetworkSecurityGroup (via vnet_id FK)
- NetworkSecurityGroup 1→* NSGRule (via nsg_id FK)
- NetworkConnection references ExternalNetworkDevice, Subnet, or NetworkSecurityGroup
  through polymorphic (id + type) pairs

## Cross-Database Compatibility

Uses UUID TypeDecorator for primary keys, String columns for enum storage,
and Text for structured data to ensure compatibility between SQLite
and PostgreSQL databases.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Table,
    Index,
    CheckConstraint,
    UniqueConstraint,
    Boolean,
    TypeDecorator,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.firewall_rule import Base, UUID


# ============================================================================
# Helper: shared timestamp columns
# ============================================================================

def _created_at():
    """Default factory for created_at column."""
    return datetime.now(timezone.utc)


def _updated_at():
    """Default factory for updated_at column."""
    return datetime.now(timezone.utc)


# ============================================================================
# Enums (string-based for cross-database compatibility)
# ============================================================================

class SyncStatus(str):
    """Sync status of an NSG with Azure."""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"


class Direction(str):
    """Traffic direction for NSG rules."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Protocol(str):
    """Protocol types for NSG rules."""
    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"
    AH = "AH"
    ANY = "*"


class Access(str):
    """Access action for NSG rules."""
    ALLOW = "allow"
    DENY = "deny"


class DeviceType(str):
    """Types of external network devices."""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    OTHER = "other"


class ConnectionType(str):
    """Types of network connections."""
    DIRECT = "direct"
    VPN = "vpn"
    EXPRESS_ROUTER = "express_router"
    PEERING = "peering"
    VPN_GATEWAY = "vpn_gateway"
    CUSTOM = "custom"


# ============================================================================
# Association Table: Subnet ↔ ExternalNetworkDevice (multiple connections)
# ============================================================================

subnet_device_connections = Table(
    "subnet_device_connections",
    Base.metadata,
    Column("subnet_id", ForeignKey("subnets.id"), primary_key=True),
    Column("device_id", ForeignKey("external_network_devices.id"), primary_key=True),
    comment="Many-to-many: subnets connected to external devices",
)


# ============================================================================
# Models
# ============================================================================


class Subnet(Base):
    """Represents a subnet within a Virtual Network.

    Subnets are logical partitions of a virtual network address space.
    Each subnet can contain resources and is associated with a Network
    Security Group for traffic control.

    Relationships:
        - Belongs to one VirtualNetwork (vnet_id FK)
        - Has zero or one NetworkSecurityGroup (nsg)
        - Can have many NetworkConnection references
        - Can be connected to many ExternalNetworkDevices (via subnet_device_connections)
    """

    __tablename__ = "subnets"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, comment="Primary key (UUID)")
    name = Column(String(255), nullable=False, unique=True, index=True, comment="Friendly name of the subnet")
    address_prefix = Column(String(64), nullable=False, comment="CIDR address prefix, e.g. '10.0.1.0/24'")
    vnet_id = Column(
        UUID,
        ForeignKey("virtual_networks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent VirtualNetwork",
    )
    nsg_id = Column(
        UUID,
        ForeignKey("network_security_groups.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to associated NSG",
    )
    description = Column(String(500), nullable=True, comment="Optional description")
    # Text for JSON array data for cross-database compatibility
    tags = Column(Text, nullable=True, default=None, comment="JSON metadata tags")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_created_at, nullable=False)
    updated_at = Column(DateTime, default=_updated_at, onupdate=_updated_at, nullable=False)

    # --- Relationships ---
    virtual_network = relationship(
        "VirtualNetwork",
        back_populates="subnets",
        single_parent=True,
    )
    nsg = relationship(
        "NetworkSecurityGroup",
        back_populates="subnets",
        single_parent=True,
    )
    external_devices = relationship(
        "ExternalNetworkDevice",
        secondary=subnet_device_connections,
        back_populates="subnets",
        lazy="selectin",
    )

    # --- Indexes ---
    __table_args__ = (
        # vnet_id has index=True on the column; use explicit index for nsg_id
        Index("ix_subnets_nsg_id", "nsg_id"),
        CheckConstraint("LENGTH(address_prefix) > 0", name="chk_address_prefix"),
    )

    def __repr__(self):
        return f"<Subnet(id={self.id}, name='{self.name}', prefix='{self.address_prefix}')>"


class VirtualNetwork(Base):
    """Represents an Azure Virtual Network.

    Virtual Networks are the fundamental networking construct in Azure.
    They contain subnets, NSGs, and serve as the top-level grouping
    for network resources.

    Relationships:
        - Has many Subnets
        - Has many NetworkSecurityGroups
    """

    __tablename__ = "virtual_networks"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, comment="Primary key (UUID)")
    name = Column(String(255), nullable=False, unique=True, index=True, comment="Azure VNet name")
    address_space = Column(String(255), nullable=False, comment="Address space CIDR, e.g. '10.0.0.0/16'")
    location = Column(String(100), nullable=False, comment="Azure region, e.g. 'eastus2'")
    resource_group = Column(String(255), nullable=False, index=True, comment="Azure resource group name")
    subscription_id = Column(String(255), nullable=True, comment="Azure subscription ID")
    # Text for JSON array data for cross-database compatibility
    tags = Column(Text, nullable=True, default=None, comment="JSON metadata tags")
    is_synced = Column(Boolean, default=False, nullable=False, comment="Whether VNet is synced with Azure")
    created_at = Column(DateTime, default=_created_at, nullable=False)
    updated_at = Column(DateTime, default=_updated_at, onupdate=_updated_at, nullable=False)

    # --- Relationships ---
    subnets = relationship(
        "Subnet",
        back_populates="virtual_network",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    nsgs = relationship(
        "NetworkSecurityGroup",
        back_populates="virtual_network",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # --- Indexes ---
    __table_args__ = (
        # NOTE: resource_group already has index=True on the column,
        # so no need for a duplicate explicit Index below.
    )

    def __repr__(self):
        return f"<VirtualNetwork(id={self.id}, name='{self.name}', group='{self.resource_group}')>"


class NetworkSecurityGroup(Base):
    """Represents a Network Security Group associated with a Virtual Network.

    NSGs contain rules that allow or deny network traffic. They can be
    synced with Azure NSGs tracked via sync_status.

    Relationships:
        - Belongs to one VirtualNetwork
        - Has many NSGRules
        - Has many Subnets (via nsg_id FK)
    """

    __tablename__ = "network_security_groups"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, comment="Primary key (UUID)")
    name = Column(String(255), nullable=False, unique=True, index=True, comment="NSG name")
    location = Column(String(100), nullable=False, comment="Azure region")
    vnet_id = Column(
        UUID,
        ForeignKey("virtual_networks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent VirtualNetwork",
    )
    resource_group = Column(String(255), nullable=False, comment="Azure resource group name")
    subscription_id = Column(String(255), nullable=True, comment="Azure subscription ID")
    # Text for JSON array data for cross-database compatibility
    tags = Column(Text, nullable=True, default=None, comment="JSON metadata tags")
    sync_status = Column(
        String(20),
        default=SyncStatus.PENDING,
        nullable=False,
        comment="Sync status with Azure",
    )
    azure_nsg_id = Column(String(500), nullable=True, comment="Azure resource ID of the synced NSG")
    last_synced_at = Column(DateTime, nullable=True, comment="Last successful sync timestamp")
    created_at = Column(DateTime, default=_created_at, nullable=False)
    updated_at = Column(DateTime, default=_updated_at, onupdate=_updated_at, nullable=False)

    # --- Relationships ---
    virtual_network = relationship(
        "VirtualNetwork",
        back_populates="nsgs",
        single_parent=True,
    )
    rules = relationship(
        "NSGRule",
        back_populates="nsg",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="NSGRule.priority.asc()",
    )
    subnets = relationship(
        "Subnet",
        back_populates="nsg",
        viewonly=True,
    )

    # --- Indexes ---
    __table_args__ = (
        # vnet_id has index=True above; explicit indexes for sync_status and composite
        Index("ix_network_security_groups_sync_status", "sync_status"),
    )

    def __repr__(self):
        return f"<NetworkSecurityGroup(id={self.id}, name='{self.name}', status={self.sync_status})>"


class NSGRule(Base):
    """Represents a rule within a Network Security Group.

    Each rule defines a priority, direction, protocol, source/destination
    addresses/ports, and access action (allow/deny).

    Relationships:
        - Belongs to one NetworkSecurityGroup
    """

    __tablename__ = "nsg_rules"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, comment="Primary key (UUID)")
    nsg_id = Column(
        UUID,
        ForeignKey("network_security_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent NSG",
    )
    name = Column(String(255), nullable=False, comment="Rule name")
    priority = Column(Integer, nullable=False, comment="Rule priority (100-4096)")
    direction = Column(
        String(20),
        nullable=False,
        comment="Traffic direction: inbound or outbound",
    )
    protocol = Column(
        String(20),
        nullable=False,
        server_default="*",
        comment="Protocol: TCP, UDP, ICMP, AH, or *",
    )
    source_address_prefix = Column(String(500), nullable=True, comment="Source IP range/CIDR")
    destination_address_prefix = Column(String(500), nullable=True, comment="Destination IP range/CIDR")
    source_port_range = Column(String(500), nullable=True, comment="Source port or range")
    destination_port_range = Column(String(500), nullable=True, comment="Destination port or range")
    access = Column(
        String(20),
        nullable=False,
        comment="Allow or Deny",
    )
    source_ip_group = Column(String(500), nullable=True, comment="Source IP Group resource ID")
    destination_ip_group = Column(String(500), nullable=True, comment="Destination IP Group resource ID")
    service_tag = Column(String(500), nullable=True, comment="Azure Service Tag name")
    priority_min = Column(Integer, default=100, nullable=False, server_default="100", comment="Minimum valid priority")
    priority_max = Column(Integer, default=4096, nullable=False, server_default="4096", comment="Maximum valid priority")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="Whether the rule is enabled")
    created_at = Column(DateTime, default=_created_at, nullable=False)
    updated_at = Column(DateTime, default=_updated_at, onupdate=_updated_at, nullable=False)

    # --- Relationships ---
    nsg = relationship(
        "NetworkSecurityGroup",
        back_populates="rules",
        single_parent=True,
    )

    # --- Indexes ---
    __table_args__ = (
        # nsg_id and priority have index=True on columns; explicit composite index
        Index("ix_nsg_rules_priority", "nsg_id", "priority"),
        CheckConstraint(
            "priority >= 100 AND priority <= 4096",
            name="chk_priority_range",
        ),
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="chk_direction_values",
        ),
        CheckConstraint(
            "access IN ('allow', 'deny')",
            name="chk_access_values",
        ),
    )

    def __repr__(self):
        return (
            f"<NSGRule(id={self.id}, name='{self.name}', "
            f"priority={self.priority}, dir={self.direction}, access={self.access})>"
        )


class ExternalNetworkDevice(Base):
    """Represents an external network device in the network topology.

    Physical or virtual devices such as routers, switches, firewalls,
    or other network infrastructure that connect to or interact with
    the virtual network.

    Relationships:
        - Connected to many Subnets via subnet_device_connections
    """

    __tablename__ = "external_network_devices"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, comment="Primary key (UUID)")
    name = Column(String(255), nullable=False, unique=True, index=True, comment="Device name")
    ip_address = Column(String(64), nullable=True, index=True, comment="Management IP address")
    device_type = Column(
        String(20),
        nullable=False,
        server_default="other",
        comment="Type of device",
    )
    vendor = Column(String(255), nullable=True, comment="Manufacturer/vendor name")
    model = Column(String(255), nullable=True, comment="Model number")
    serial_number = Column(String(255), nullable=True, unique=True, comment="Serial number")
    contact_name = Column(String(255), nullable=True, comment="Contact person name")
    contact_email = Column(String(255), nullable=True, comment="Contact person email")
    contact_phone = Column(String(50), nullable=True, comment="Contact phone number")
    notes = Column(Text, nullable=True, comment="Additional notes")
    # Text for JSON array data for cross-database compatibility
    tags = Column(Text, nullable=True, default=None, comment="JSON metadata tags")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_created_at, nullable=False)
    updated_at = Column(DateTime, default=_updated_at, onupdate=_updated_at, nullable=False)

    # --- Relationships ---
    subnets = relationship(
        "Subnet",
        secondary=subnet_device_connections,
        back_populates="external_devices",
        lazy="selectin",
    )

    # --- Indexes ---
    __table_args__ = (
        Index("ix_external_network_devices_type", "device_type"),
        Index("ix_external_network_devices_vendor", "vendor"),
    )

    def __repr__(self):
        return f"<ExternalNetworkDevice(id={self.id}, name='{self.name}', type={self.device_type})>"


class NetworkConnection(Base):
    """Represents a link in the network topology graph.

    Connections define how network entities relate to each other.
    Each connection references a source and destination, each of which
    can be a Subnet, NetworkSecurityGroup, or ExternalNetworkDevice.

    Relationships:
        - References source and destination entities (polymorphic via type strings)
    """

    __tablename__ = "network_connections"

    id = Column(UUID, primary_key=True, default=uuid.uuid4, comment="Primary key (UUID)")
    source_id = Column(UUID, nullable=False, comment="Source entity ID")
    source_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Source entity type: subnet, nsg, external_device",
    )
    destination_id = Column(UUID, nullable=False, comment="Destination entity ID")
    destination_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Destination entity type: subnet, nsg, external_device",
    )
    connection_type = Column(
        String(20),
        nullable=False,
        server_default="direct",
        comment="Type of connection",
    )
    description = Column(String(500), nullable=True, comment="Connection description")
    created_at = Column(DateTime, default=_created_at, nullable=False)

    # --- Relationships ---
    # NOTE: NetworkConnection is polymorphic — it references Subnet, NSG, or
    # ExternalNetworkDevice via (id + type) pairs.  No FK exists; lookups
    # are performed in the service layer using source_id/source_type and
    # destination_id/destination_type columns.
    __table_args__ = (
        # Unique constraint on source/dest pairs (same connection type)
        # Different connection types between same entities are allowed
        UniqueConstraint(
            "source_id", "destination_id", "source_type", "destination_type", "connection_type",
            name="uq_source_destination_conn",
        ),
        Index("ix_network_connections_lookup", "source_id", "destination_id"),
        Index("ix_network_connections_source", "source_id", "source_type"),
        Index("ix_network_connections_dest", "destination_id", "destination_type"),
    )

    def __repr__(self):
        return (
            f"<NetworkConnection(id={self.id}, "
            f"source={self.source_type}:{self.source_id}, "
            f"dest={self.destination_type}:{self.destination_id})>"
        )


# ============================================================================
# Model exports
# ============================================================================

__all__ = [
    "Subnet",
    "VirtualNetwork",
    "NetworkSecurityGroup",
    "NSGRule",
    "ExternalNetworkDevice",
    "NetworkConnection",
    "SyncStatus",
    "Direction",
    "Protocol",
    "Access",
    "DeviceType",
    "ConnectionType",
    "subnet_device_connections",
]