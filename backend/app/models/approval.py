"""
Database models for Approval Workflows.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, list

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import Enum as SAEnum

Base = declarative_base()


class ChangeType(str, Enum):
    Create = "create"
    Update = "update"
    Delete = "delete"


class ApprovalStatus(str, Enum):
    Pending = "pending"
    Approved = "approved"
    Rejected = "rejected"
    Revoked = "revoked"
    Expired = "expired"


class ApprovalRole(str, Enum):
    WorkloadStakeholder = "workload_stakeholder"
    SecurityStakeholder = "security_stakeholder"


class ApprovalRequest(Base):
    """Approval request model for firewall rule changes."""
    __tablename__ = "approval_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_ids = Column(ARRAY(PG_UUID(as_uuid=True)), nullable=False)
    change_type = Column(SAEnum(ChangeType), nullable=False)
    description = Column(Text, nullable=True)
    current_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    status = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.Pending)
    workload_id = Column(PG_UUID(as_uuid=True), ForeignKey("workloads.id"), nullable=True)

    required_approvals = Column(Integer, default=2)
    current_approval_stage = Column(Integer, default=0)
    approval_flow = Column(String(50), default="multi_level")

    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    approval_steps = relationship("ApprovalStep", back_populates="approval_request")
    audit_logs = relationship("AuditLog", back_populates="approval_request_ref")
    rules = relationship("FirewallRule", back_populates="approval_requests")
    workload_obj = relationship("Workload", back_populates="approval_requests")
    creator = relationship("User", foreign_keys=[current_user_id])

    def __repr__(self):
        return f"<ApprovalRequest(id={self.id}, status={self.status})>"


class ApprovalStep(Base):
    """Individual step in an approval workflow."""
    __tablename__ = "approval_steps"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False)
    approver_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approver_role = Column(SAEnum(ApprovalRole), nullable=False)

    status = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.Pending)
    comments = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    approval_request = relationship("ApprovalRequest", back_populates="approval_steps")
    approver = relationship("User", foreign_keys=[approver_id])


class ApprovalWorkflowDefinition(Base):
    """Workflow definition for different workload types."""
    __tablename__ = "approval_workflow_definitions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    trigger_conditions = Column(JSONB, nullable=True)
    required_roles = Column(ARRAY(String), nullable=False)
    timeout_hours = Column(Integer, default=48)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())