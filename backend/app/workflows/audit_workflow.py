"""
Audit workflow: ensures every API operation is logged in the audit trail.

This module provides automatic audit logging for all API operations,
including firewall rules, approvals, authentication, and system events.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AuditWorkflow:
    """Orchestrates audit logging across all modules.

    Every API operation that modifies state should go through this workflow
    to ensure consistent audit trail coverage.

    Usage::

        audit_wf = AuditWorkflow()
        audit_wf.log_api_operation(
            db=session,
            user_id=user_uuid,
            action="update",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value={"old_name": "old"},
            new_value={"new_name": "new"},
        )
    """

    def __init__(self, audit_service: Optional[AuditService] = None):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._audit_service = audit_service or AuditService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def log_api_operation(
        self,
        db: Session,
        *,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Log a generic API operation to the audit trail.

        Returns True if the audit entry was written successfully.
        """
        try:
            self._audit_service.log_action(
                db=db,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                old_value=old_value,
                new_value=new_value,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return True
        except Exception:  # noqa: B902
            self._logger.exception(
                "AuditWorkflow.log_api_operation failed: action=%s resource=%s",
                action, resource_id,
            )
            return False

    def log_firewall_rule_created(
        self,
        db: Session,
        *,
        user_id: UUID,
        rule_id: UUID,
        rule_data: dict,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log firewall rule creation."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="create",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            new_value={**rule_data, "action": "create"},
            metadata={"correlation_id": correlation_id},
        )

    def log_firewall_rule_updated(
        self,
        db: Session,
        *,
        user_id: UUID,
        rule_id: UUID,
        old_data: dict,
        new_data: dict,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log firewall rule update."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="update",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value=old_data,
            new_value={**new_data, "action": "update"},
            metadata={"correlation_id": correlation_id},
        )

    def log_firewall_rule_deleted(
        self,
        db: Session,
        *,
        user_id: UUID,
        rule_id: UUID,
        old_data: dict,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log firewall rule deletion."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="delete",
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value=old_data,
            new_value={"action": "delete"},
            metadata={"correlation_id": correlation_id},
        )

    def log_firewall_rule_cloned(
        self,
        db: Session,
        *,
        user_id: UUID,
        source_rule_id: UUID,
        cloned_rule_id: UUID,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log firewall rule cloning."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="clone",
            resource_type="firewall_rule",
            resource_id=str(cloned_rule_id),
            old_value={"source_rule_id": str(source_rule_id)},
            new_value={"action": "clone", "cloned_to": str(cloned_rule_id)},
            metadata={"correlation_id": correlation_id},
        )

    def log_approval_created(
        self,
        db: Session,
        *,
        user_id: UUID,
        approval_id: UUID,
        change_type: str,
        rule_ids: list[str],
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log approval request creation."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="create_approval",
            resource_type="approval_request",
            resource_id=str(approval_id),
            new_value={
                "change_type": change_type,
                "rule_count": len(rule_ids),
                "rule_ids": rule_ids,
            },
            metadata={"correlation_id": correlation_id},
        )

    def log_approval_approved(
        self,
        db: Session,
        *,
        user_id: UUID,
        approval_id: UUID,
        comment: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log approval approval."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="approve",
            resource_type="approval_request",
            resource_id=str(approval_id),
            new_value={
                "status": "approved",
                "comment": comment,
            },
            metadata={"correlation_id": correlation_id},
        )

    def log_approval_rejected(
        self,
        db: Session,
        *,
        user_id: UUID,
        approval_id: UUID,
        comment: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log approval rejection."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="reject",
            resource_type="approval_request",
            resource_id=str(approval_id),
            new_value={
                "status": "rejected",
                "comment": comment,
            },
            metadata={"correlation_id": correlation_id},
        )

    def log_bulk_operation(
        self,
        db: Session,
        *,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_ids: list[str],
        count: int,
        metadata: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Log bulk operation."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id="bulk",
            new_value={
                "resource_count": count,
                "resource_ids": resource_ids,
            },
            metadata={**{"correlation_id": correlation_id}, **(metadata or {})},
        )

    def log_notification_sent(
        self,
        db: Session,
        *,
        user_id: UUID,
        notification_type: str,
        recipient_email: str,
        resource_id: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Log notification delivery."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="notification_sent",
            resource_type="notification",
            resource_id=resource_id,
            new_value={
                "type": notification_type,
                "recipient": recipient_email,
            },
            metadata=metadata,
        )

    def log_azure_sync(
        self,
        db: Session,
        *,
        user_id: UUID,
        sync_type: str,
        rules_synced: int,
        rules_updated: int,
        rules_created: int,
        rules_deleted: int,
        errors: list[str],
    ) -> bool:
        """Log Azure sync operation."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action="azure_sync",
            resource_type="azure_integration",
            resource_id="sync",
            new_value={
                "sync_type": sync_type,
                "rules_synced": rules_synced,
                "rules_updated": rules_updated,
                "rules_created": rules_created,
                "rules_deleted": rules_deleted,
                "errors": errors,
            },
        )

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------
    def log_bulk_api_operation(
        self,
        db: Session,
        *,
        user_id: UUID,
        action: str,
        resource_type: str,
        items: list[dict],
        errors: list[dict],
    ) -> bool:
        """Log a bulk API operation with success/failure details."""
        return self.log_api_operation(
            db=db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=f"bulk_{len(items)}",
            new_value={
                "items_processed": len(items),
                "success_count": len(items) - len(errors),
                "error_count": len(errors),
                "items": items,
            },
            metadata={"errors": errors},
        )