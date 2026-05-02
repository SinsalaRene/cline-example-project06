"""
API routes for Firewall Rules management.

This module provides endpoints for managing Azure firewall rules including
CRUD operations, search, filtering, bulk operations, export, and rule validation.

## Request Format

All POST/PUT endpoints accept JSON bodies matching the corresponding Pydantic
schemas defined in ``app.schemas.firewall_rule``.

## Response Format

Success responses return the created/updated resource or a paginated envelope::

    {
        "items": [...],
        "total": 42,
        "page": 1,
        "page_size": 50,
        "total_pages": 1
    }

## Error Codes

| Code         | Status | Description                           |
|--------------|--------|---------------------------------------|
| AUTH_REQUIRED    | 401  | Missing or invalid authentication token |
| VALIDATION_ERROR | 422  | Request body failed Pydantic validation  |
| NOT_FOUND        | 404  | Resource does not exist                    |
| CONFLICT         | 409  | Priority or duplicate conflict             |
| RATE_LIMIT       | 429  | Rate limit exceeded                        |
| INTERNAL_ERROR   | 500  | Unexpected server-side error               |
"""  # noqa: E501

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
    """Convert a SQLAlchemy FirewallRule model to a dict for JSON responses.
    
    Parses JSON fields stored as strings and normalizes enum values to
    lowercase for Pydantic compatibility.
    """
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


