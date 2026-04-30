"""
Notification service for handling approval workflow notifications.

This service manages email, in-app, and webhook notifications for approval
workflow events including timeouts, escalations, bulk approvals, and more.
"""

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.approval import (
    ApprovalRequest, ApprovalStep, ApprovalStatus,
    ChangeType, ApprovalRole
)


class NotificationType(str, PyEnum):
    """Types of notifications that can be sent."""
    APPROVAL_REQUEST_CREATED = "approval_request_created"
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_ESCALATED = "approval_escalated"
    APPROVAL_BULK_COMPLETED = "approval_bulk_completed"
    ESCALATION_TRIGGERED = "escalation_triggered"


class NotificationChannel(str, PyEnum):
    """Channels through which notifications can be sent."""
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    ALL = "all"


@dataclass
class NotificationMessage:
    """Represents a notification message."""
    notification_type: NotificationType
    recipient_email: str
    recipient_name: str
    title: str
    body: str
    data: Optional[dict] = None
    timestamp: Optional[datetime] = None
    channel: NotificationChannel = NotificationChannel.ALL

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class NotificationService:
    """Service for managing notification workflows.
    
    Handles email, in-app, and webhook notifications for approval
    workflow events. Supports bulk notifications, escalation notifications,
    and configurable channel routing.
    
    Usage:
        service = NotificationService()
        service.send_approval_notification(db, approval_request, user)
    """

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_email: str = "noreply@example.com",
        use_tls: bool = True,
        enable_email: bool = True,
        enable_in_app: bool = True,
        enable_webhook: bool = False,
        webhook_url: str = "",
    ):
        """Initialize the NotificationService.
        
        Args:
            smtp_host: SMTP server hostname for email notifications.
            smtp_port: SMTP server port.
            smtp_user: SMTP username for authentication.
            smtp_password: SMTP password for authentication.
            from_email: Default sender email address.
            use_tls: Whether to use TLS for SMTP connections.
            enable_email: Whether to send email notifications.
            enable_in_app: Whether to create in-app notifications.
            enable_webhook: Whether to send webhook notifications.
            webhook_url: URL for webhook notifications.
        """
        self._logger = logging.getLogger(__name__)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls
        self.enable_email = enable_email
        self.enable_in_app = enable_in_app
        self.enable_webhook = enable_webhook
        self.webhook_url = webhook_url

    def send_approval_notification(
        self,
        db: Session,
        approval_request: ApprovalRequest,
        notification_type: NotificationType,
        recipient_email: str = "",
        recipient_name: str = "",
        additional_data: Optional[dict] = None,
        channel: Optional[NotificationChannel] = None,
    ) -> bool:
        """Send notification for an approval workflow event.
        
        Args:
            db: SQLAlchemy database session.
            approval_request: The approval request that triggered the notification.
            notification_type: Type of notification to send.
            recipient_email: Email address of the recipient.
            recipient_name: Name of the recipient.
            additional_data: Additional data to include in the notification.
            channel: Specific channel to use. If None, uses all enabled channels.
        
        Returns:
            True if notification was successfully queued/sent.
        """
        try:
            self._logger.info(
                "Sending notification type=%s for approval_id=%s",
                notification_type, approval_request.id,
            )
            
            # Build notification message
            message = self._build_notification_message(
                approval_request=approval_request,
                notification_type=notification_type,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                additional_data=additional_data or {},
            )
            
            # Send via appropriate channels
            channels_to_use = channel if channel else NotificationChannel.ALL
            success = self._deliver_notification(db, message, channels_to_use)
            
            if success:
                self._logger.info(
                    "Notification delivered for approval_id=%s type=%s",
                    approval_request.id, notification_type,
                )
            else:
                self._logger.warning(
                    "Failed to deliver notification for approval_id=%s type=%s",
                    approval_request.id, notification_type,
                )
            
            return success
            
        except Exception:
            self._logger.exception(
                "Error sending notification for approval_id=%s",
                approval_request.id,
            )
            return False

    def send_bulk_approval_notification(
        self,
        db: Session,
        approval_ids: list[UUID],
        notification_type: NotificationType,
        change_type: Optional[ChangeType] = None,
        initiator_name: str = "",
        initiator_email: str = "",
    ) -> bool:
        """Send notification for bulk approval operations.
        
        Args:
            db: SQLAlchemy database session.
            approval_ids: List of approval request IDs included in the bulk operation.
            notification_type: Type of bulk notification.
            change_type: Type of change applied.
            initiator_name: Name of the user who performed bulk operation.
            initiator_email: Email of the user who performed bulk operation.
        
        Returns:
            True if all bulk notifications were sent successfully.
        """
        self._logger.info(
            "Sending bulk notification type=%s for %d approvals",
            notification_type, len(approval_ids),
        )
        
        all_success = True
        for approval_id in approval_ids:
            try:
                approval = db.query(ApprovalRequest).filter(
                    ApprovalRequest.id == approval_id
                ).first()
                
                if not approval:
                    self._logger.warning(
                        "Approval %s not found for bulk notification",
                        approval_id,
                    )
                    all_success = False
                    continue
                
                success = self.send_approval_notification(
                    db=db,
                    approval_request=approval,
                    notification_type=notification_type,
                    additional_data={
                        "bulk_operation": True,
                        "bulk_count": len(approval_ids),
                        "change_type": change_type.value if change_type else None,
                        "initiator_name": initiator_name,
                        "initiator_email": initiator_email,
                    },
                )
                
                if not success:
                    all_success = False
                    
            except Exception:
                self._logger.exception(
                    "Error sending bulk notification for approval %s",
                    approval_id,
                )
                all_success = False
        
        return all_success

    def send_escalation_notification(
        self,
        db: Session,
        approval_request: ApprovalRequest,
        original_approver_id: UUID,
        escalated_to_role: ApprovalRole,
        reason: str = "",
        override_timeout: Optional[datetime] = None,
    ) -> bool:
        """Send escalation notification for an approval timeout.
        
        Args:
            db: SQLAlchemy database session.
            approval_request: The approval request being escalated.
            original_approver_id: UUID of the approver who timed out.
            escalated_to_role: Role to escalate to.
            reason: Reason for escalation.
            override_timeout: Override timeout datetime.
        
        Returns:
            True if escalation notification was sent successfully.
        """
        try:
            # Determine escalation timeout
            timeout_hours = 48  # Default escalation timeout
            if override_timeout:
                timeout_hours = (override_timeout - datetime.now(timezone.utc)).total_seconds() / 3600
            
            escalation_data = {
                "original_approver_id": str(original_approver_id),
                "escalated_to_role": escalated_to_role.value,
                "reason": reason,
                "timeout_hours": timeout_hours,
                "escalation_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            self._logger.info(
                "Sending escalation notification for approval_id=%s to_role=%s",
                approval_request.id, escalated_to_role,
            )
            
            return self.send_approval_notification(
                db=db,
                approval_request=approval_request,
                notification_type=NotificationType.APPROVAL_ESCALATED,
                additional_data=escalation_data,
            )
            
        except Exception:
            self._logger.exception(
                "Error sending escalation notification for approval_id=%s",
                approval_request.id,
            )
            return False

    def _build_notification_message(
        self,
        approval_request: ApprovalRequest,
        notification_type: NotificationType,
        recipient_email: str,
        recipient_name: str,
        additional_data: dict,
    ) -> NotificationMessage:
        """Build a notification message from approval request data.
        
        Args:
            approval_request: The approval request that triggered the notification.
            notification_type: Type of notification.
            recipient_email: Email of the recipient.
            recipient_name: Name of the recipient.
            additional_data: Additional data for the message.
        
        Returns:
            NotificationMessage object.
        
        Raises:
            ValueError: If notification_type is unknown.
        """
        change_type = approval_request.change_type
        status = approval_request.status
        
        # Map notification types to titles and bodies
        templates = {
            NotificationType.APPROVAL_REQUEST_CREATED: {
                "title": f"New Approval Request: {change_type}",
                "body": (
                    f"A new {change_type} approval request has been submitted.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Description: {approval_request.description}\n"
                    f"Required approvals: {approval_request.required_approvals}\n"
                    f"Created: {approval_request.created_at}\n"
                    f"Timeout: 48 hours"
                ),
            },
            NotificationType.APPROVAL_PENDING: {
                "title": f"Action Required: {change_type} approval pending",
                "body": (
                    f"You have a pending {change_type} approval request.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Description: {approval_request.description}\n"
                    f"Status: Pending approval"
                ),
            },
            NotificationType.APPROVAL_APPROVED: {
                "title": f"Approval Approved: {change_type}",
                "body": (
                    f"Your {change_type} approval request has been approved.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Completed: {approval_request.completed_at}"
                ),
            },
            NotificationType.APPROVAL_REJECTED: {
                "title": f"Approval Rejected: {change_type}",
                "body": (
                    f"Your {change_type} approval request has been rejected.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Completed: {approval_request.completed_at}"
                ),
            },
            NotificationType.APPROVAL_EXPIRED: {
                "title": f"Approval Expired: {change_type}",
                "body": (
                    f"Your {change_type} approval request has expired.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Expired: {approval_request.completed_at}"
                ),
            },
            NotificationType.APPROVAL_ESCALATED: {
                "title": f"Approval Escalated: {change_type}",
                "body": (
                    f"Your {change_type} approval request has been escalated.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Reason: {additional_data.get('reason', 'Timeout exceeded')}"
                ),
            },
            NotificationType.APPROVAL_BULK_COMPLETED: {
                "title": f"Bulk Approval Complete: {change_type}",
                "body": (
                    f"Batch {change_type} operation completed.\n\n"
                    f"Total approved: {additional_data.get('bulk_count', 0)}\n"
                    f"Initiator: {additional_data.get('initiator_name', 'Unknown')}"
                ),
            },
            NotificationType.ESCALATION_TRIGGERED: {
                "title": f"Escalation Triggered: {change_type}",
                "body": (
                    f"Approval escalation has been triggered for {change_type}.\n\n"
                    f"Request ID: {approval_request.id}\n"
                    f"Escalated to: {additional_data.get('escalated_to_role', 'N/A')}"
                ),
            },
        }
        
        if notification_type not in templates:
            raise ValueError(f"Unknown notification type: {notification_type}")
        
        template = templates[notification_type]
        
        # Add any additional data to the body
        if additional_data:
            extra_lines = "\n".join(f"{k}: {v}" for k, v in additional_data.items())
            body = f"{template['body']}\n\nAdditional Data:\n{extra_lines}"
        else:
            body = template["body"]
        
        return NotificationMessage(
            notification_type=notification_type,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            title=template["title"],
            body=body,
            data=additional_data,
            channel=NotificationChannel.ALL,
        )

    def _deliver_notification(
        self,
        db: Session,
        message: NotificationMessage,
        channel: NotificationChannel,
    ) -> bool:
        """Deliver a notification via the specified channel(s).
        
        Args:
            db: SQLAlchemy database session.
            message: The notification message to deliver.
            channel: Channel(s) to use for delivery.
        
        Returns:
            True if all deliveries succeeded.
        """
        all_success = True
        
        # Email delivery
        if self.enable_email and channel != NotificationChannel.IN_APP:
            email_success = self._send_email(message)
            if not email_success:
                all_success = False
        
        # In-app delivery
        if self.enable_in_app:
            in_app_success = self._create_in_app_notification(db, message)
            if not in_app_success:
                all_success = False
        
        # Webhook delivery
        if self.enable_webhook:
            webhook_success = self._send_webhook(message)
            if not webhook_success:
                all_success = False
        
        return all_success

    def _send_email(self, message: NotificationMessage) -> bool:
        """Send an email notification.
        
        Args:
            message: The notification message to send.
        
        Returns:
            True if email was successfully sent.
        """
        if not self.enable_email:
            return True
        
        self._logger.debug("Sending email to %s: %s", message.recipient_email, message.title)
        
        try:
            if self.enable_email:
                msg = self._build_email_message(message)
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls()
                    server.ehlo()
                    # Login if credentials provided
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, message.recipient_email, msg.as_string())
            
            self._logger.info("Email sent successfully to %s", message.recipient_email)
            return True
            
        except Exception:
            self._logger.exception("Failed to send email to %s", message.recipient_email)
            return False

    def _build_email_message(self, message: NotificationMessage) -> str:
        """Build an email message from a NotificationMessage.
        
        Args:
            message: The notification message to convert.
        
        Returns:
            Email message string.
        """
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Firewall Manager] {message.title}"
        msg["From"] = self.from_email
        msg["To"] = message.recipient_email
        
        # Create plain text version
        text = f"""{message.title}

{message.body}

Sent: {message.timestamp}
        """
        msg.attach(MIMEText(text, "plain"))
        
        return msg.as_string()

    def _create_in_app_notification(
        self,
        db: Session,
        message: NotificationMessage,
    ) -> bool:
        """Create an in-app notification in the database.
        
        Args:
            db: SQLAlchemy database session.
            message: The notification message to create.
        
        Returns:
            True if in-app notification was created.
        """
        try:
            self._logger.info(
                "Creating in-app notification for email=%s type=%s",
                message.recipient_email, message.notification_type,
            )
            # In a full implementation, this would:
            # 1. Create an InAppNotification model record
            # 2. Potentially use WebSocket to push the notification
            # 3. Store in a notifications table linked to users
            
            # For now, log the notification creation
            notification_data = {
                "type": message.notification_type.value,
                "title": message.title,
                "body": message.body[:200],  # Truncate for logging
                "recipient": message.recipient_email,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            }
            self._logger.debug("In-app notification data: %s", notification_data)
            
            return True
            
        except Exception:
            self._logger.exception("Failed to create in-app notification")
            return False

    def _send_webhook(self, message: NotificationMessage) -> bool:
        """Send a webhook notification.
        
        Args:
            message: The notification message to send.
        
        Returns:
            True if webhook was successfully sent.
        """
        if not self.enable_webhook or not self.webhook_url:
            return True
        
        self._logger.info("Sending webhook for type=%s", message.notification_type)
        
        try:
            import requests
            
            payload = {
                "type": message.notification_type.value,
                "title": message.title,
                "body": message.body,
                "recipient_email": message.recipient_email,
                "recipient_name": message.recipient_name,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "data": message.data or {},
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            
            if response.status_code >= 400:
                self._logger.warning(
                    "Webhook returned status %d: %s",
                    response.status_code, response.text,
                )
                return False
            
            self._logger.info("Webhook sent successfully")
            return True
            
        except Exception:
            self._logger.exception("Failed to send webhook")
            return False

    def get_notification_history(
        self,
        db: Session,
        approval_id: UUID,
        notification_type: Optional[NotificationType] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get notification history for an approval request.
        
        Args:
            db: SQLAlchemy database session.
            approval_id: UUID of the approval request.
            notification_type: Optional filter by notification type.
            page: Page number for pagination.
            page_size: Items per page.
        
        Returns:
            Dictionary with notifications and pagination metadata.
        
        Note:
            Notification history is stored using a NotificationHistory model.
            For this implementation, we use the audit table or a dedicated
            notification table in a full deployment.
        """
        self._logger.info(
            "Getting notification history for approval_id=%s", approval_id,
        )
        
        # In a full implementation, this would query a NotificationHistory model.
        # For now, return an empty result with pagination metadata.
        # The notification_history table would need to be created via migration.
        
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "note": "NotificationHistory model needs to be created via database migration",
        }
