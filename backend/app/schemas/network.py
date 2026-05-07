"""
Network Topology Management Schemas.

This module defines Pydantic request/response schemas for all network entities,
including Virtual Networks, Subnets, NSGs, NSG Rules, External Devices,
and Connections.

Schemas support create/update/response patterns with proper validation rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enum values (mirrored from models for validation)
# ============================================================================

class SyncStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"


class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Protocol(str, Enum):
    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"
    AH = "AH"
    ANY = "*"


class Access(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class DeviceType(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    OTHER = "other"


class ConnectionType(str, Enum):
    DIRECT = "direct"
    VPN = "vpn"
    EXPRESS_ROUTER = "express_router"
    PEERING = "peering"
    VPN_GATEWAY = "vpn_gateway"
    CUSTOM = "custom"


# ============================================================================
# UUID helper schema
# ============================================================================

class UUIDSchema(BaseModel):
    """Base schema with a UUID id field."""

    id: uuid.UUID = Field(..., description="Entity UUID")


# ============================================================================
# Virtual Network Schemas
# ============================================================================

class VirtualNetworkCreate(BaseModel):
    """Schema for creating a Virtual Network."""

    name: str = Field(..., min_length=1, max_length=255, description="VNet name")
    address_space: str = Field(..., min_length=1, description="CIDR address space")
    location: str = Field(..., min_length=1, max_length=100, description="Azure region")
    resource_group: str = Field(..., min_length=1, description="Resource group name")
    subscription_id: Optional[str] = Field(None, description="Azure subscription ID")
    tags: Optional[dict] = Field(default_factory=dict, description="Metadata tags")

    @field_validator("address_space")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Basic CIDR format validation."""
        if "/" not in v or not v.split("/"):
            raise ValueError("address_space must be a valid CIDR notation")
        return v


class VirtualNetworkUpdate(BaseModel):
    """Schema for updating a Virtual Network."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address_space: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    resource_group: Optional[str] = None
    subscription_id: Optional[str] = None
    tags: Optional[dict] = None


class VirtualNetworkSchema(UUIDSchema):
    """Virtual Network response schema."""

    name: str
    address_space: str
    location: str
    resource_group: str
    subscription_id: Optional[str] = None
    tags: Optional[dict] = None
    is_synced: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Subnet Schemas
# ============================================================================

class SubnetCreate(BaseModel):
    """Schema for creating a Subnet."""

    name: str = Field(..., min_length=1, max_length=255, description="Subnet name")
    address_prefix: str = Field(..., min_length=1, description="CIDR prefix")
    vnet_id: uuid.UUID = Field(..., description="Parent VNet UUID")
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[dict] = Field(default_factory=dict)

    @field_validator("address_prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        if "/" not in v:
            raise ValueError("address_prefix must be a valid CIDR notation")
        return v


class SubnetUpdate(BaseModel):
    """Schema for updating a Subnet."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address_prefix: Optional[str] = None
    vnet_id: Optional[uuid.UUID] = None
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[dict] = None
    is_active: Optional[bool] = None


class SubnetSchema(UUIDSchema):
    """Subnet response schema."""

    name: str
    address_prefix: str
    vnet_id: uuid.UUID
    nsg_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    tags: Optional[dict] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# NSG Schemas
# ============================================================================

class NSGCreate(BaseModel):
    """Schema for creating a Network Security Group."""

    name: str = Field(..., min_length=1, max_length=255, description="NSG name")
    location: str = Field(..., min_length=1, max_length=100, description="Azure region")
    vnet_id: uuid.UUID = Field(..., description="Parent VNet UUID")
    resource_group: str = Field(..., min_length=1, description="Resource group name")
    subscription_id: Optional[str] = Field(None, description="Azure subscription ID")
    tags: Optional[dict] = Field(default_factory=dict)


class NSGUpdate(BaseModel):
    """Schema for updating a Network Security Group."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = None
    vnet_id: Optional[uuid.UUID] = None
    resource_group: Optional[str] = None
    subscription_id: Optional[str] = None
    tags: Optional[dict] = None
    sync_status: Optional[str] = None


class NSGRuleCreate(BaseModel):
    """Schema for creating an NSG rule."""

    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    priority: int = Field(..., ge=100, le=4096, description="Rule priority")
    direction: Direction = Field(..., description="Traffic direction")
    protocol: Protocol = Field(default=Protocol.ANY, description="Protocol")
    source_address_prefix: Optional[str] = None
    destination_address_prefix: Optional[str] = None
    source_port_range: Optional[str] = None
    destination_port_range: Optional[str] = None
    access: Access = Field(..., description="Allow or Deny")
    source_ip_group: Optional[str] = None
    destination_ip_group: Optional[str] = None
    service_tag: Optional[str] = None
    is_enabled: bool = True

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if v < 100 or v > 4096:
            raise ValueError("Priority must be between 100 and 4096")
        return v


class NSGRuleUpdate(BaseModel):
    """Schema for updating an NSG rule."""

    name: Optional[str] = None
    priority: Optional[int] = Field(None, ge=100, le=4096)
    direction: Optional[Direction] = None
    protocol: Optional[Protocol] = None
    source_address_prefix: Optional[str] = None
    destination_address_prefix: Optional[str] = None
    source_port_range: Optional[str] = None
    destination_port_range: Optional[str] = None
    access: Optional[Access] = None
    source_ip_group: Optional[str] = None
    destination_ip_group: Optional[str] = None
    service_tag: Optional[str] = None
    is_enabled: Optional[bool] = None


class NSGRuleSchema(UUIDSchema):
    """NSG Rule response schema."""

    nsg_id: uuid.UUID
    name: str
    priority: int
    direction: Direction
    protocol: Protocol = Protocol.ANY
    source_address_prefix: Optional[str] = None
    destination_address_prefix: Optional[str] = None
    source_port_range: Optional[str] = None
    destination_port_range: Optional[str] = None
    access: Access
    source_ip_group: Optional[str] = None
    destination_ip_group: Optional[str] = None
    service_tag: Optional[str] = None
    is_enabled: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NSGSchema(UUIDSchema):
    """Network Security Group response schema."""

    name: str
    location: str
    vnet_id: uuid.UUID
    resource_group: str
    subscription_id: Optional[str] = None
    tags: Optional[dict] = None
    sync_status: str = SyncStatus.PENDING
    azure_nsg_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    rules: List[NSGRuleSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# External Network Device Schemas
# ============================================================================

class ExternalDeviceCreate(BaseModel):
    """Schema for creating an External Network Device."""

    name: str = Field(..., min_length=1, max_length=255, description="Device name")
    ip_address: Optional[str] = Field(None, max_length=64)
    device_type: DeviceType = Field(default=DeviceType.OTHER)
    vendor: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    serial_number: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    tags: Optional[dict] = Field(default_factory=dict)

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and "@" not in v:
            raise ValueError("contact_email must be a valid email")
        return v


class ExternalDeviceUpdate(BaseModel):
    """Schema for updating an External Network Device."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ip_address: Optional[str] = None
    device_type: Optional[DeviceType] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[dict] = None
    is_active: Optional[bool] = None