# ============================================================================
# Firewall Rule Endpoints
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List firewall rules",
    description=(
        "Get a paginated list of firewall rules. Supports filtering by status "
        "and workload_id. Results are ordered by priority ascending.\n\n"
        "**Example**: ``GET /api/v1/rules?page=1&page_size=10&status=active``"
    ),
    responses={
        200: {
            "description": "Successful list of firewall rules",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "rule_collection_name": "DefaultRuleCollection",
                                "priority": 100,
                                "action": "allow",
                                "protocol": "tcp",
                                "source_addresses": ["10.0.0.0/8"],
                                "destination_fqdns": ["example.com"],
                                "source_ip_groups": [],
                                "destination_ports": ["443"],
                                "description": "Allow HTTPS from internal network",
                                "status": "active",
                                "workload_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                                "azure_resource_id": "",
                                "created_by": "user@example.com",
                                "created_at": "2026-01-15T10:00:00+00:00",
                                "updated_at": "2026-01-15T10:00:00+00:00",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                        "total_pages": 1,
                    }
                }
            },
        },
        401: {"description": "Unauthorized - Missing or invalid auth token"},
        422: {"description": "Validation error - Invalid page or page_size parameter"},
    },
)
async def list_rules(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page (1-100)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (active, inactive, pending, blocked)"),
    workload_id: Optional[UUID] = Query(None, description="Filter by workload UUID"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List firewall rules with pagination, optional filtering by status and workload.
    
    **Query Parameters**:
    - ``page``: Page number (default 1, minimum 1)
    - ``page_size``: Items per page (default 50, range 1-100)
    - ``status``: Filter by rule status
    - ``workload_id``: Filter by workload UUID
    
    **Response**: Paginated list of firewall rule objects.
    """
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
    description=(
        "Retrieve a single firewall rule by its UUID.\n\n"
        "**Example**: ``GET /api/v1/rules/a1b2c3d4-e5f6-7890-abcd-ef1234567890``"
    ),
    responses={
        200: {
            "description": "Rule details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "rule_collection_name": "DefaultRuleCollection",
                        "priority": 100,
                        "action": "allow",
                        "protocol": "tcp",
                        "source_addresses": ["10.0.0.0/8"],
                        "destination_fqdns": ["example.com"],
                        "source_ip_groups": [],
                        "destination_ports": ["443"],
                        "description": "Allow HTTPS from internal network",
                        "status": "active",
                        "workload_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "azure_resource_id": "/subscriptions/.../resourceGroups/.../providers/Microsoft.Network/networkSecurityGroups/...",
                        "created_by": "user@example.com",
                        "created_at": "2026-01-15T10:00:00+00:00",
                        "updated_at": "2026-01-15T10:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized - Missing or invalid auth token"},
        404: {
            "description": "Not Found - Rule does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Firewall rule not found",
                            "path": "/api/v1/rules/00000000-0000-0000-0000-000000000000"
                        }
                    }
                }
            },
        },
    },
)
async def get_rule(
    rule_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single firewall rule by ID.
    
    **Path Parameters**:
    - ``rule_id``: UUID of the firewall rule
    
    **Response**: Single firewall rule object or 404 if not found.
    """
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
    description=(
        "Create a new firewall rule. The rule will be validated for priority conflicts, "
        "duplicate detection, and Azure SDK compatibility if configured.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "rule_collection_name": "DefaultRuleCollection",\n'
        '  "priority": 100,\n'
        '  "action": "allow",\n'
        '  "protocol": "tcp",\n'
        '  "source_addresses": ["10.0.0.0/8"],\n'
        '  "destination_fqdns": ["example.com"],\n'
        '  "destination_ports": ["443"],\n'
        '  "description": "Allow HTTPS from internal network"\n'
        "}\n"
        "```"
    ),
    responses={
        201: {
            "description": "Rule created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "rule_collection_name": "DefaultRuleCollection",
                        "priority": 100,
                        "action": "allow",
                        "protocol": "tcp",
                        "source_addresses": ["10.0.0.0/8"],
                        "destination_fqdns": ["example.com"],
                        "source_ip_groups": [],
                        "destination_ports": ["443"],
                        "description": "Allow HTTPS from internal network",
                        "status": "pending",
                        "workload_id": None,
                        "azure_resource_id": "",
                        "created_by": "user@example.com",
                        "created_at": "2026-01-15T10:00:00+00:00",
                        "updated_at": "2026-01-15T10:00:00+00:00",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Invalid rule data",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Validation error: input should be 'allow' or 'deny'",
                        }
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        409: {
            "description": "Conflict - Priority already taken",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRIORITY_CONFLICT",
                            "message": "A rule with priority 100 already exists",
                        }
                    }
                }
            },
        },
    },
)
async def create_rule(
    rule: FirewallRuleCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new firewall rule.
    
    **Request Body**: FirewallRuleCreate schema with required fields:
    - ``rule_collection_name``: Name of the rule collection (required)
    - ``priority``: Priority value, lower = higher priority (required)
    - ``action``: Either "allow" or "deny" (required)
    - ``protocol``: Protocol type - "tcp", "udp", "http", "https", or "*" (required)
    - ``source_addresses``: List of source IP/CIDR blocks (optional)
    - ``destination_fqdns``: List of destination FQDNs (optional)
    - ``source_ip_groups``: List of source IP group names (optional)
    - ``destination_ports``: List of destination port numbers (optional)
    - ``description``: Human-readable description (optional)
    - ``workload_id``: Associated workload UUID (optional)
    - ``azure_resource_id``: Azure NSG resource ID (optional)
    
    **Response**: Created firewall rule object.
    """
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
    description=(
        "Update an existing firewall rule. Only provided fields will be updated "
        "(partial update). All existing fields have defaults of ``None``.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "priority": 200,\n'
        '  "description": "Updated description"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Rule updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "rule_collection_name": "DefaultRuleCollection",
                        "priority": 200,
                        "action": "allow",
                        "protocol": "tcp",
                        "source_addresses": ["10.0.0.0/8"],
                        "destination_fqdns": ["example.com"],
                        "source_ip_groups": [],
                        "destination_ports": ["443"],
                        "description": "Updated description",
                        "status": "active",
                        "workload_id": None,
                        "azure_resource_id": "",
                        "created_by": "user@example.com",
                        "created_at": "2026-01-15T10:00:00+00:00",
                        "updated_at": "2026-01-15T11:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Rule does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Firewall rule not found",
                        }
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Invalid update data",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Validation error: value must be 'allow' or 'deny'",
                        }
                    }
                }
            },
        },
    },
)
async def update_rule(
    rule_id: UUID,
    rule: FirewallRuleUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a firewall rule (partial update).
    
    **Path Parameters**:
    - ``rule_id``: UUID of the rule to update
    
    **Request Body**: Partial FirewallRuleUpdate - only fields to update need to be provided.
    
    **Response**: Updated firewall rule object or 404/422 on error.
    """
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
    description=(
        "Delete a firewall rule. This operation is irreversible and will log "
        "to the audit trail.\n\n"
        "**Example**: ``DELETE /api/v1/rules/a1b2c3d4-e5f6-7890-abcd-ef1234567890``"
    ),
    responses={
        204: {"description": "Rule deleted successfully"},
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Rule does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Firewall rule not found",
                        }
                    }
                }
            },
        },
    },
)
async def delete_rule(
    rule_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a firewall rule by ID.
    
    **Path Parameters**:
    - ``rule_id``: UUID of the rule to delete
    
    **Response**: Empty body (204 No Content) on success, 404 if not found.
    """
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


# ============================================================================
# Workload Endpoints
# ============================================================================


@router.get(
    "/workloads",
    response_model=List[WorkloadResponse],
    summary="List workloads",
    description=(
        "Get all workloads that have associated firewall rules. Each workload "
        "represents an application or service that has firewall configurations.\n\n"
        "**Example**: ``GET /api/v1/rules/workloads``"
    ),
    responses={
        200: {
            "description": "List of workloads",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                            "name": "WebApplication",
                            "description": "Public-facing web application",
                            "created_at": "2026-01-01T00:00:00+00:00",
                        },
                        {
                            "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                            "name": "BackendAPI",
                            "description": "Internal REST API service",
                            "created_at": "2026-01-02T00:00:00+00:00",
                        },
                    ]
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def list_workloads(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all workloads.
    
    **Response**: Array of workload objects with id, name, and description.
    """
    service = WorkloadService()
    return service.get_workloads(db)


@router.get(
    "/workloads/{workload_id}",
    response_model=WorkloadResponse,
    summary="Get workload details",
    description=(
        "Get detailed information about a specific workload including all its "
        "associated firewall rules.\n\n"
        "**Example**: ``GET /api/v1/rules/workloads/b2c3d4e5-f6a7-8901-bcde-f12345678901``"
    ),
    responses={
        200: {
            "description": "Workload details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "name": "WebApplication",
                        "description": "Public-facing web application",
                        "firewall_rules_count": 5,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Workload does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Workload not found",
                        }
                    }
                }
            },
        },
    },
)
async def get_workload(
    workload_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed workload information by ID.
    
    **Path Parameters**:
    - ``workload_id``: UUID of the workload
    
    **Response**: Workload object or 404 if not found.
    """
    service = WorkloadService()
    workload = service.get_workload(db, workload_id)
    if not workload:
        raise HTTPException(status_code=404, detail="Workload not found")
    return workload


# ============================================================================
# Search Endpoint
# ============================================================================


@router.get(
    "/search",
    response_model=PaginatedResponse,
    summary="Search firewall rules",
    description=(
        "Search firewall rules by free-text query and optional filters. "
        "Searches across rule name, description, source addresses, and "
        "destination FQDNs.\n\n"
        "**Example**: ``GET /api/v1/rules/search?q=HTTPS&status=active&action=allow``"
    ),
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "rule_collection_name": "DefaultRuleCollection",
                                "priority": 100,
                                "action": "allow",
                                "protocol": "tcp",
                                "source_addresses": ["10.0.0.0/8"],
                                "destination_fqdns": ["example.com"],
                                "destination_ports": ["443"],
                                "description": "Allow HTTPS from internal network",
                                "status": "active",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        422: {
            "description": "Validation Error - Search query must be at least 1 character",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "q"],
                                "msg": "Field required",
                                "type": "missing",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def search_rules(
    q: str = Query(..., min_length=1, description="Search query (minimum 1 character)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    action_filter: Optional[str] = Query(None, description="Filter by action (allow/deny)"),
    protocol_filter: Optional[str] = Query(None, description="Filter by protocol (tcp/udp/http/icmp/*)"),
    workload_id: Optional[UUID] = Query(None, description="Filter by workload"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search firewall rules by query and filters.
    
    **Query Parameters**:
    - ``q``: Full-text search query (required, minimum 1 character)
    - ``page``: Page number (default 1)
    - ``page_size``: Items per page (default 50, max 100)
    - ``status``: Filter by rule status
    - ``action``: Filter by action (allow/deny)
    - ``protocol``: Filter by protocol (tcp/udp/http/icmp/*)
    - ``workload_id``: Filter by workload UUID
    
    **Response**: Paginated search results.
    """
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


# ============================================================================
# Bulk Operation Endpoints
# ============================================================================


@router.post(
    "/bulk",
    response_model=dict,
    summary="Bulk create rules",
    description=(
        "Create multiple firewall rules in a single request. Each rule is "
        "validated independently. Successful creations and failures are reported "
        "separately.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "[\n"
        "  {\n"
        '    "rule_collection_name": "WebRules",\n'
        '    "priority": 100,\n'
        '    "action": "allow",\n'
        '    "protocol": "tcp",\n'
        '    "source_addresses": ["10.0.0.0/8"],\n'
        '    "destination_fqdns": ["example.com"],\n'
        '    "destination_ports": ["443"]\n'
        "  },\n"
        "  {\n"
        '    "rule_collection_name": "DBRules",\n'
        '    "priority": 200,\n'
        '    "action": "deny",\n'
        '    "protocol": "tcp",\n'
        '    "source_addresses": ["0.0.0.0/0"],\n'
        '    "destination_fqdns": ["db.example.com"],\n'
        '    "destination_ports": ["3306"]\n'
        "  }\n"
        "]\n"
        "```"
    ),
    responses={
        201: {
            "description": "Bulk creation results",
            "content": {
                "application/json": {
                    "example": {
                        "created": 2,
                        "errors": [],
                        "rules": [
                            {
                                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "rule_collection_name": "WebRules",
                                "priority": 100,
                                "action": "allow",
                                "status": "pending",
                            },
                            {
                                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                                "rule_collection_name": "DBRules",
                                "priority": 200,
                                "action": "deny",
                                "status": "pending",
                            },
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Empty rules array",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "No rules provided",
                        }
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def bulk_create_rules(
    rules: List[FirewallRuleCreate],
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk create multiple firewall rules.
    
    **Request Body**: Array of FirewallRuleCreate objects.
    
    **Response**: Summary with ``created`` count, ``errors`` array, and ``rules`` array.
    """
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
    description=(
        "Update multiple firewall rules simultaneously. All rules in the given "
        "list will receive the same field updates.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "rule_ids": ["a1b2c3d4...", "b2c3d4e5..."],\n'
        '  "priority": 500,\n'
        '  "description": "Updated description"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Bulk update results",
            "content": {
                "application/json": {
                    "example": {
                        "updated": 1,
                        "errors": [{"id": "b2c3d4e5...", "error": "Rule not found"}],
                        "rules": [
                            {
                                "id": "a1b2c3d4...",
                                "priority": 500,
                                "description": "Updated description",
                            }
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - No rule IDs provided",
            "content": {
                "application/json": {
                    "example": {"error": {"code": "VALIDATION_ERROR", "message": "No rule IDs provided"}}
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def bulk_update_rules(
    bulk_data: dict,
    update_data: FirewallRuleUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk update multiple firewall rules.
    
    **Request Body**: Two parts - ``bulk_data`` dict (containing ``rule_ids``) and ``update_data`` (fields to update).
    
    **Response**: Summary with ``updated`` count, ``errors`` array, and ``rules`` array.
    """
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
    description=(
        "Delete multiple firewall rules at once. Returns a list of deleted "
        "IDs and any errors encountered.\n\n"
        "**Example Request**:\n"
        "```json\n"
        '{\n'
        '  "rule_ids": ["a1b2c3d4...", "b2c3d4e5..."]\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Bulk delete results",
            "content": {
                "application/json": {
                    "example": {
                        "deleted": ["a1b2c3d4...", "b2c3d4e5..."],
                        "errors": [{"id": "c3d4e5f6...", "error": "Rule not found"}],
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - No rule IDs provided",
            "content": {
                "application/json": {
                    "example": {"error": {"code": "VALIDATION_ERROR", "message": "No rule IDs provided"}}
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def bulk_delete_rules(
    bulk_data: dict,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk delete multiple firewall rules.
    
    **Request Body**: Dict containing ``rule_ids`` array.
    
    **Response**: ``deleted`` list of IDs and ``errors`` array.
    """
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


# ============================================================================
# Export Endpoint
# ============================================================================


@router.get(
    "/export",
    summary="Export firewall rules",
    description=(
        "Export all firewall rules (optionally filtered) to CSV or JSON format. "
        "CSV returns a file download with ``Content-Disposition`` header.\n\n"
        "**Example**: ``GET /api/v1/rules/export?format=json``\n"
        "**Example CSV**: ``GET /api/v1/rules/export?format=csv&status=active``"
    ),
    responses={
        200: {
            "description": "Exported rules",
            "content": {
                "application/json": {
                    "example": {
                        "export_format": "json",
                        "total": 2,
                        "rules": [
                            {"id": "a1b2c3d4...", "rule_collection_name": "WebRules", "priority": 100},
                            {"id": "b2c3d4e5...", "rule_collection_name": "DBRules", "priority": 200},
                        ],
                    }
                },
                "text/csv": {
                    "example": "id,rule_collection_name,priority,action,protocol,description\na1b2...,WebRules,100,allow,tcp,Allow HTTPS"
                },
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def export_rules(
    format: str = Query("json", description="Export format (json or csv)"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    workload_id: Optional[UUID] = Query(None, description="Filter by workload"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export firewall rules to CSV or JSON.
    
    **Query Parameters**:
    - ``format``: Export format - ``json`` or ``csv`` (default ``json``)
    - ``status``: Filter by status (optional)
    - ``workload_id``: Filter by workload (optional)
    
    **Response**: JSON object with rules or CSV file download.
    """
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


# ============================================================================
# Clone Endpoint
# ============================================================================


@router.post(
    "/{rule_id}/clone",
    response_model=FirewallRuleResponse,
    summary="Clone rule",
    description=(
        "Create a copy of an existing firewall rule with a new name. "
        "All fields except ``id``, ``name``, and timestamps are copied.\n\n"
        "**Example**: ``POST /api/v1/rules/a1b2c3d4.../clone?new_name=WebRules-Copy``"
    ),
    responses={
        201: {
            "description": "Cloned rule",
            "content": {
                "application/json": {
                    "example": {
                        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                        "rule_collection_name": "WebRules-Copy",
                        "priority": 100,
                        "action": "allow",
                        "protocol": "tcp",
                        "status": "pending",
                        "created_at": "2026-01-15T11:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Source rule does not exist",
            "content": {
                "application/json": {
                    "example": {"error": {"code": "RESOURCE_NOT_FOUND", "message": "Firewall rule not found"}}
                }
            },
        },
    },
)
async def clone_rule(
    rule_id: UUID,
    new_name: str = Query(..., description="New name for the cloned rule"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clone an existing firewall rule.
    
    **Path Parameters**:
    - ``rule_id``: UUID of the rule to clone
    
    **Query Parameters**:
    - ``new_name``: Name for the cloned rule (required)
    
    **Response**: New firewall rule object (cloned copy).
    """
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


# ============================================================================
# Stats Endpoint
# ============================================================================


@router.get(
    "/stats",
    summary="Get firewall rule statistics",
    description=(
        "Get summary statistics about firewall rules including counts by status, "
        "action, protocol, and workload.\n\n"
        "**Example**: ``GET /api/v1/rules/stats``"
    ),
    responses={
        200: {
            "description": "Rule statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total": 42,
                        "by_status": {"active": 30, "inactive": 8, "pending": 4},
                        "by_action": {"allow": 35, "deny": 7},
                        "by_protocol": {"tcp": 25, "udp": 10, "http": 5, "*": 2},
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def get_rule_stats(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get firewall rule statistics.
    
    **Response**: Dictionary with counts by status, action, protocol, etc.
    """
    service = FirewallService()
    stats = service.get_rule_stats(db)
    return stats


# ============================================================================
# Validate Endpoint
# ============================================================================


@router.post(
    "/validate",
    response_model=dict,
    summary="Validate rule",
    description=(
        "Validate a firewall rule configuration without creating it. "
        "Checks for priority conflicts, duplicate detection, protocol "
        "compatibility, and Azure SDK validation.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "rule_collection_name": "TestRule",\n'
        '  "priority": 100,\n'
        '  "action": "allow",\n'
        '  "protocol": "tcp"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Validation result",
            "content": {
                "application/json": {
                    "examples": {
                        "valid": {
                            "summary": "Rule is valid",
                            "is_valid": True,
                            "warnings": [],
                        },
                        "invalid": {
                            "summary": "Rule has errors",
                            "is_valid": False,
                            "errors": [
                                "A rule with priority 100 already exists",
                                "Protocol 'invalid' is not supported"
                            ],
                        },
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        422: {
            "description": "Validation Error - Invalid request body",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [{"loc": ["body", "priority"], "msg": "input should be a valid integer"}]
                    }
                }
            },
        },
    },
)
async def validate_rule(
    rule: FirewallRuleCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate a firewall rule configuration without saving.
    
    **Request Body**: Full FirewallRuleCreate schema.
    
    **Response**: Validation result with ``is_valid`` flag, ``errors`` list,
    and ``warnings`` list.
    """
    service = FirewallService()
    result = service.validate_firewall_rule(db, rule)
    return result