"""
Pydantic schemas for Firewall Rules.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


class FirewallRuleAction(str, Enum):
    Allow = "Allow"
    allow = "allow"
    Deny = "Deny"
    deny = "deny"

    @classmethod
    def _missing_(cls, value):
        if value is None:
            return None
        # Try direct match first
        if hasattr(value, 'value'):
            return value
        value_stripped = str(value).strip()
        # Try case-insensitive match
        for member in cls:
            if member.value.lower() == value_stripped.lower():
                return member
        # Try title case
        value_title = value_stripped.title()
        for member in cls:
            if member.value == value_title:
                return member
        return None


class FirewallProtocol(str, Enum):
    Http = "Http"
    Https = "Https"
    Tcp = "Tcp"
    Udp = "Udp"
    Icmp = "Icmp"
    Any = "Any"

    @classmethod
    def _missing_(cls, value):
        if value is None:
            return None
        # Try direct match first
        if hasattr(value, 'value'):
            return value
        value_stripped = str(value).strip()
        # Try case-insensitive match
        for member in cls:
            if member.value.lower() == value_stripped.lower():
                return member
        # Try title case
        value_title = value_stripped.title()
        for member in cls:
            if member.value == value_title:
                return member
        return None


class FirewallRuleStatus(str, Enum):
    Active = "active"
    Pending = "pending"
    Archived = "archived"


# --- Request Schemas ---

class FirewallRuleCreate(BaseModel):
    """Schema for creating a firewall rule."""
    rule_collection_name: str = Field(..., min_length=1, max_length=255)
    priority: int = Field(..., ge=1, le=65000)
    rule_group_name: Optional[str] = None
    action: FirewallRuleAction
    protocol: FirewallProtocol
    source_addresses: Optional[list[str]] = None
    destination_fqdns: Optional[list[str]] = None
    source_ip_groups: Optional[list[str]] = None
    destination_ports: Optional[list[int]] = None
    description: Optional[str] = None
    workload_id: Optional[UUID] = None
    azure_resource_id: Optional[str] = None


class FirewallRuleUpdate(BaseModel):
    """Schema for updating a firewall rule."""
    rule_collection_name: Optional[str] = None
    priority: Optional[int] = None
    rule_group_name: Optional[str] = None
    action: Optional[FirewallRuleAction] = None
    protocol: Optional[FirewallProtocol] = None
    source_addresses: Optional[list[str]] = None
    destination_fqdns: Optional[list[str]] = None
    source_ip_groups: Optional[list[str]] = None
    destination_ports: Optional[list[int]] = None
    description: Optional[str] = None


class FirewallRuleImport(BaseModel):
    """Schema for bulk importing firewall rules."""
    rules: list[FirewallRuleCreate] = Field(..., min_length=1, description="Rules list must have at least one rule")


# --- Response Schemas ---

class FirewallRuleResponse(BaseModel):
    """Response schema for a firewall rule."""
    id: UUID
    rule_collection_name: str
    priority: int
    rule_group_name: Optional[str] = None
    action: FirewallRuleAction
    protocol: FirewallProtocol
    source_addresses: Optional[list[str]] = None
    destination_fqdns: Optional[list[str]] = None
    source_ip_groups: Optional[list[str]] = None
    destination_ports: Optional[list[int]] = None
    description: Optional[str] = None
    workload_id: Optional[UUID] = None
    azure_resource_id: str
    status: FirewallRuleStatus
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkloadResponse(BaseModel):
    """Response schema for a workload."""
    id: UUID
    name: str
    description: Optional[str] = None
    owner_id: Optional[UUID] = None
    resource_groups: Optional[list[str]] = None
    subscriptions: Optional[list[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Aliases for backward compatibility ---
# These aliases are used by schemas/__init__.py to import names that are 
# equivalent to the actual schema names above.

FirewallRuleSchema = FirewallRuleResponse
FirewallRuleSearch = FirewallRuleCreate
FirewallRuleBulkCreate = FirewallRuleImport
FirewallRuleBulkResponse = list[FirewallRuleResponse]
