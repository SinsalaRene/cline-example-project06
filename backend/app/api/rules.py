"""
API routes for Firewall Rules management.
"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth_service import get_current_user
from app.schemas.user import UserInfo
from app.schemas.firewall_rule import (
    FirewallRuleCreate,
    FirewallRuleUpdate,
    FirewallRuleResponse,
    WorkloadResponse,
    PaginatedResponse,
)
from app.services.firewall_service import FirewallService, WorkloadService
from app.services.audit_service import AuditService
from app.models.firewall_rule import FirewallRuleAction, FirewallProtocol, FirewallRuleStatus

router = APIRouter(prefix="/rules", tags=["rules"])


def _rule_to_dict(rule) -> dict:
    """Convert a SQLAlchemy FirewallRule model to a dict for JSON responses."""
    if hasattr(rule, 'dict'):
        data = rule.dict()
    elif hasattr(rule, '__dict__') and not hasattr(rule, '__table__'):
        data = {k: v for k, v in rule.__dict__.items() if not k.startswith('_')}
    else:
        data = {}

    # Parse JSON fields stored as strings in the DB
    for field in ("source_addresses", "destination_fqdns", "source_ip_groups", "destination_ports"):
        val = data.get(field)
        if isinstance(val, str):
            try:
                data[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                data[field] = None
        elif val is None:
            data[field] = None

    # Normalize status/action/protocol to lowercase for Pydantic
    if "status" in data and data["status"] is not None:
        data["status"] = str(data["status"]).lower()
    for norm_field in ("action", "protocol"):
        if norm_field in data and isinstance(data.get(norm_field), str):
            data[norm_field] = data[norm_field].lower()

    return data


def _convert_model(item):
    """Convert a raw SQLAlchemy model instance to a JSON-compatible dict."""
    if isinstance(item, dict):
        data = dict(item)
    elif hasattr(item, '__dict__') and not hasattr(item, '__table__'):
        data = {k: v for k, v in item.__dict__.items() if not k.startswith('_sa_')}
    elif hasattr(item, '__table__'):
        # SQLAlchemy model with table - get column names from the model
        data = {}
        for col_name in item.__table__.columns.keys():
            val = getattr(item, col_name, None)
            # Always include the field (even if None) so Pydantic can validate it
            data[col_name] = val
    else:
        return item

    # Parse JSON fields stored as strings in the DB
    for field in ("source_addresses", "destination_fqdns", "source_ip_groups", "destination_ports"):
        val = data.get(field)
        if isinstance(val, str):
            try:
                data[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                data[field] = None

    # Normalize status to lowercase for Pydantic
    if "status" in data and data["status"] is not None:
        data["status"] = str(data["status"]).lower()

    # Normalize action to lowercase for Pydantic FirewallRuleAction enum
    if "action" in data and data["action"] is not None:
        data["action"] = str(data["action"]).lower()

    # Normalize protocol to lowercase for Pydantic FirewallProtocol enum
    if "protocol" in data and data["protocol"] is not None:
        data["protocol"] = str(data["protocol"]).lower()

    # Ensure azure_resource_id always has a value (empty string if None)
    if data.get("azure_resource_id") is None:
        data["azure_resource_id"] = ""

    return data


def _convert_paged(result_dict):
    """Convert paginated results that may contain raw models."""
    if not isinstance(result_dict, dict):
        return result_dict
    if "items" in result_dict and isinstance(result_dict["items"], list):
        result_dict["items"] = [_convert_model(i) for i in result_dict["items"]]
    return result_dict


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List firewall rules",
    description="Get paginated list of firewall rules",
)
async def list_rules(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    workload_id: Optional[UUID] = Query(None, description="Filter by workload"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List firewall rules with pagination."""
    service = FirewallService()
    result = service.get_firewall_rules(
        db=db,
        user_id=current_user.object_id,
        workload_id=workload_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


@router.get(
    "/{rule_id}",
    response_model=FirewallRuleResponse,
    summary="Get firewall rule",
    description="Get a single firewall rule by ID",
)
async def get_rule(
    rule_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single firewall rule."""
    service = FirewallService()
    rule = service.get_firewall_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    return _convert_model(rule)


@router.post(
    "",
    response_model=FirewallRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create firewall rule",
    description="Create a new firewall rule",
)
async def create_rule(
    rule: FirewallRuleCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new firewall rule."""
    service = FirewallService()
    new_rule = service.create_firewall_rule(
        db=db,
        rule_collection_name=rule.rule_collection_name,
        priority=rule.priority,
        action=rule.action,
        protocol=rule.protocol,
        source_addresses=rule.source_addresses,
        destination_fqdns=rule.destination_fqdns,
        source_ip_groups=rule.source_ip_groups,
        destination_ports=rule.destination_ports,
        description=rule.description,
        workload_id=rule.workload_id,
        azure_resource_id=rule.azure_resource_id,
        user_id=current_user.object_id,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="create",
        resource_type="firewall_rule",
        resource_id=str(new_rule.id),
        new_value={"rule_collection_name": rule.rule_collection_name},
        correlation_id=None,
    )
    return _convert_model(new_rule)


@router.put(
    "/{rule_id}",
    response_model=FirewallRuleResponse,
    summary="Update firewall rule",
    description="Update an existing firewall rule",
)
async def update_rule(
    rule_id: UUID,
    rule: FirewallRuleUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a firewall rule."""
    service = FirewallService()
    old_rule = service.get_firewall_rule(db, rule_id)

    update_data = rule.model_dump(exclude_unset=True)
    new_rule = service.update_firewall_rule(
        db=db,
        rule_id=rule_id,
        user_id=current_user.object_id,
        **update_data,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="update",
        resource_type="firewall_rule",
        resource_id=str(rule_id),
        old_value={"old_name": old_rule.rule_collection_name if old_rule else "unknown"},
        new_value={"new_name": new_rule.rule_collection_name if new_rule else "unknown"},
        correlation_id=None,
    )
    return _convert_model(new_rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete firewall rule",
    description="Delete a firewall rule",
)
async def delete_rule(
    rule_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a firewall rule."""
    service = FirewallService()
    service.delete_firewall_rule(db, rule_id)
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="delete",
        resource_type="firewall_rule",
        resource_id=str(rule_id),
        correlation_id=None,
    )
    return None


@router.get(
    "/workloads",
    response_model=List[WorkloadResponse],
    summary="List workloads",
    description="Get all workloads",
)
async def list_workloads(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all workloads."""
    service = WorkloadService()
    return service.get_workloads(db)


@router.get(
    "/workloads/{workload_id}",
    response_model=WorkloadResponse,
    summary="Get workload details",
    description="Get detailed information about a specific workload",
)
async def get_workload(
    workload_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed workload information."""
    service = WorkloadService()
    workload = service.get_workload(db, workload_id)
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    return workload


@router.get(
    "/search",
    response_model=PaginatedResponse,
    summary="Search firewall rules",
    description="Search firewall rules by various criteria",
)
async def search_rules(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    action_filter: Optional[str] = Query(None, description="Filter by action (allow/deny)"),
    protocol_filter: Optional[str] = Query(None, description="Filter by protocol (tcp/udp/http/icmp/*)"),
    workload_id: Optional[UUID] = Query(None, description="Filter by workload"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search firewall rules by query and filters."""
    service = FirewallService()
    result = service.search_firewall_rules(
        db=db,
        query=q,
        user_id=current_user.object_id,
        status=status_filter,
        action=action_filter,
        protocol=protocol_filter,
        workload_id=workload_id,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


@router.post(
    "/bulk",
    response_model=dict,
    summary="Bulk create rules",
    description="Create multiple firewall rules at once",
)
async def bulk_create_rules(
    rules: List[FirewallRuleCreate],
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk create multiple firewall rules."""
    service = FirewallService()
    if not rules:
        raise HTTPException(status_code=400, detail="No rules provided")

    created = []
    errors = []

    for i, rule in enumerate(rules):
        try:
            new_rule = service.create_firewall_rule(
                db=db,
                rule_collection_name=rule.rule_collection_name,
                priority=rule.priority,
                action=rule.action,
                protocol=rule.protocol,
                source_addresses=rule.source_addresses,
                destination_fqdns=rule.destination_fqdns,
                source_ip_groups=rule.source_ip_groups,
                destination_ports=rule.destination_ports,
                description=rule.description,
                workload_id=rule.workload_id,
                azure_resource_id=rule.azure_resource_id,
                user_id=current_user.object_id,
            )
            created.append(_convert_model(new_rule))
        except Exception as e:
            errors.append({"index": i, "error": str(e), "rule": rule.dict()})

    return {"created": len(created), "errors": errors, "rules": created}


@router.put(
    "/bulk",
    response_model=dict,
    summary="Bulk update rules",
    description="Update multiple firewall rules at once",
)
async def bulk_update_rules(
    bulk_data: dict,
    update_data: FirewallRuleUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk update multiple firewall rules."""
    rule_ids = bulk_data.get("rule_ids", [])
    if not rule_ids:
        raise HTTPException(status_code=400, detail="No rule IDs provided")
    service = FirewallService()
    updated = []
    errors = []

    update_dict = update_data.model_dump(exclude_unset=True)

    for rule_id in rule_ids:
        try:
            rule = service.get_firewall_rule(db, rule_id)
            if not rule:
                errors.append({"id": str(rule_id), "error": "Rule not found"})
                continue

            updated_rule = service.update_firewall_rule(
                db=db,
                rule_id=rule_id,
                user_id=current_user.object_id,
                **update_dict,
            )
            updated.append(_convert_model(updated_rule))

            AuditService().log_action(
                db=db,
                user_id=current_user.object_id,
                action="bulk_update",
                resource_type="firewall_rule",
                resource_id=str(rule_id),
                new_value=update_dict,
                correlation_id=None,
            )
        except Exception as e:
            errors.append({"id": str(rule_id), "error": str(e)})

    return {"updated": len(updated), "errors": errors, "rules": updated}


@router.delete(
    "/bulk",
    response_model=dict,
    summary="Bulk delete rules",
    description="Delete multiple firewall rules at once",
)
async def bulk_delete_rules(
    bulk_data: dict,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk delete multiple firewall rules."""
    rule_ids = bulk_data.get("rule_ids", [])
    if not rule_ids:
        raise HTTPException(status_code=400, detail="No rule IDs provided")
    service = FirewallService()
    deleted = []
    errors = []

    for rule_id in rule_ids:
        try:
            rule = service.get_firewall_rule(db, rule_id)
            if not rule:
                errors.append({"id": str(rule_id), "error": "Rule not found"})
                continue

            service.delete_firewall_rule(db, rule_id)
            deleted.append(str(rule_id))

            AuditService().log_action(
                db=db,
                user_id=current_user.object_id,
                action="bulk_delete",
                resource_type="firewall_rule",
                resource_id=str(rule_id),
                correlation_id=None,
            )
        except Exception as e:
            errors.append({"id": str(rule_id), "error": str(e)})

    return {"deleted": deleted, "errors": errors}


@router.get(
    "/export",
    summary="Export firewall rules",
    description="Export firewall rules to CSV or JSON format",
)
async def export_rules(
    format: str = Query("json", description="Export format (json or csv)"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    workload_id: Optional[UUID] = Query(None, description="Filter by workload"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export firewall rules to CSV or JSON."""
    service = FirewallService()
    rules = service.get_firewall_rules(
        db=db,
        user_id=current_user.object_id,
        workload_id=workload_id,
        status=status_filter,
        page=1,
        page_size=10000,
    )

    if format == "csv":
        import io
        output = io.StringIO()
        if rules.get("items"):
            writer = __import__('csv').DictWriter(
                output,
                fieldnames=["id", "rule_collection_name", "priority", "action",
                            "protocol", "source_addresses", "destination_fqdns",
                            "source_ip_groups", "destination_ports",
                            "description", "status", "workload_id"],
            )
            writer.writeheader()
            for item in rules["items"]:
                row = {k: str(v) if v else "" for k, v in item.dict().items()}
                writer.writerow(row)
        return FastAPIResponse(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="firewall_rules_export.csv"'},
        )

    return {"export_format": "json", "total": rules.get("total", 0), "rules": rules}


@router.post(
    "/{rule_id}/clone",
    response_model=FirewallRuleResponse,
    summary="Clone rule",
    description="Create a copy of an existing firewall rule",
)
async def clone_rule(
    rule_id: UUID,
    new_name: str = Query(..., description="New name for the cloned rule"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clone an existing firewall rule."""
    service = FirewallService()
    rule = service.get_firewall_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")

    cloned_rule = service.create_firewall_rule(
        db=db,
        rule_collection_name=f"{new_name} (copy)",
        priority=rule.priority,
        action=rule.action,
        protocol=rule.protocol,
        source_addresses=rule.source_addresses,
        destination_fqdns=rule.destination_fqdns,
        source_ip_groups=rule.source_ip_groups,
        destination_ports=rule.destination_ports,
        description=f"Cloned from: {rule.description}",
        workload_id=rule.workload_id,
        azure_resource_id=rule.azure_resource_id,
        user_id=current_user.object_id,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="clone",
        resource_type="firewall_rule",
        resource_id=str(rule_id),
        new_value={"cloned_from": str(rule_id), "cloned_to": str(cloned_rule.id)},
        correlation_id=None,
    )
    return _convert_model(cloned_rule)


@router.get(
    "/stats",
    summary="Get firewall rule statistics",
    description="Get statistics about firewall rules",
)
async def get_rule_stats(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get firewall rule statistics."""
    service = FirewallService()
    stats = service.get_rule_stats(db)
    return stats


@router.post(
    "/validate",
    response_model=dict,
    summary="Validate rule",
    description="Validate a firewall rule before creating/updating",
)
async def validate_rule(
    rule: FirewallRuleCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate a firewall rule configuration."""
    service = FirewallService()
    result = service.validate_firewall_rule(db, rule)
    return result