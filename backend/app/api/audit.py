"""
API routes for Audit log management.

Provides endpoints for viewing, filtering, searching, and exporting audit logs.
"""

import csv
import io
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth_service import get_current_user
from app.schemas.user import UserInfo
from app.services.audit_service import AuditService
from datetime import datetime

router = APIRouter(prefix="/audit", tags=["audit"])


def _convert_model(item):
    """Convert a raw SQLAlchemy model instance to a JSON-compatible dict."""
    if isinstance(item, dict):
        return item
    if hasattr(item, '__dict__') and not hasattr(item, '__table__'):
        data = {k: v for k, v in item.__dict__.items() if not k.startswith('_sa_')}
    elif hasattr(item, '__table__'):
        data = {}
        for col_name in item.__table__.columns.keys():
            val = getattr(item, col_name, None)
            if val is not None:
                data[col_name] = val
    else:
        return item

    # Normalize fields
    for field in ("severity",):
        if field in data and data[field] is not None:
            data[field] = str(data[field]).lower()
    return data


def _convert_audit_item(item):
    """Convert an AuditLog SQLAlchemy model to a JSON-compatible dict."""
    if isinstance(item, dict):
        return item
    data = {}
    for col_name in item.__table__.columns.keys():
        val = getattr(item, col_name, None)
        data[col_name] = val
    # Convert JSON string fields back to dicts
    if data.get("old_value") and isinstance(data["old_value"], str):
        try:
            data["old_value"] = json.loads(data["old_value"])
        except (json.JSONDecodeError, TypeError):
            data["old_value"] = None
    if data.get("new_value") and isinstance(data["new_value"], str):
        try:
            data["new_value"] = json.loads(data["new_value"])
        except (json.JSONDecodeError, TypeError):
            data["new_value"] = None
    return data


def _convert_paged(result_dict):
    """Convert paginated results that may contain raw models."""
    if not isinstance(result_dict, dict):
        return result_dict
    for key in ("items", "logs", "data"):
        if key in result_dict and isinstance(result_dict[key], list):
            converted = []
            for i in result_dict[key]:
                if hasattr(i, '__table__'):
                    converted.append(_convert_audit_item(i))
                elif isinstance(i, dict):
                    converted.append(i)
                else:
                    converted.append(_convert_model(i))
            result_dict[key] = converted
    return result_dict


def _convert_result(result):
    """Convert SQLAlchemy models in a result dict."""
    if isinstance(result, dict):
        new_result = {}
        for k, v in result.items():
            if isinstance(v, list):
                new_result[k] = [_convert_model(item) if hasattr(item, '__dict__') else item for item in v]
            elif hasattr(v, '__dict__') and not hasattr(v, '__table__'):
                new_result[k] = _convert_model(v)
            else:
                new_result[k] = v
        return new_result
    return result


