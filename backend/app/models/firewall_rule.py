"""
Database models for firewall rules and workloads.

This module contains SQLAlchemy models that are compatible with both
SQLite (development) and PostgreSQL (production) databases.

Cross-database compatibility:
- Uses UUID (String) for primary keys instead of PostgreSQL-specific UUID type
- Uses Text for JSON arrays instead of ARRAY/JSONB
- Uses String for IP addresses instead of INET
- Uses String/Text for enum storage instead of PostgreSQL-specific Enum
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional, List, Any

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declared_attr, declarative_base
from sqlalchemy.types import TypeDecorator

if TYPE_CHECKING:
    from app.models.approval import ApprovalRequest


# UUID TypeDecorator for cross-database compatibility
class UUID(TypeDecorator):
    """Platform-independent UUID type.

    Stores UUIDs as CHAR(36) on databases that don't support UUID natively,
    and as UUID on databases that do support it. This ensures compatibility
    between SQLite and PostgreSQL.
    """

    impl = String(36)
    cache_ok = True

    def process_literal_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value) if isinstance(value, str) else value


Base = declarative_base()


class FirewallRuleAction(str, PyEnum):
    """Allowed actions for firewall rules."""
    Allow = "Allow"
    Deny = "Deny"


class FirewallProtocol(str, PyEnum):
    """Supported network protocols."""
    Any = "Any"
    Tcp = "Tcp"
    Udp = "Udp"
    IpProtocol = "IpProtocol"


class FirewallRuleStatus(str, PyEnum):
    """Status states for firewall rules."""
    Pending = "Pending"
    Active = "Active"
    Deleted = "Deleted"
    Error = "Error"


def _utc_now():
    """Return the current UTC datetime."""
    from datetime import datetime, timezone as tz
    return datetime.now(tz.utc)


class Workload(Base):
    """Workload model representing an Azure application or service.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key to ensure cross-database compatibility.
    """

    __tablename__ = "workloads"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    resource_groups = Column(Text, nullable=True)  # JSON string
    subscriptions = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    rules = relationship("FirewallRule", back_populates="workload", cascade="all, delete-orphan")
    approval_requests = relationship("ApprovalRequest", back_populates="workload_obj", cascade="all, delete-orphan")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_workloads")
    user_roles = relationship("UserRole", back_populates="workload", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workload(name={self.name!r})>"


class FirewallRule(Base):
    """Firewall rule model for Azure Firewall management.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key and foreign keys.
    Uses Text columns for array data (source_addresses, destination_fqdns, etc.)
    for cross-database compatibility.
    """

    __tablename__ = "firewall_rules"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    rule_collection_name = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    protocol = Column(String(50), nullable=False)
    source_addresses = Column(Text, nullable=True)
    destination_fqdns = Column(Text, nullable=True)
    source_ip_groups = Column(Text, nullable=True)
    destination_ports = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default=FirewallRuleStatus.Pending.value, nullable=False)
    workload_id = Column(UUID, ForeignKey("workloads.id"), nullable=True)
    azure_resource_id = Column(String(500), nullable=True)
    created_by = Column(UUID, nullable=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships
    workload = relationship("Workload", back_populates="rules")

    def __repr__(self):
        return f"<FirewallRule(name={self.rule_collection_name!r}, priority={self.priority})>"
