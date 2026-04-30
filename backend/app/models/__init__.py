"""
Database models package.

This package contains all SQLAlchemy models for the application.
Models are compatible with both SQLite (development) and PostgreSQL (production).

Modules:
- firewall_rule: Workload and FirewallRule models
- approval: ApprovalRequest, ApprovalStep, ApprovalWorkflowDefinition models
- audit: AuditLog, User, UserRole models
"""

# Import Base from firewall_rule (it's the first module loaded)
from app.models.firewall_rule import (
    Base,
    Workload,
    FirewallRule,
    FirewallRuleAction,
    FirewallProtocol,
    FirewallRuleStatus,
)

# Import approval models
from app.models.approval import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflowDefinition,
    ChangeType,
    ApprovalStatus,
    ApprovalRole,
)

# Import audit models
from app.models.audit import (
    AuditLog,
    User,
    UserRole,
    AuditAction,
)

__all__ = [
    # Base
    "Base",
    # Firewall rule models
    "Workload",
    "FirewallRule",
    "FirewallRuleAction",
    "FirewallProtocol",
    "FirewallRuleStatus",
    # Approval models
    "ApprovalRequest",
    "ApprovalStep",
    "ApprovalWorkflowDefinition",
    "ChangeType",
    "ApprovalStatus",
    "ApprovalRole",
    # Audit models
    "AuditLog",
    "User",
    "UserRole",
    "AuditAction",
]