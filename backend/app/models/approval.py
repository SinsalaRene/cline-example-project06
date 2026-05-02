"""
Database models for Approval Workflows.

This module contains SQLAlchemy models that are compatible with both
SQLite (development) and PostgreSQL (production) databases.

Cross-database compatibility:
- Uses UUID (String) for primary keys instead of PostgreSQL-specific UUID type
- Uses Text for JSON arrays instead of ARRAY/JSONB
- Uses String type for enum storage
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    func,
    Table,
    MetaData,
)
from sqlalchemy.orm import relationship, declarative_base

from app.models.firewall_rule import Base, UUID

# Association table for many-to-many between ApprovalRequest and FirewallRule
approval_rule_associations = Table(
    "approval_rule_associations",
    Base.metadata,
    Column("id", UUID, primary_key=True, default=uuid.uuid4),
    Column("approval_request_id", UUID, ForeignKey("approval_requests.id"), nullable=False),
    Column("firewall_rule_id", UUID, ForeignKey("firewall_rules.id"), nullable=False),
)

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.firewall_rule import Workload


class ChangeType(str, PyEnum):
    """Type of change for approval requests."""
    Create = "create"
    Update = "update"
    Delete = "delete"

    @classmethod
    def _missing_(cls, value):
        value_normalized = str(value).strip().lower() if value else value
        for member in cls:
            if member.value == value_normalized:
                return member
        return None


class ApprovalStatus(str, PyEnum):
    """Status states for approval requests."""
    Pending = "pending"
    Approved = "approved"
    Rejected = "rejected"
    Revoked = "revoked"
    Expired = "expired"

    @classmethod
    def _missing_(cls, value):
        value_normalized = str(value).strip().lower() if value else value
        for member in cls:
            if member.value == value_normalized:
                return member
        return None


class ApprovalRole(str, PyEnum):
    """Role types for approval workflow."""
    WorkloadStakeholder = "workload_stakeholder"
    SecurityStakeholder = "security_stakeholder"

    @classmethod
    def _missing_(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
            # Also try matching against the member name (e.g., "SecurityStakeholder" -> "SecurityStakeholder")
            if member.name == value or member.name.lower() == value_lower:
                return member
        return None


def _utc_now_server_default():
    """Return current UTC datetime for server_default."""
    return datetime.now(datetime.timezone.utc)


class ApprovalRequest(Base):
    """Approval request model for firewall rule changes.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key and foreign keys.
    Uses Text columns for array data for cross-database compatibility.
    """

    __tablename__ = "approval_requests"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    rule_ids = Column(Text, nullable=False)  # JSON array string
    change_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    current_user_id = Column(UUID, ForeignKey("users.id"), nullable=True)

    status = Column(String(50), default=ApprovalStatus.Pending.value, nullable=False)
    workload_id = Column(UUID, ForeignKey("workloads.id"), nullable=True)

    required_approvals = Column(Integer, default=2)
    current_approval_stage = Column(Integer, default=0)
    approval_flow = Column(String(50), default="multi_level")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    approval_steps = relationship("ApprovalStep", back_populates="approval_request", cascade="all, delete-orphan")
    comments = relationship("ApprovalComment", back_populates="approval_request", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="approval_request_ref")
    rules = relationship("FirewallRule", secondary="approval_rule_associations", viewonly=True)
    workload_obj = relationship("Workload", back_populates="approval_requests", foreign_keys=[workload_id])
    creator = relationship("User", foreign_keys=[current_user_id], back_populates="approval_requests_created")

    def __repr__(self):
        return f"<ApprovalRequest(id={self.id}, status={self.status})>"


class ApprovalStep(Base):
    """Individual step in an approval workflow.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key and foreign keys.
    """

    __tablename__ = "approval_steps"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    approval_request_id = Column(UUID, ForeignKey("approval_requests.id"), nullable=False)
    approver_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    approver_role = Column(String(50), nullable=False)

    status = Column(String(50), default=ApprovalStatus.Pending.value, nullable=False)
    comments = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    approval_request = relationship("ApprovalRequest", back_populates="approval_steps")
    approver = relationship("User", foreign_keys=[approver_id], back_populates="approved_steps")


class ApprovalWorkflowDefinition(Base):
    """Workflow definition for different workload types.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key.
    """

    __tablename__ = "approval_workflow_definitions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    trigger_conditions = Column(Text, nullable=True)  # JSON string
    required_roles = Column(Text, nullable=False)  # JSON array string
    timeout_hours = Column(Integer, default=48)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ApprovalComment(Base):
    """Comment model for approval requests.

    Allows users to add comments to approval requests for audit trail.
    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key and foreign keys.
    """

    __tablename__ = "approval_comments"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    approval_request_id = Column(UUID, ForeignKey("approval_requests.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    approval_request = relationship("ApprovalRequest", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id], back_populates="approval_comments")

    def __repr__(self):
        return f"<ApprovalComment(id={self.id}, approval_request_id={self.approval_request_id})>"
