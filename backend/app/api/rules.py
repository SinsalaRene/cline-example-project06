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