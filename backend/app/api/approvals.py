"""
API routes for Approval workflow management.

This module provides endpoints for managing approval requests including
CRUD operations, approve/reject/escalate workflows, bulk operations,
export, and request search.

## Request Format

All POST/PUT endpoints accept JSON bodies matching the corresponding Pydantic
schemas defined in ``app.schemas.approval``.

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
| CONFLICT         | 409  | Duplicate resource / conflicting action    |
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
from app.schemas.approval import (
    ApprovalRequestCreate,
    ApprovalRequestUpdate,
    ApprovalRequestResponse,
    PaginatedApprovalResponse,
)
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.models.approval import ApprovalStatus

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _convert_model(item) -> dict:
    """Convert a raw SQLAlchemy model instance to a JSON-compatible dict."""
    if isinstance(item, dict):
        data = dict(item)
    elif hasattr(item, '__dict__') and not hasattr(item, '__table__'):
        data = {k: v for k, v in item.__dict__.items() if not k.startswith('_sa_')}
    elif hasattr(item, '__table__'):
        data = {}
        for col_name in item.__table__.columns.keys():
            val = getattr(item, col_name, None)
            data[col_name] = val
    else:
        return item

    # Parse JSON fields stored as strings
    for field in ("approvals", "metadata", "old_value", "new_value"):
        val = data.get(field)
        if isinstance(val, str):
            try:
                data[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                data[field] = None

    # Normalize status to lowercase
    if "status" in data and data["status"] is not None:
        data["status"] = str(data["status"]).lower()

    return data


def _convert_paged(result_dict):
    """Convert paginated results that may contain raw models."""
    if not isinstance(result_dict, dict):
        return result_dict
    if "items" in result_dict and isinstance(result_dict["items"], list):
        result_dict["items"] = [_convert_model(i) for i in result_dict["items"]]
    return result_dict


# ============================================================================
# Approval Request Endpoints
# ============================================================================


@router.get(
    "",
    response_model=PaginatedApprovalResponse,
    summary="List approval requests",
    description=(
        "Get a paginated list of approval requests. Supports filtering by "
        "status, type, approver, and requester.\n\n"
        "**Example**: ``GET /api/v1/approvals?status=pending&page=1&page_size=10``"
    ),
    responses={
        200: {
            "description": "Successful list of approval requests",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "type": "firewall_rule",
                                "title": "Allow HTTPS from internal network",
                                "requester_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                                "approver_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                                "status": "pending",
                                "priority": "normal",
                                "due_date": "2026-01-22T10:00:00+00:00",
                                "metadata": {"rule_id": "rule-123"},
                                "created_at": "2026-01-15T10:00:00+00:00",
                                "updated_at": "2026-01-15T10:00:00+00:00",
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                    }
                }
            },
        },
        401: {"description": "Unauthorized - Missing or invalid auth token"},
        422: {"description": "Validation error - Invalid page or page_size parameter"},
    },
)
async def list_approval_requests(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page (1-100)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, approved, rejected, cancelled, escalated, expired)"),
    type_filter: Optional[str] = Query(None, description="Filter by request type"),
    approver_id: Optional[UUID] = Query(None, description="Filter by approver user ID"),
    requester_id: Optional[UUID] = Query(None, description="Filter by requester user ID"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List approval requests with pagination and filtering.
    
    **Query Parameters**:
    - ``page``: Page number (default 1)
    - ``page_size``: Items per page (default 50, range 1-100)
    - ``status``: Filter by approval status
    - ``type``: Filter by request type (e.g., firewall_rule)
    - ``approver_id``: Filter by approver UUID
    - ``requester_id``: Filter by requester UUID
    
    **Response**: Paginated list of approval request objects.
    """
    service = ApprovalService()
    result = service.get_approval_requests(
        db=db,
        status=status_filter,
        type_filter=type_filter,
        approver_id=approver_id,
        requester_id=requester_id,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


@router.get(
    "/{approval_id}",
    response_model=ApprovalRequestResponse,
    summary="Get approval request",
    description=(
        "Retrieve a single approval request by its UUID including all "
        "approval chain details.\n\n"
        "**Example**: ``GET /api/v1/approvals/a1b2c3d4-e5f6-7890-abcd-ef1234567890``"
    ),
    responses={
        200: {
            "description": "Approval request details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "type": "firewall_rule",
                        "title": "Allow HTTPS from internal network",
                        "description": "Request to allow HTTPS traffic from the internal network",
                        "requester_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "approver_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                        "status": "pending",
                        "priority": "normal",
                        "due_date": "2026-01-22T10:00:00+00:00",
                        "metadata": {"rule_id": "rule-123"},
                        "created_at": "2026-01-15T10:00:00+00:00",
                        "updated_at": "2026-01-15T10:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Approval request does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Approval request not found",
                        }
                    }
                }
            },
        },
    },
)
async def get_approval_request(
    approval_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single approval request by ID.
    
    **Path Parameters**:
    - ``approval_id``: UUID of the approval request
    
    **Response**: Approval request object or 404 if not found.
    """
    service = ApprovalService()
    approval = service.get_approval_request(db, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return _convert_model(approval)


@router.post(
    "",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create approval request",
    description=(
        "Create a new approval request. The request will be validated for "
        "completeness and added to the approval chain.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "type": "firewall_rule",\n'
        '  "title": "Allow HTTPS from internal network",\n'
        '  "description": "Request to allow HTTPS traffic",\n'
        '  "target_id": "rule-123",\n'
        '  "priority": "normal"\n'
        "}\n"
        "```"
    ),
    responses={
        201: {
            "description": "Approval request created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "type": "firewall_rule",
                        "title": "Allow HTTPS from internal network",
                        "status": "pending",
                        "priority": "normal",
                        "created_at": "2026-01-15T10:00:00+00:00",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Invalid approval data",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Validation error: title is required",
                        }
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        409: {
            "description": "Conflict - Duplicate approval request",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CONFLICT",
                            "message": "A pending approval request for this resource already exists",
                        }
                    }
                }
            },
        },
    },
)
async def create_approval_request(
    request: ApprovalRequestCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new approval request.
    
    **Request Body**: ApprovalRequestCreate schema with required fields:
    - ``type``: Type of resource needing approval (required)
    - ``title``: Short title for the request (required)
    - ``description``: Detailed description (optional)
    - ``target_id``: ID of the target resource (optional)
    - ``priority``: Request priority - "low", "normal", "high", "critical" (optional)
    - ``due_date``: Due date for the request (optional)
    - ``metadata``: Additional metadata dict (optional)
    
    **Response**: Created approval request object.
    """
    service = ApprovalService()
    new_request = service.create_approval_request(
        db=db,
        type=request.type,
        title=request.title,
        description=request.description,
        requester_id=current_user.object_id,
        target_id=request.target_id,
        priority=request.priority,
        due_date=request.due_date,
        metadata=request.metadata,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="create",
        resource_type="approval_request",
        resource_id=str(new_request.id),
        new_value={"type": request.type, "title": request.title},
        correlation_id=None,
    )
    return _convert_model(new_request)


@router.put(
    "/{approval_id}",
    response_model=ApprovalRequestResponse,
    summary="Update approval request",
    description=(
        "Update an existing approval request. Only provided fields will be "
        "updated (partial update).\n\n"
        "**Example Request**:\n"
        "```json\n"
        '{\n'
        '  "priority": "high"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Approval request updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "type": "firewall_rule",
                        "title": "Allow HTTPS from internal network",
                        "priority": "high",
                        "status": "pending",
                        "updated_at": "2026-01-15T11:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Approval request not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Approval request not found",
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
                            "message": "Validation error: priority must be one of",
                        }
                    }
                }
            },
        },
    },
)
async def update_approval_request(
    approval_id: UUID,
    request: ApprovalRequestUpdate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an approval request (partial update).
    
    **Path Parameters**:
    - ``approval_id``: UUID of the approval request to update
    
    **Request Body**: Partial ApprovalRequestUpdate - only fields to update.
    
    **Response**: Updated approval request object or error.
    """
    service = ApprovalService()
    update_data = request.model_dump(exclude_unset=True)
    updated_request = service.update_approval_request(
        db=db,
        approval_id=approval_id,
        **update_data,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="update",
        resource_type="approval_request",
        resource_id=str(approval_id),
        new_value=update_data,
        correlation_id=None,
    )
    return _convert_model(updated_request)


# ============================================================================
# Approval Action Endpoints
# ============================================================================


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalRequestResponse,
    summary="Approve request",
    description=(
        "Approve an approval request. This triggers the approval workflow "
        "and notifies the relevant parties.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "comment": "Looks good, approved"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Request approved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "status": "approved",
                        "updated_at": "2026-01-15T11:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        403: {
            "description": "Forbidden - Current user is not the assigned approver",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INSUFFICIENT_PERMISSIONS",
                            "message": "You are not the assigned approver",
                        }
                    }
                }
            },
        },
        404: {
            "description": "Not Found - Request does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Approval request not found",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Conflict - Request already has a decision",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CONFLICT",
                            "message": "This request has already been approved or rejected",
                        }
                    }
                }
            },
        },
    },
)
async def approve_request(
    approval_id: UUID,
    comment: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve an approval request.
    
    **Path Parameters**:
    - ``approval_id``: UUID of the approval request to approve
    
    **Query Parameters**:
    - ``comment``: Optional approval comment
    
    **Response**: Updated approval request with status "approved".
    """
    service = ApprovalService()
    updated = service.approve_request(
        db=db,
        approval_id=approval_id,
        approver_id=current_user.object_id,
        comment=comment,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="approve",
        resource_type="approval_request",
        resource_id=str(approval_id),
        new_value={"approved_by": str(current_user.object_id), "comment": comment},
        correlation_id=None,
    )
    return _convert_model(updated)


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalRequestResponse,
    summary="Reject request",
    description=(
        "Reject an approval request. The requester will be notified.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "comment": "This does not meet security requirements"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Request rejected successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "status": "rejected",
                        "updated_at": "2026-01-15T11:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        403: {
            "description": "Forbidden - Not the assigned approver",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INSUFFICIENT_PERMISSIONS",
                            "message": "You are not the assigned approver",
                        }
                    }
                }
            },
        },
        404: {
            "description": "Not Found - Request does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Approval request not found",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Conflict - Request already decided",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CONFLICT",
                            "message": "This request has already been approved or rejected",
                        }
                    }
                }
            },
        },
    },
)
async def reject_request(
    approval_id: UUID,
    comment: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject an approval request.
    
    **Path Parameters**:
    - ``approval_id``: UUID of the approval request to reject
    
    **Query Parameters**:
    - ``comment``: Optional rejection comment (required for audit)
    
    **Response**: Updated approval request with status "rejected".
    """
    service = ApprovalService()
    updated = service.reject_request(
        db=db,
        approval_id=approval_id,
        approver_id=current_user.object_id,
        comment=comment,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="reject",
        resource_type="approval_request",
        resource_id=str(approval_id),
        new_value={"rejected_by": str(current_user.object_id), "comment": comment},
        correlation_id=None,
    )
    return _convert_model(updated)


@router.post(
    "/{approval_id}/escalate",
    response_model=ApprovalRequestResponse,
    summary="Escalate request",
    description=(
        "Escalate an approval request to a higher priority or different approver.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "new_approver_id": "user-uuid-here",\n'
        '  "reason": "Urgent production issue"\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Request escalated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "priority": "urgent",
                        "status": "escalated",
                        "updated_at": "2026-01-15T11:00:00+00:00",
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
        404: {
            "description": "Not Found - Request does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RESOURCE_NOT_FOUND",
                            "message": "Approval request not found",
                        }
                    }
                }
            },
        },
    },
)
async def escalate_request(
    approval_id: UUID,
    new_approver_id: Optional[UUID] = None,
    reason: Optional[str] = None,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Escalate an approval request.
    
    **Path Parameters**:
    - ``approval_id``: UUID of the approval request to escalate
    
    **Query Parameters**:
    - ``new_approver_id``: UUID of new approver (optional)
    - ``reason``: Reason for escalation (optional)
    
    **Response**: Updated approval request with escalated status.
    """
    service = ApprovalService()
    updated = service.escalate_request(
        db=db,
        approval_id=approval_id,
        new_approver_id=new_approver_id,
        reason=reason,
        escalated_by=current_user.object_id,
    )
    AuditService().log_action(
        db=db,
        user_id=current_user.object_id,
        action="escalate",
        resource_type="approval_request",
        resource_id=str(approval_id),
        new_value={"escalated_by": str(current_user.object_id), "reason": reason},
        correlation_id=None,
    )
    return _convert_model(updated)


# ============================================================================
# Bulk Operation Endpoints
# ============================================================================


@router.post(
    "/bulk",
    response_model=dict,
    summary="Bulk approve/reject requests",
    description=(
        "Approve or reject multiple approval requests in a single request. "
        "Each request is processed independently.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "action": "approve",\n'
        '  "comment": "Bulk approval",\n'
        '  "approval_ids": ["a1b2c3d4...", "b2c3d4e5..."]\n'
        "}\n"
        "```"
    ),
    responses={
        200: {
            "description": "Bulk operation results",
            "content": {
                "application/json": {
                    "example": {
                        "approved": 2,
                        "rejected": 0,
                        "errors": [],
                        "results": [
                            {"id": "a1b2c3d4...", "status": "approved"},
                            {"id": "b2c3d4e5...", "status": "approved"},
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - No IDs or invalid action",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "No approval IDs provided",
                        }
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def bulk_approve_reject(
    action: str = Query(..., description="Action: approve or reject"),
    comment: Optional[str] = Query(None, description="Comment for the action"),
    approval_ids: List[UUID] = Query(..., description="List of approval request IDs"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk approve or reject multiple approval requests.
    
    **Query Parameters**:
    - ``action``: "approve" or "reject" (required)
    - ``comment``: Optional comment for the action
    - ``approval_ids``: List of approval request UUIDs (required)
    
    **Response**: Summary with counts and per-request results.
    """
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'.")
    if not approval_ids:
        raise HTTPException(status_code=400, detail="No approval IDs provided")

    service = ApprovalService()
    results = []
    errors = []
    approved_count = 0
    rejected_count = 0

    for approval_id in approval_ids:
        try:
            if action == "approve":
                service.approve_request(
                    db=db,
                    approval_id=approval_id,
                    approver_id=current_user.object_id,
                    comment=comment,
                )
                approved_count += 1
            else:
                service.reject_request(
                    db=db,
                    approval_id=approval_id,
                    approver_id=current_user.object_id,
                    comment=comment,
                )
                rejected_count += 1
            results.append({"id": str(approval_id), "action": action})
        except Exception as e:
            errors.append({"id": str(approval_id), "error": str(e)})

    return {
        "approved": approved_count,
        "rejected": rejected_count,
        "errors": errors,
        "results": results,
    }


# ============================================================================
# Search Endpoint
# ============================================================================


@router.get(
    "/search",
    response_model=PaginatedApprovalResponse,
    summary="Search approval requests",
    description=(
        "Search approval requests by free-text query and optional filters.\n\n"
        "**Example**: ``GET /api/v1/approvals/search?q=HTTPS&status=pending``"
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
                                "type": "firewall_rule",
                                "title": "Allow HTTPS from internal network",
                                "status": "pending",
                                "priority": "normal",
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
            "description": "Validation Error - Search query required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [{"loc": ["query", "q"], "msg": "Field required", "type": "missing"}]
                    }
                }
            },
        },
    },
)
async def search_approval_requests(
    q: str = Query(..., min_length=1, description="Search query (minimum 1 character)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    type_filter: Optional[str] = Query(None, description="Filter by type"),
    approver_id: Optional[UUID] = Query(None, description="Filter by approver"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search approval requests by query and filters.
    
    **Query Parameters**:
    - ``q``: Search query (required, min 1 char)
    - ``status``: Filter by status
    - ``type``: Filter by type
    - ``approver_id``: Filter by approver UUID
    - ``page``: Page number (default 1)
    - ``page_size``: Items per page (default 50, max 100)
    
    **Response**: Paginated search results.
    """
    service = ApprovalService()
    result = service.search_approval_requests(
        db=db,
        query=q,
        status=status_filter,
        type_filter=type_filter,
        approver_id=approver_id,
        page=page,
        page_size=page_size,
    )
    return _convert_paged(result)


# ============================================================================
# Export Endpoint
# ============================================================================


@router.get(
    "/export",
    summary="Export approval requests",
    description=(
        "Export approval requests to CSV or JSON format. CSV returns a file "
        "download with ``Content-Disposition`` header.\n\n"
        "**Example**: ``GET /api/v1/approvals/export?format=json``"
    ),
    responses={
        200: {
            "description": "Exported data",
            "content": {
                "application/json": {
                    "example": {
                        "export_format": "json",
                        "total": 2,
                        "requests": [
                            {"id": "a1b2c3d4...", "title": "Allow HTTPS", "status": "pending"},
                            {"id": "b2c3d4e5...", "title": "Allow SSH", "status": "approved"},
                        ],
                    }
                },
                "text/csv": {
                    "example": "id,title,type,status,priority\na1b2...,Allow HTTPS,firewall_rule,pending,normal"
                },
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def export_approval_requests(
    format: str = Query("json", description="Export format (json or csv)"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    type_filter: Optional[str] = Query(None, description="Filter by type"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export approval requests to CSV or JSON.
    
    **Query Parameters**:
    - ``format``: Export format - ``json`` or ``csv`` (default ``json``)
    - ``status``: Filter by status (optional)
    - ``type``: Filter by type (optional)
    
    **Response**: JSON object with requests or CSV file download.
    """
    service = ApprovalService()
    result = service.get_approval_requests(
        db=db,
        status=status_filter,
        type_filter=type_filter,
        page=1,
        page_size=10000,
    )

    if format == "csv":
        import io
        output = io.StringIO()
        if result.get("items"):
            writer = __import__('csv').DictWriter(
                output,
                fieldnames=["id", "title", "type", "status", "priority", "requester_id", "approver_id"],
            )
            writer.writeheader()
            for item in result["items"]:
                row = {k: str(v) if v else "" for k, v in item.dict().items()}
                writer.writerow(row)
        return FastAPIResponse(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="approval_requests_export.csv"'},
        )

    return {"export_format": "json", "total": result.get("total", 0), "requests": result}


# ============================================================================
# Stats Endpoint
# ============================================================================


@router.get(
    "/stats",
    summary="Get approval request statistics",
    description=(
        "Get summary statistics about approval requests including counts "
        "by status, type, and priority.\n\n"
        "**Example**: ``GET /api/v1/approvals/stats``"
    ),
    responses={
        200: {
            "description": "Approval statistics",
            "content": {
                "application/json": {
                    "example": {
                        "total": 100,
                        "by_status": {"pending": 30, "approved": 50, "rejected": 15, "expired": 5},
                        "by_type": {"firewall_rule": 60, "network_change": 40},
                        "by_priority": {"low": 10, "normal": 60, "high": 25, "critical": 5},
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def get_approval_stats(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get approval request statistics.
    
    **Response**: Dictionary with counts by status, type, priority, etc.
    """
    service = ApprovalService()
    stats = service.get_approval_stats(db)
    return stats


# ============================================================================
# Validate Endpoint
# ============================================================================


@router.post(
    "/validate",
    response_model=dict,
    summary="Validate request",
    description=(
        "Validate an approval request configuration without creating it.\n\n"
        "**Example Request**:\n"
        "```json\n"
        "{\n"
        '  "type": "firewall_rule",\n'
        '  "title": "Allow HTTPS from internal network"\n'
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
                            "summary": "Request is valid",
                            "is_valid": True,
                            "warnings": [],
                        },
                        "invalid": {
                            "summary": "Request has errors",
                            "is_valid": False,
                            "errors": ["Title is required"],
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
                        "detail": [{"loc": ["body", "title"], "msg": "Field required", "type": "missing"}]
                    }
                }
            },
        },
    },
)
async def validate_approval_request(
    request: ApprovalRequestCreate,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate an approval request without saving.
    
    **Request Body**: Full ApprovalRequestCreate schema.
    
    **Response**: Validation result with ``is_valid`` flag and ``errors``/``warnings`` lists.
    """
    service = ApprovalService()
    result = service.validate_approval_request(db, request)
    return result