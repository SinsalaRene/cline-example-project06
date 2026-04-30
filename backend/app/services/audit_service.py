"""
Audit service for tracking all changes and actions.
"""

import json
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit import AuditLog
from app.models.approval import ApprovalRequest


class AuditService:
    """Service for audit trail management."""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        old_value: dict = None,
        new_value: dict = None,
        ip_address: str = None,
        user_agent: str = None,
        correlation_id: UUID = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: UUID = None,
        resource_type: str = None,
        action: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get audit logs with filtering and pagination."""
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
        
        query = query.order_by(desc(AuditLog.timestamp))
        
        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    @staticmethod
    def get_audit_for_resource(db: Session, resource_type: str, resource_id: str) -> list:
        """Get audit logs for a specific resource."""
        return db.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        ).order_by(desc(AuditLog.timestamp)).all()