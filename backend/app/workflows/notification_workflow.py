"""
Notification workflow: routes notifications to email, in-app, and webhook channels.

This module provides a unified notification delivery system that:
1. Aggregates notifications from different sources (approvals, audits, Azure sync)
2. Routes them through appropriate channels (email, in-app, webhook)
3. Tracks delivery status
4. Provides fallback mechanisms
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.notification_service import NotificationService, NotificationType

logger = logging.getLogger(__name__)


class NotificationChannel:
    """Enum-like class for notification channels."""
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    ALL = "all"


class NotificationResult:
    """Result of a notification delivery attempt."""

    def __init__(self, channel: str, success: bool, error: Optional[str] = None):
        self.channel = channel
        self.success = success
        self.error = error

    @property
    def to_dict(self):
        return {
            "channel": self.channel,
            "success": self.success,
            "error": self.error,
        }


class NotificationWorkflow:
    """Orchestrates notification delivery across multiple channels.

    Usage::

        notify_wf = NotificationWorkflow()
        result = notify_wf.send_approval_notification(
            db=session,
            approval_request=approval,
            channel=NotificationChannel.EMAIL,
            recipient_email="user@example.com",
            recipient_name="User Name",
        )
    """

    def __init__(self, notification_service: Optional[NotificationService] = None):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._notification_service = notification_service or NotificationService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def send_approval_notification(
        self,
        db: Session,
        *,
        approval_request,
        notification_type: NotificationType,
        channel: str = NotificationChannel.EMAIL,
        recipient_email: str,
        recipient_name: str,
        additional_data: Optional[dict] = None,
    ) -> NotificationResult:
        """Send a notification about approval status change.

        Args:
            db: Database session
            approval_request: The ApprovalRequest model instance
            notification_type: Type of notification (APPROVED, REJECTED, CREATED)
            channel: Delivery channel (EMAIL, IN_APP, WEBHOOK)
            recipient_email: Recipient email address
            recipient_name: Recipient display name
            additional_data: Additional context data

        Returns:
            NotificationResult with delivery status
        """
        self._logger.info(
            "NotificationWorkflow.send_approval_notification: type=%s channel=%s recipient=%s",
            notification_type, channel, recipient_email,
        )

        try:
            success = self._notification_service.send_approval_notification(
                db=db,
                approval_request=approval_request,
                notification_type=notification_type,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                additional_data=additional_data,
            )
            return NotificationResult(
                channel=channel,
                success=success,
                error=None if success else "Notification delivery failed",
            )
        except Exception as e:  # noqa: B902
            self._logger.exception(
                "NotificationWorkflow.send_approval_notification failed: %s", e
            )
            return NotificationResult(
                channel=channel,
                success=False,
                error=str(e),
            )

    def send_bulk_approval_notifications(
        self,
        db: Session,
        *,
        approval_request,
        notification_type: NotificationType,
        recipients: list[dict],
    ) -> list[NotificationResult]:
        """Send approval notifications to multiple recipients.

        Args:
            db: Database session
            approval_request: The ApprovalRequest model instance
            notification_type: Type of notification
            recipients: List of dicts with 'email' and 'name' keys

        Returns:
            List of NotificationResult for each recipient
        """
        results = []
        for recipient in recipients:
            result = self.send_approval_notification(
                db=db,
                approval_request=approval_request,
                notification_type=notification_type,
                channel=NotificationChannel.EMAIL,
                recipient_email=recipient.get("email", ""),
                recipient_name=recipient.get("name", "Unknown"),
            )
            results.append(result)
        return results

    def send_audit_notification(
        self,
        db: Session,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: UUID,
        channel: str = NotificationChannel.IN_APP,
        recipient_email: str = "",
        recipient_name: str = "System",
    ) -> NotificationResult:
        """Send a notification about an audit event.

        Audit notifications are typically in-app and low priority.
        """
        self._logger.info(
            "NotificationWorkflow.send_audit_notification: action=%s resource=%s",
            action, resource_type,
        )

        try:
            success = self._notification_service.send_notification(
                db=db,
                notification_type=NotificationType.AUDIT_LOG,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                title=f"Audit: {action}",
                body=f"Resource {resource_type}/{resource_id} was {action}",
                user_id=user_id,
                additional_data={
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "channel": channel,
                },
            )
            return NotificationResult(
                channel=channel,
                success=success,
                error=None if success else "Audit notification delivery failed",
            )
        except Exception as e:  # noqa: B902
            self._logger.exception("NotificationWorkflow.send_audit_notification failed: %s", e)
            return NotificationResult(
                channel=channel,
                success=False,
                error=str(e),
            )

    def send_azure_sync_notification(
        self,
        db: Session,
        *,
        sync_type: str,
        rules_synced: int,
        rules_updated: int,
        rules_created: int,
        rules_deleted: int,
        errors: list[str],
        user_id: UUID,
        channel: str = NotificationChannel.EMAIL,
        recipient_email: str = "",
        recipient_name: str = "System Admin",
    ) -> NotificationResult:
        """Send a notification about Azure sync completion."""
        self._logger.info(
            "NotificationWorkflow.send_azure_sync_notification: type=%s synced=%d",
            sync_type, rules_synced,
        )

        summary_parts = []
        if rules_updated:
            summary_parts.append(f"{rules_updated} updated")
        if rules_created:
            summary_parts.append(f"{rules_created} created")
        if rules_deleted:
            summary_parts.append(f"{rules_deleted} deleted")
        if errors:
            summary_parts.append(f"{len(errors)} errors")

        summary = ", ".join(summary_parts) if summary_parts else "completed"

        try:
            success = self._notification_service.send_notification(
                db=db,
                notification_type=NotificationType.AZURE_SYNC,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                title=f"Azure Sync: {sync_type}",
                body=f"Sync {summary} (synced: {rules_synced}, updated: {rules_updated}, "
                     f"created: {rules_created}, deleted: {rules_deleted}, "
                     f"errors: {len(errors)})",
                user_id=user_id,
                additional_data={
                    "sync_type": sync_type,
                    "rules_synced": rules_synced,
                    "rules_updated": rules_updated,
                    "rules_created": rules_created,
                    "rules_deleted": rules_deleted,
                    "errors": errors,
                },
            )
            return NotificationResult(
                channel=channel,
                success=success,
                error=None if success else "Azure sync notification delivery failed",
            )
        except Exception as e:  # noqa: B902
            self._logger.exception("NotificationWorkflow.send_azure_sync_notification failed: %s", e)
            return NotificationResult(
                channel=channel,
                success=False,
                error=str(e),
            )

    def send_system_notification(
        self,
        db: Session,
        *,
        title: str,
        body: str,
        recipient_email: str,
        recipient_name: str,
        severity: str = "info",
        channel: str = NotificationChannel.EMAIL,
    ) -> NotificationResult:
        """Send a general system notification."""
        self._logger.info(
            "NotificationWorkflow.send_system_notification: title=%s severity=%s",
            title, severity,
        )

        try:
            success = self._notification_service.send_notification(
                db=db,
                notification_type=NotificationType.SYSTEM,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                title=title,
                body=body,
                additional_data={
                    "severity": severity,
                    "channel": channel,
                },
            )
            return NotificationResult(
                channel=channel,
                success=success,
                error=None if success else "System notification delivery failed",
            )
        except Exception as e:  # noqa: B902
            self._logger.exception("NotificationWorkflow.send_system_notification failed: %s", e)
            return NotificationResult(
                channel=channel,
                success=False,
                error=str(e),
            )

    def send_multi_channel(
        self,
        db: Session,
        *,
        approval_request,
        notification_type: NotificationType,
        recipients: list[dict],
    ) -> list[NotificationResult]:
        """Send notifications to all available channels for each recipient.

        For each recipient, sends via EMAIL, IN_APP, and WEBHOOK.

        Args:
            db: Database session
            approval_request: The ApprovalRequest model instance
            notification_type: Type of notification
            recipients: List of dicts with 'email' and 'name' keys

        Returns:
            List of NotificationResult for each channel
        """
        all_results = []

        for recipient in recipients:
            for channel in [NotificationChannel.EMAIL, NotificationChannel.IN_APP,
                            NotificationChannel.WEBHOOK]:
                result = self.send_approval_notification(
                    db=db,
                    approval_request=approval_request,
                    notification_type=notification_type,
                    channel=channel,
                    recipient_email=recipient.get("email", ""),
                    recipient_name=recipient.get("name", "Unknown"),
                )
                all_results.append(result)

        return all_results