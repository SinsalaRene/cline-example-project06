"""
Database models for firewall rules and workloads.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Integer, DateTime, Text, UUID as SQLAlchemyUUID, Enum as SQLAlchemyEnum, ForeignKey, func
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import ForeignKeyConstraint
import enum


class FirewallRuleAction(str, Enum):
    Allow = "Allow"
    Deny = "Deny"


class FirewallProtocol(str, Enum):
    Any = "Any"
    Tcp = "Tcp"
    Udp = "Udp"
    IpProtocol = "IpProtocol"


class FirewallRuleStatus(str, Enum):
    Pending = "Pending"
    Active = "Active"
    Deleted = "Deleted"
    Error = "Error"


Base = declarative_base()


class Workload(Base):
    """Workload model representing an Azure application or service."""

    __tablename__ = "workloads"

    id = Column(SQLAlchemyUUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    owner_id = Column(SQLAlchemyUUID, nullable=True)
    resource_groups = Column(Text, nullable=True)  # JSON string
    subscriptions = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    rules = relationship("FirewallRule", back_populates="workload", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workload(name={self.name})>"


class FirewallRule(Base):
    """Firewall rule model."""

    __tablename__ = "firewall_rules"

    id = Column(SQLAlchemyUUID, primary_key=True, default=uuid4)
    rule_collection_name = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)
    action = Column(SQLAlchemyEnum(FirewallRuleAction), nullable=False)
    protocol = Column(SQLAlchemyEnum(FirewallProtocol), nullable=False)
    source_addresses = Column(Text, nullable=True)  # JSON string
    destination_fqdns = Column(Text, nullable=True)  # JSON string
    source_ip_groups = Column(Text, nullable=True)  # JSON string
    destination_ports = Column(Text, nullable=True)  # JSON string
    description = Column(Text, nullable=True)
    status = Column(SQLAlchemyEnum(FirewallRuleStatus), default=FirewallRuleStatus.Pending, nullable=False)
    workload_id = Column(SQLAlchemyUUID, ForeignKey("workloads.id"), nullable=True)
    azure_resource_id = Column(String(500), nullable=True)
    created_by = Column(SQLAlchemyUUID, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    workload = relationship("Workload", back_populates="rules")

    def __repr__(self):
        return f"<FirewallRule(name={self.rule_collection_name}, priority={self.priority})>"