@router.get(
    "",
    summary="Get audit logs",
    description="Get paginated audit logs with comprehensive filtering and search",
)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action (create, update, delete, etc.)"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    search: Optional[str] = Query(None, description="Search across message and details"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit logs with pagination and comprehensive filtering."""
    service = AuditService()
    result = service.get_audit_logs(
        db=db,
        user_id=current_user.object_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


@router.get(
    "/resource/{resource_id}",
    summary="Get audit log for resource",
    description="Get all audit entries for a specific resource",
)
async def get_audit_for_resource(
    resource_id: UUID,
    resource_type: str = Query(..., description="Resource type (firewall_rule, approval_request, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit logs for a specific resource."""
    service = AuditService()
    logs = service.get_audit_for_resource(db, resource_type, str(resource_id))
    converted_logs = [_convert_model(log) for log in logs] if logs else []
    return {"resource_id": str(resource_id), "resource_type": resource_type, "audit_logs": converted_logs, "total": len(converted_logs)}


@router.get(
    "/user/{user_id}",
    summary="Get audit logs by user",
    description="Get all audit entries for a specific user",
)
async def get_audit_for_user(
    user_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit logs filtered by user ID."""
    service = AuditService()
    result = service.get_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


@router.get(
    "/stats",
    summary="Get audit statistics",
    description="Get summary statistics for audit logs",
)
async def get_audit_stats(
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get audit log statistics grouped by resource type, action, and user."""
    service = AuditService()
    stats = service.get_audit_stats(db=db, start_date=start_date, end_date=end_date)
    return _convert_result(stats)


@router.get(
    "/search",
    summary="Search audit logs",
    description="Search audit logs across all fields",
)
async def search_audit_logs(
    q: str = Query(..., min_length=1, description="Search query"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search audit logs with full-text search."""
    service = AuditService()
    result = service.search_audit_logs(
        db=db,
        query_str=q,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


@router.get(
    "/export",
    summary="Export audit logs",
    description="Export audit logs to CSV/JSON format",
)
async def export_audit_logs(
    format: str = Query("json", description="Export format (json or csv)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export audit logs to CSV or JSON format."""
    service = AuditService()
    logs = service.get_audit_logs(
        db=db,
        user_id=current_user.object_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000,
    )
    
    if format == "csv":
        # Return CSV format
        import csv
        import io

        output = io.StringIO()
        # Only export the audit log fields that are safe for CSV
        csv_fields = ["id", "user_id", "action", "resource_type", "resource_id", "old_value", "new_value", "ip_address", "user_agent", "timestamp", "approval_request_id", "correlation_id"]
        if logs.get("items"):
            writer = csv.DictWriter(output, fieldnames=csv_fields, extrasaction='ignore')
            writer.writeheader()
            for item in logs["items"]:
                if hasattr(item, '__table__'):
                    item_dict = _convert_audit_item(item)
                else:
                    item_dict = item if isinstance(item, dict) else dict(item)
                row = {k: str(v) if v is not None else "" for k, v in item_dict.items() if k in csv_fields}
                writer.writerow(row)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="audit_export.csv"'}
        )

    # Return JSON format
    return {"export_format": "json", "total_records": logs.get("total", 0), "logs": _convert_paged(logs)}


@router.get(
    "/export/csv",
    summary="Export audit logs as CSV",
    description="Export audit logs to CSV format",
)
async def export_audit_logs_csv(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export audit logs to CSV format."""
    import io
    service = AuditService()
    logs = service.get_audit_logs(
        db=db,
        user_id=current_user.object_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000,
    )
    
    output = io.StringIO()
    if logs.get("items"):
        writer = csv.DictWriter(output, fieldnames=["id", "user_id", "action", "resource_type", "resource_id", "old_value", "new_value", "ip_address", "user_agent", "timestamp"])
        writer.writeheader()
        for item in logs["items"]:
            if hasattr(item, '__table__'):
                item_dict = _convert_audit_item(item)
            else:
                item_dict = item if isinstance(item, dict) else dict(item)
            row = {k: str(v) if v else "" for k, v in item_dict.items()}
            writer.writerow(row)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_export.csv"'}
    )


@router.get(
    "/by-correlation/{correlation_id}",
    summary="Get audit logs by correlation ID",
    description="Get all audit entries for a correlation ID (request tracing)",
)
async def get_audit_by_correlation(
    correlation_id: str,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all audit entries for a correlation ID."""
    service = AuditService()
    logs = service.get_audit_by_correlation_id(db, correlation_id)
    converted_logs = [_convert_model(log) for log in logs] if logs else []
    return {"correlation_id": correlation_id, "audit_logs": converted_logs, "total": len(converted_logs)}


@router.get(
    "/actions",
    summary="Get available actions",
    description="Get list of all distinct actions recorded in audit logs",
)
async def get_available_actions(
    resource_type: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of distinct actions in audit logs."""
    service = AuditService()
    actions = service.get_distinct_actions(db, resource_type=resource_type)
    return _convert_result({"actions": actions})


@router.get(
    "/resource-types",
    summary="Get available resource types",
    description="Get list of all distinct resource types in audit logs",
)
async def get_available_resource_types(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of distinct resource types in audit logs."""
    service = AuditService()
    types = service.get_distinct_resource_types(db)
    return _convert_result({"resource_types": types})
