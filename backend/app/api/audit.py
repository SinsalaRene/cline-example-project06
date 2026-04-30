"""
API routes for Audit log management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth_service import get_current_user
from app.schemas.user import UserInfo
from app.services.audit_service import AuditService
from datetime import datetime

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    summary="Get audit logs",
    description="Get paginated audit logs with filtering",
)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit logs with pagination and filtering."""
    result = AuditService.get_audit_logs(
        db=db,
        user_id=current_user.object_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return result


@router.get(
    "/resource/{resource_id}",
    summary="Get audit log for resource",
    description="Get audit logs for a specific resource",
)
async def get_audit_for_resource(
    resource_id: UUID,
    resource_type: str = Query(..., description="Resource type (firewall_rule, approval_request, etc.)"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit logs for a specific resource."""
    logs = AuditService.get_audit_for_resource(db, resource_type, str(resource_id))
    return {"resource_id": str(resource_id), "resource_type": resource_type, "audit_logs": logs}


@router.get(
    "/export",
    summary="Export audit logs",
    description="Export audit logs to CSV/JSON",
)
async def export_audit_logs(
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export audit logs."""
    # Get all matching records (no pagination for export)
    logs = AuditService.get_audit_logs(
        db=db,
        user_id=current_user.object_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000,
    )
    return {"exported_logs": logs}