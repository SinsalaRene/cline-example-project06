"""
Approval workflow: wires approval completion → rule application + notifications.

When an approval request transitions to a terminal state (Approved/Rejected),
this workflow:
1. Determines which firewall rules were affected
2. Applies the corresponding state changes (activate/ deactivate / update rules)
3. Triggers notifications to interested parties
4. Emits an audit event for the end-to-end chain
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.approval import ApprovalRequest, ApprovalStatus, ChangeType
from app.models.firewall_rule import FirewallRule, FirewallRuleStatus
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService, NotificationType

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """Orchestrates the chain: approval → rule application → notification → audit.

    Usage::

        wf = ApprovalWorkflow()
        wf.on_approval_completed(db, approval_request, user_id)
    """

    def __init__(self, audit_service: Optional[AuditService] = None,
                 notification_service: Optional[NotificationService] = None):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._audit_service = audit_service or AuditService()
        self._notification_service = notification_service or NotificationService()

    # ------------------------------------------------------------------
    # Public entry-points
    # ------------------------------------------------------------------
    def on_approval_completed(self, db: Session, approval_request: ApprovalRequest,
                               user_id: UUID) -> dict:
        """Callback executed after an approval reaches a terminal state.

        Applies rule changes for APPROVED, sends notifications, logs audit.
        Returns a summary dict.
        """
        self._logger.info(
            "ApprovalWorkflow.on_approval_completed: approval_id=%s status=%s user=%s",
            approval_request.id, approval_request.status, user_id,
        )

        result: dict = {
            "approval_id": str(approval_request.id),
            "status": approval_request.status.value,
            "rules_applied": 0,
            "notifications_sent": 0,
            "audit_logged": False,
        }

        if approval_request.status != ApprovalStatus.Approved:
            # Only apply rules on APPROVED; REJECTED leaves rules untouched
            self._logger.info(
                "Skipping rule application for non-APPROVED status: %s",
                approval_request.status.value,
            )
            result["rules_applied"] = 0
            return result

        rule_ids = self._parse_rule_ids(approval_request.rule_ids)
        if not rule_ids:
            self._logger.warning("No rule_ids parsed from approval %s", approval_request.id)
            return result

        # 1. Apply rule state changes
        rules_updated = self._apply_rules(db, rule_ids, approval_request)
        result["rules_applied"] = rules_updated

        # 2. Send notifications
        notifications_sent = self._dispatch_approval_notification(db, approval_request, user_id)
        result["notifications_sent"] = notifications_sent

        # 3. Audit log the chain
        try:
            self._audit_service.log_action(
                db=db,
                user_id=user_id,
                action="approval_rule_applied",
                resource_type="approval_request",
                resource_id=str(approval_request.id),
                old_value={"change_type": approval_request.change_type.value,
                            "rule_count": len(rule_ids)},
                new_value={"rules_updated": rules_updated,
                            "notification_count": notifications_sent},
            )
            result["audit_logged"] = True
        except Exception:  # noqa: B902
            self._logger.exception("Failed to write approval_rule_applied audit entry")

        return result

    def on_approval_created(self, db: Session, approval_request: ApprovalRequest,
                             user_id: UUID) -> dict:
        """Callback executed immediately after a new approval request is created.

        Sends initial notification and audit log.
        """
        self._logger.info("ApprovalWorkflow.on_approval_created: approval_id=%s user=%s",
                          approval_request.id, user_id)

        notifications_sent = self._dispatch_notification_for_creation(db, approval_request, user_id)

        try:
            self._audit_service.log_action(
                db=db,
                user_id=user_id,
                action="approval_created",
                resource_type="approval_request",
                resource_id=str(approval_request.id),
                new_value={"change_type": approval_request.change_type.value},
            )
        except Exception:  # noqa: B902
            self._logger.exception("Failed to write approval_created audit entry")

        return {
            "approval_id": str(approval_request.id),
            "notifications_sent": notifications_sent,
            "audit_logged": True,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_rule_ids(rule_ids_json_str: Optional[str]) -> list[UUID]:
        """Deserialize the rule_ids JSON string stored on the ApprovalRequest."""
        if not rule_ids_json_str:
            return []
        try:
            ids = json.loads(rule_ids_json_str)
            return [UUID(rid) for rid in ids]
        except (json.JSONDecodeError, ValueError):
            return []

    def _apply_rules(self, db: Session, rule_ids: list[UUID],
                     approval_request: ApprovalRequest) -> int:
        """Update matching firewall rules: activate if APPROVED, deactivate if REJECTED."""
        updated = 0
        for rule_id in rule_ids:
            try:
                rule = db.query(FirewallRule).filter(FirewallRule.id == rule_id).first()
                if not rule:
                    self._logger.warning("Rule %s not found; skipping", rule_id)
                    continue

                if approval_request.status == ApprovalStatus.Approved:
                    # Activate rules that are Pending
                    if rule.status == FirewallRuleStatus.Pending:
                        rule.status = FirewallRuleStatus.Active
                elif approval_request.status == ApprovalStatus.Rejected:
                    if rule.status == FirewallRuleStatus.Pending:
                        rule.status = FirewallRuleStatus.Deleted

                rule.updated_at = datetime.now(timezone.utc)
                updated += 1

            except Exception:  # noqa: B902
                self._logger.exception("Failed to apply rules for rule_id=%s", rule_id)

        try:
            db.commit()
        except Exception:  # noqa: B902
            db.rollback()
            self._logger.exception("Failed to commit rule updates")

        self._logger.info("Applied rules for approval %s: updated=%d",
                          approval_request.id, updated)
        return updated

    def _dispatch_approval_notification(self, db: Session,
                                         approval_request: ApprovalRequest,
                                         user_id: UUID) -> int:
        """Send email/in-app/webhook for approval completion."""
        count = 0
        try:
            sent = self._notification_service.send_approval_notification(
                db=db,
                approval_request=approval_request,
                notification_type=(
                    NotificationType.APPROVAL_APPROVED
                    if approval_request.status == ApprovalStatus.Approved
                    else NotificationType.APPROVAL_REJECTED
                ),
                recipient_email="creator@example.com",  # resolved from user in production
                recipient_name="Approval Creator",
                additional_data={"applied_by": str(user_id)},
            )
            if sent:
                count += 1
        except Exception:  # noqa: B902
            self._logger.exception("Failed to send approval completion notification")
        return count

    def _dispatch_notification_for_creation(self, db: Session,
                                             approval_request: ApprovalRequest,
                                             user_id: UUID) -> int:
        """Send notification when a new approval request is created."""
        count = 0
        try:
            sent = self._notification_service.send_approval_notification(
                db=db,
                approval_request=approval_request,
                notification_type=NotificationType.APPROVAL_REQUEST_CREATED,
                recipient_email="reviewer@example.com",
                recipient_name="Reviewer",
                additional_data={"initiated_by": str(user_id)},
            )
            if sent:
                count += 1
        except Exception:  # noqa: B902
            self._logger.exception("Failed to send creation notification")
        return count