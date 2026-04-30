"""
Audit service for tracking all changes and actions.

Refactored to use class-based dependency injection pattern for proper
FastAPI integration with dependency injection support.
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit trail management with dependency injection.

    This service provides comprehensive audit logging for all operations
    in the system, supporting filtering, search, and export.

    Usage in FastAPI:
        @app.post("/firewall-rules")
        def create_rule(data: RuleCreate, db: Session = Depends(get_db)):
            service = AuditService()
            rule = service.create_rule(db, data)
            service.log_action(db, "CREATE", "firewall_rule", rule.id, ...)
            return rule
    """

    def __init__(self, logger_name: str = __name__):
        """Initialize the AuditService."""
        self._logger = logging.getLogger(logger_name)
        self._logger.debug("AuditService initialized")

    def log_action(
        self,
        db: Session,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[UUID] = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            db: SQLAlchemy database session.
            user_id: UUID of the user performing the action.
            action: Action performed (CREATE/UPDATE/DELETE/etc.).
            resource_type: Type of resource (firewall_rule/approval/audit).
            resource_id: UUID of the resource being modified.
            old_value: Previous state before the action (as dict).
            new_value: New state after the action (as dict).
            ip_address: Optional IP address of the requester.
            user_agent: Optional user agent string.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            The created AuditLog object.

        Raises:
            Exception: Database commit or connection errors.
        """
        self._logger.info("log_action called: user=%s, action=%s, resource=%s/%s",
                          user_id, action, resource_type, resource_id)

        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=str(correlation_id) if correlation_id else None,
        )

        try:
            db.add(audit_entry)
            db.commit()
            db.refresh(audit_entry)
        except Exception:
            db.rollback()
            self._logger.exception("Failed to log audit action %s for resource %s/%s",
                                   action, resource_type, resource_id)
            raise

        self._logger.debug("Audit log entry %s created for action %s",
                          audit_entry.id, action)
        return audit_entry

    def log_firewall_rule_change(
        self,
        db: Session,
        user_id: UUID,
        action: str,
        rule_id: UUID,
        old_data: Optional[dict],
        new_data: Optional[dict],
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log a firewall rule change with convenience method.

        Args:
            db: SQLAlchemy database session.
            user_id: UUID of the user.
            action: Action performed (CREATE/UPDATE/DELETE).
            rule_id: UUID of the firewall rule.
            old_data: Previous state dict.
            new_data: New state dict.
            ip_address: Optional IP address.

        Returns:
            The created AuditLog object.
        """
        self._logger.info("log_firewall_rule_change: action=%s, rule=%s, user=%s",
                          action, rule_id, user_id)
        return self.log_action(
            db=db,
            user_id=user_id,
            action=action,
            resource_type="firewall_rule",
            resource_id=str(rule_id),
            old_value=old_data,
            new_value=new_data,
            ip_address=ip_address,
        )

    def log_approval_change(
        self,
        db: Session,
        user_id: UUID,
        action: str,
        approval_id: UUID,
        old_data: Optional[dict],
        new_data: Optional[dict],
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log an approval change with convenience method.

        Args:
            db: SQLAlchemy database session.
            user_id: UUID of the user.
            action: Action performed (APPROVE/REJECT/EXPIRE).
            approval_id: UUID of the approval request.
            old_data: Previous state dict.
            new_data: New state dict.
            ip_address: Optional IP address.

        Returns:
            The created AuditLog object.
        """
        self._logger.info("log_approval_change: action=%s, approval=%s, user=%s",
                          action, approval_id, user_id)
        return self.log_action(
            db=db,
            user_id=user_id,
            action=action,
            resource_type="approval",
            resource_id=str(approval_id),
            old_value=old_data,
            new_value=new_data,
            ip_address=ip_address,
        )

    def get_audit_logs(
        self,
        db: Session,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get audit logs with filtering and pagination.

        Args:
            db: SQLAlchemy database session.
            user_id: Optional UUID to filter by user.
            resource_type: Optional resource type to filter.
            action: Optional action to filter.
            start_date: Optional start date for filtering.
            end_date: Optional end date for filtering.
            page: Page number for pagination (1-based).
            page_size: Number of items per page.

        Returns:
            Dictionary containing paginated audit logs and metadata.
        """
        self._logger.info("get_audit_logs called - user=%s, resource_type=%s, action=%s",
                          user_id, resource_type, action)

        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if page_size < 1:
            raise ValueError(f"page_size must be >= 1, got {page_size}")

        query = db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if action:
            query = query.filter(AuditLog.action == action)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        total = query.count()
        self._logger.info("Found %d audit logs matching criteria", total)

        query = query.order_by(desc(AuditLog.timestamp))

        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()

        self._logger.debug("Returning %d items for page %d", len(items), page)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def get_audit_for_resource(
        self,
        db: Session,
        resource_type: str,
        resource_id: str,
    ) -> list:
        """Get audit logs for a specific resource.

        Args:
            db: SQLAlchemy database session.
            resource_type: Type of resource to query.
            resource_id: UUID of the resource.

        Returns:
            List of AuditLog objects for the resource.
        """
        self._logger.info("get_audit_for_resource called: type=%s, id=%s", resource_type, resource_id)

        logs = db.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        ).order_by(desc(AuditLog.timestamp)).all()

        self._logger.info("Found %d audit entries for %s/%s", len(logs), resource_type, resource_id)
        return logs

    def get_audit_for_user(
        self,
        db: Session,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list:
        """Get audit logs for a specific user within a date range.

        Args:
            db: SQLAlchemy database session.
            user_id: UUID of the user.
            start_date: Optional start date for filtering.
            end_date: Optional end date for filtering.

        Returns:
            List of AuditLog objects for the user.
        """
        self._logger.info("get_audit_for_user called for user %s", user_id)

        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        logs = query.order_by(desc(AuditLog.timestamp)).all()

        self._logger.info("Found %d audit entries for user %s", len(logs), user_id)
        return logs

    def export_audit_logs(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
    ) -> list[dict]:
        """Export audit logs as dictionaries for CSV/JSON export.

        Args:
            db: SQLAlchemy database session.
            start_date: Optional start date for filtering.
            end_date: Optional end date for filtering.
            resource_type: Optional resource type filter.
            action: Optional action filter.

        Returns:
            List of dicts containing audit log data (without SQLAlchemy objects).
        """
        self._logger.info("export_audit_logs called - resource_type=%s, action=%s",
                          resource_type, action)

        logs = self.get_audit_logs_filtered(db, start_date, end_date, resource_type, action)

        exported = []
        for log in logs:
            exported.append({
                "id": str(log.id),
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "old_value": json.loads(log.old_value) if log.old_value else None,
                "new_value": json.loads(log.new_value) if log.new_value else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "correlation_id": str(log.correlation_id) if log.correlation_id else None,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            })

        self._logger.info("Exported %d audit log entries", len(exported))
        return exported

    def get_audit_logs_filtered(
        self,
        db: Session,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        resource_type: Optional[str],
        action: Optional[str],
    ) -> list:
        """Internal helper for filtered audit log queries.

        Args:
            db: SQLAlchemy database session.
            start_date: Optional start date.
            end_date: Optional end date.
            resource_type: Optional resource type.
            action: Optional action.

        Returns:
            List of AuditLog objects matching filters.
        """
        query = db.query(AuditLog)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if action:
            query = query.filter(AuditLog.action == action)

        return query.order_by(desc(AuditLog.timestamp)).all()