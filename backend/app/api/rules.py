"""
API routes for Firewall Rules management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    result = FirewallService.get_firewall_rules(
        db=db,
        user_id=current_user.object_id,
        workload_id=workload_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return result


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
    rule = FirewallService.get_firewall_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    return rule


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
    new_rule = FirewallService.create_firewall_rule(
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
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="create",
        resource_type="firewall_rule",
        resource_id=str(new_rule.id),
        new_value={"rule_collection_name": rule.rule_collection_name},
        correlation_id=None,
    )
    
    return new_rule


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
    old_rule = FirewallService.get_firewall_rule(db, rule_id)
    
    update_data = rule.model_dump(exclude_unset=True)
    new_rule = FirewallService.update_firewall_rule(
        db=db,
        rule_id=rule_id,
        user_id=current_user.object_id,
        **update_data,
    )
    
    # Log audit
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="update",
        resource_type="firewall_rule",
        resource_id=str(rule_id),
        old_value={"old_name": old_rule.rule_collection_name},
        new_value={"new_name": new_rule.rule_collection_name},
        correlation_id=None,
    )
    
    return new_rule


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
    FirewallService.delete_firewall_rule(db, rule_id)
    
    # Log audit
    AuditService.log_action(
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
    return WorkloadService.get_workloads(db)


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
    workload = WorkloadService.get_workload(db, workload_id)
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
    result = FirewallService.search_firewall_rules(
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
    return result


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
    if not rules:
        raise HTTPException(status_code=400, detail="No rules provided")
    
    created = []
    errors = []
    
    for i, rule in enumerate(rules):
        try:
            new_rule = FirewallService.create_firewall_rule(
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
            created.append(new_rule)
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
    rule_ids: List[UUID],
    update_data: FirewallRuleUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk update multiple firewall rules."""
    updated = []
    errors = []
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for rule_id in rule_ids:
        try:
            rule = FirewallService.get_firewall_rule(db, rule_id)
            if not rule:
                errors.append({"id": str(rule_id), "error": "Rule not found"})
                continue
            
            updated_rule = FirewallService.update_firewall_rule(
                db=db,
                rule_id=rule_id,
                user_id=current_user.object_id,
                **update_dict,
            )
            updated.append(updated_rule)
            
            AuditService.log_action(
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bulk delete rules",
    description="Delete multiple firewall rules at once",
)
async def bulk_delete_rules(
    rule_ids: List[UUID],
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk delete multiple firewall rules."""
    deleted = []
    errors = []
    
    for rule_id in rule_ids:
        try:
            rule = FirewallService.get_firewall_rule(db, rule_id)
            if not rule:
                errors.append({"id": str(rule_id), "error": "Rule not found"})
                continue
            
            FirewallService.delete_firewall_rule(db, rule_id)
            deleted.append(str(rule_id))
            
            AuditService.log_action(
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
    rules = FirewallService.get_firewall_rules(
        db=db,
        user_id=current_user.object_id,
        workload_id=workload_id,
        status=status_filter,
        page=1,
        page_size=10000,
    )
    
    if format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        if rules.get("items"):
            writer = csv.DictWriter(output, fieldnames=[
                "id", "rule_collection_name", "priority", "action", "protocol",
                "source_addresses", "destination_fqdns", "source_ip_groups",
                "destination_ports", "description", "status", "workload_id"
            ])
            writer.writeheader()
            for item in rules["items"]:
                row = {k: str(v) if v else "" for k, v in item.dict().items()}
                writer.writerow(row)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="firewall_rules_export.csv"'}
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
    rule = FirewallService.get_firewall_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Firewall rule not found")
    
    cloned_rule = FirewallService.create_firewall_rule(
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
    
    AuditService.log_action(
        db=db,
        user_id=current_user.object_id,
        action="clone",
        resource_type="firewall_rule",
        resource_id=str(rule_id),
        new_value={"cloned_from": str(rule_id), "cloned_to": str(cloned_rule.id)},
        correlation_id=None,
    )
    
    return cloned_rule


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
    stats = FirewallService.get_rule_stats(db)
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
    result = FirewallService.validate_firewall_rule(db, rule)
    return result
