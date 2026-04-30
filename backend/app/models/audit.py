"""
Database models for Audit Logs and User/Roles.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, INET
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import func, Enum as SAEnum

Base = declarative_base()


class AuditAction(str, Enum):
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
    """Immutable audit log model."""
    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Text, nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(PG_UUID(as_uuid=True), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approval_request_ref = relationship("ApprovalRequest", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, timestamp={self.timestamp})>"


class User(Base):
    """User model synced from Entra ID."""
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    object_id = Column(String(36), unique=True, nullable=False, index=True)  # Entra ID object ID
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    given_name = Column(String(255), nullable=True)
    surname = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1)  # Boolean stored as integer for compatibility
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    owned_workloads = relationship("Workload", foreign_keys=[Workload.owner_id], back_populates="owner")
    assigned_roles = relationship("UserRole", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    approval_requests_created = relationship("ApprovalRequest", foreign_keys=[ApprovalRequest.current_user_id])
    approved_steps = relationship("ApprovalStep", foreign_keys=[ApprovalStep.approver_id])


class UserRole(Base):
    """User role assignment model."""
    __tablename__ = "user_roles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(100), nullable=False)  # owner, admin, developer, security_reader, network_admin
    workload_id = Column(PG_UUID(as_uuid=True), ForeignKey("workloads.id"), nullable=True)
    granted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="assigned_roles")
    workload = relationship("Workload", back_populates="user_roles")
    granter = relationship("User", foreign_keys=[granted_by])

    def __repr__(self):
        return f"<UserRole(id={self.id}, user_id={self.user_id}, role={self.role})>"


# Import Workload and ApprovalRequest here to reference them
from backend.app.models.firewall_rule import Workload
from backend.app.models.approval import ApprovalRequest