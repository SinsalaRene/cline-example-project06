"""
Workflow module for cross-module integration.

This module provides workflow orchestration for approval-triggered rule changes,
audit logging on all operations, and notification delivery.

Workflows:
- ApprovalWorkflow: Wires approval completion to rule application and notifications.
- AuditWorkflow: Ensures every API operation is logged in the audit trail.
- NotificationWorkflow: Routes notifications to email, in-app, and webhook channels.
"""

from app.workflows.approval_workflow import ApprovalWorkflow
from app.workflows.audit_workflow import AuditWorkflow
from app.workflows.notification_workflow import (
    NotificationWorkflow,
    NotificationChannel,
    NotificationResult,
)

__all__ = [
    "ApprovalWorkflow",
    "AuditWorkflow",
    "NotificationWorkflow",
    "NotificationChannel",
    "NotificationResult",
]