class ExternalDeviceSchema(UUIDSchema):
    """External Network Device response schema."""

    name: str
    ip_address: Optional[str] = None
    device_type: DeviceType = DeviceType.OTHER
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[dict] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Network Connection Schemas
# ============================================================================

class NetworkConnectionCreate(BaseModel):
    """Schema for creating a Network Connection."""

    source_id: uuid.UUID = Field(..., description="Source entity UUID")
    source_type: str = Field(..., description="Source entity type")
    destination_id: uuid.UUID = Field(..., description="Destination entity UUID")
    destination_type: str = Field(..., description="Destination entity type")
    connection_type: ConnectionType = Field(default=ConnectionType.DIRECT)
    description: Optional[str] = Field(None, max_length=500)


class NetworkConnectionSchema(UUIDSchema):
    """Network Connection response schema."""

    source_id: uuid.UUID
    source_type: str
    destination_id: uuid.UUID
    destination_type: str
    connection_type: ConnectionType = ConnectionType.DIRECT
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Topology Graph Schema
# ============================================================================

class TopologyGraphSchema(BaseModel):
    """Aggregated response containing all network topology nodes and edges."""

    virtual_networks: List[VirtualNetworkSchema] = Field(default_factory=list)
    subnets: List[SubnetSchema] = Field(default_factory=list)
    nsgs: List[NSGSchema] = Field(default_factory=list)
    nsg_rules: List[NSGRuleSchema] = Field(default_factory=list)
    external_devices: List[ExternalDeviceSchema] = Field(default_factory=list)
    connections: List[NetworkConnectionSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ============================================================================
# Impact Analysis Schema
# ============================================================================

class ImpactAnalysisSchema(BaseModel):
    """Result of running impact analysis on NSG rule changes.

    Compares old rules vs new rules and identifies affected subnets
    and reachable external devices.
    """

    nsg_id: uuid.UUID = Field(..., description="NSG that was modified")
    nsg_name: str = Field(..., description="NSG name")
    before_rules: List[NSGRuleSchema] = Field(default_factory=list, description="Rules before change")
    after_rules: List[NSGRuleSchema] = Field(default_factory=list, description="Rules after change")
    affected_subnets: List[SubnetSchema] = Field(default_factory=list, description="Subnets affected by the change")
    affected_external_devices: List[ExternalDeviceSchema] = Field(
        default_factory=list,
        description="External devices reachable after the change",
    )
    changed_rule_ids: List[uuid.UUID] = Field(default_factory=list, description="IDs of rules that changed")
    added_rules: List[NSGRuleSchema] = Field(default_factory=list, description="Newly added rules")
    removed_rules: List[NSGRuleSchema] = Field(default_factory=list, description="Removed rules")

    model_config = {"from_attributes": True}


# ============================================================================
# Sync Schemas
# ============================================================================

class NSGSyncRequest(BaseModel):
    """Request to sync an NSG to Azure."""

    pass


class NSGSyncResponse(BaseModel):
    """Response from NSG sync operation."""

    success: bool
    message: str
    sync_status: str
    last_synced_at: Optional[datetime] = None


# ============================================================================
# Export all schemas
# ============================================================================

__all__ = [
    # Virtual Network
    "VirtualNetworkCreate",
    "VirtualNetworkUpdate",
    "VirtualNetworkSchema",
    # Subnet
    "SubnetCreate",
    "SubnetUpdate",
    "SubnetSchema",
    # NSG
    "NSGCreate",
    "NSGUpdate",
    "NSGSchema",
    # NSG Rules
    "NSGRuleCreate",
    "NSGRuleUpdate",
    "NSGRuleSchema",
    # External Devices
    "ExternalDeviceCreate",
    "ExternalDeviceUpdate",
    "ExternalDeviceSchema",
    # Connections
    "NetworkConnectionCreate",
    "NetworkConnectionSchema",
    # Topology & Analysis
    "TopologyGraphSchema",
    "ImpactAnalysisSchema",
    # Sync
    "NSGSyncRequest",
    "NSGSyncResponse",
]