"""
Database models for Audit Logs and User/Roles.

This module contains SQLAlchemy models that are compatible with both
SQLite (development) and PostgreSQL (production) databases.

Cross-database compatibility:
- Uses UUID (String) for primary keys instead of PostgreSQL-specific UUID type
- Uses Text for JSON data instead of JSONB
- Uses String(45) for IP addresses instead of INET (supports IPv6 up to 45 chars)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship, declarative_base

from app.models.firewall_rule import Base, UUID

# Import models we need for relationships
import app.models.approval as approval_module


class AuditAction(str, PyEnum):
    """Types of audit actions."""
    Create = "create"
    Update = "update"
    Delete = "delete"
    Approve = "approve"
    Reject = "reject"
    Import = "import"
    Export = "export"
    Login = "login"
    CreateApproval = "create_approval"
    ApplyRule = "apply_rule"


class AuditLog(Base):
    """Immutable audit log model.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for primary key and foreign keys.
    Uses Text columns for old_value/new_value instead of JSONB.
    Uses String(45) for ip_address (supports IPv6 max length).
    """

    __tablename__ = "audit_logs"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    approval_request_id = Column(UUID, ForeignKey("approval_requests.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)  # JSON string (was JSONB)
    new_value = Column(Text, nullable=True)  # JSON string (was JSONB)
    ip_address = Column(String(45), nullable=True)  # VARCHAR(45) supports IPv6 max length
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(String(36), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approval_request_ref = relationship("ApprovalRequest", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, timestamp={self.timestamp})>"


class User(Base):
    """User model synced from Entra ID.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for cross-database compatibility.
    """

    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    object_id = Column(String(36), unique=True, nullable=False, index=True)  # Entra ID object ID
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    given_name = Column(String(255), nullable=True)
    surname = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)  # Proper boolean type
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    # Relationships - using string references to avoid circular imports
    owned_workloads = relationship("Workload", foreign_keys="[Workload.owner_id]", back_populates="owner")
    assigned_roles = relationship("UserRole", foreign_keys="[UserRole.user_id]", back_populates="user")
    granted_roles = relationship("UserRole", foreign_keys="[UserRole.granted_by]", back_populates="granter")
    audit_logs = relationship("AuditLog", back_populates="user")
    approval_requests_created = relationship(
        "ApprovalRequest", foreign_keys="[ApprovalRequest.current_user_id]", overlaps="creator"
    )
    approved_steps = relationship(
        "ApprovalStep", foreign_keys="[ApprovalStep.approver_id]", overlaps="approver, approval_comments"
    )
    approval_comments = relationship(
        "ApprovalComment", foreign_keys="[ApprovalComment.user_id]", back_populates="user"
    )


class UserRole(Base):
    """User role assignment model.

    Compatible with both SQLite and PostgreSQL databases.
    Uses UUID TypeDecorator for cross-database compatibility.
    """

    __tablename__ = "user_roles"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    role = Column(String(100), nullable=False)  # owner, admin, developer, security_reader, network_admin
    workload_id = Column(String(36), ForeignKey("workloads.id"), nullable=True)
    granted_by = Column(UUID, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="assigned_roles")
    workload = relationship("Workload", back_populates="user_roles")
    granter = relationship("User", foreign_keys=[granted_by], back_populates="granted_roles")

    def __repr__(self):
        return f"<UserRole(id={self.id}, user_id={self.user_id}, role={self.role})>"