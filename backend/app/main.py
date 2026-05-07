"""
Azure Firewall Management API - Main Application.

FastAPI application for managing Azure firewall rules with approval workflows,
role-based access control, and audit trails.

Production-ready with health checks, metrics, structured logging, and error tracking.

## API Documentation

This API follows OpenAPI 3.0 / Swagger 2.0 conventions. All endpoints are
documented with request/response examples and error codes.

Access the interactive Swagger UI at ``/docs`` (development only) or
the ReDoc variant at ``/redoc``.

## Authentication

All endpoints (except health checks) require a Bearer token obtained via
``POST /auth/login``. Include it in the ``Authorization`` header:

```
Authorization: Bearer <access_token>
```

## Error Response Format

Every error response follows this structure::

    {
      "error": {
        "code": "VALIDATION_ERROR",
        "message": "Detailed error message",
        "path": "/api/v1/rules",
        "request_id": "req-uuid-here",
        "timestamp": "2026-01-15T10:30:00+00:00",
        "details": [...]   // optional, present for validation errors
      }
    }

## HTTP Error Codes

| Code   | Name                        | Description                                                                     |
|--------|-----------------------------|---------------------------------------------------------------------------------|
| 400    | BAD_REQUEST                 | Malformed request body or syntax error                                          |
| 401    | UNAUTHORIZED                | Missing or invalid authentication credentials                                   |
| 403    | FORBIDDEN                   | Valid credentials but insufficient permissions                                  |
| 404    | NOT_FOUND                   | Resource does not exist                                                         |
| 409    | CONFLICT                    | Duplicate resource (e.g., priority conflict)                                    |
| 422    | VALIDATION_ERROR            | Request body failed Pydantic validation                                          |
| 429    | TOO_MANY_REQUESTS           | Rate limit exceeded                                                             |
| 500    | INTERNAL_ERROR              | Unexpected server-side error                                                    |
| 503    | SERVICE_UNAVAILABLE         | Service temporarily unavailable (health checks)                                 |

## Rate Limiting

- **Login**: 5 attempts per 5 minutes per IP
- **Token refresh**: 20 attempts per 5 minutes per IP
- **General API**: 100 requests per minute per user

Rate limit headers are included in every response:
- ``X-RateLimit-Limit``: Maximum requests in the window
- ``X-RateLimit-Remaining``: Requests remaining
- ``X-RateLimit-Reset``: Unix timestamp when the window resets
"""  # noqa: E501

import os
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# fastapi.openapi.utils.openapi was removed in FastAPI 0.104+, use app.openapi() instead

from app.config import settings
from app.database import init_db
from app.api.rules import router as rules_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.network import router as network_router
from app.auth.router import router as auth_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.metrics import record_request as record_request_metric
from app.logging import setup_logging, get_logger, request_id_var, span_id_var, traceparent_var
from app.logging import create_span_id
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.middleware.exception_handler import ExceptionHandlerMiddleware
from app.middleware.validation import ValidationMiddleware

# Initialize logging
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    json_format=None if settings.debug else settings.log_format,
)
logger = get_logger(__name__)

# Initialize error tracking
from app.error_tracking import setup_error_tracking
setup_error_tracking()


# ============================================================================
# Error Code Reference Dictionary
# ============================================================================

ERROR_CODE_REFERENCE: Dict[str, Any] = {
    "VALIDATION_ERROR": {
        "code": "VALIDATION_ERROR",
        "http_status": 422,
        "description": "Request body failed schema validation",
        "example": {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation error: input should be a valid integer",
                "details": [
                    {
                        "loc": ["body", "priority"],
                        "msg": "input should be a valid integer",
                        "type": "type_error.integer"
                    }
                ]
            }
        }
    },
    "RESOURCE_NOT_FOUND": {
        "code": "RESOURCE_NOT_FOUND",
        "http_status": 404,
        "description": "The requested resource does not exist",
        "example": {
            "error": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "Firewall rule not found",
                "path": "/api/v1/rules/00000000-0000-0000-0000-000000000000"
            }
        }
    },
    "AUTH_REQUIRED": {
        "code": "AUTH_REQUIRED",
        "http_status": 401,
        "description": "Authentication credentials are required",
        "example": {
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "Authentication credentials missing",
                "path": "/api/v1/rules"
            }
        }
    },
    "INVALID_TOKEN": {
        "code": "INVALID_TOKEN",
        "http_status": 401,
        "description": "Authentication token is invalid, expired, or revoked",
        "example": {
            "error": {
                "code": "INVALID_TOKEN",
                "message": "Not authenticated",
                "path": "/api/v1/rules"
            }
        }
    },
    "INSUFFICIENT_PERMISSIONS": {
        "code": "INSUFFICIENT_PERMISSIONS",
        "http_status": 403,
        "description": "User lacks required role or permission",
        "example": {
            "error": {
                "code": "INSUFFICIENT_PERMISSIONS",
                "message": "Insufficient permissions. Required role: FirewallAdministrator",
                "path": "/api/v1/rules"
            }
        }
    },
    "PRIORITY_CONFLICT": {
        "code": "PRIORITY_CONFLICT",
        "http_status": 409,
        "description": "Rule priority conflicts with existing rule",
        "example": {
            "error": {
                "code": "PRIORITY_CONFLICT",
                "message": "A rule with priority 100 already exists",
                "path": "/api/v1/rules"
            }
        }
    },
    "RATE_LIMIT_EXCEEDED": {
        "code": "RATE_LIMIT_EXCEEDED",
        "http_status": 429,
        "description": "Too many requests - rate limit exceeded",
        "example": {
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many login attempts, please try again later.",
                "path": "/api/v1/auth/login"
            }
        }
    },
    "INTERNAL_ERROR": {
        "code": "INTERNAL_ERROR",
        "http_status": 500,
        "description": "Unexpected server-side error",
        "example": {
            "error": {
                "code": "InternalError",
                "message": "Internal server error",
                "path": "/api/v1/rules"
            }
        }
    },
}


# ============================================================================
# Application Factory & Configuration
# ============================================================================

app = FastAPI(
    title="Azure Firewall Management API",
    description=(
        "API for managing Azure firewall rules with approval workflows and RBAC.\n\n"
        "## Features\n"
        "- **Firewall Rules**: CRUD operations for Azure Network Security Group (NSG) rules\n"
        "- **Approval Workflows**: Multi-step approval process with escalation\n"
        "- **Audit Logs**: Complete audit trail of all operations\n"
        "- **Authentication**: JWT-based auth with refresh token rotation\n"
        "- **Azure Integration**: Sync with Azure Network Watcher\n"
        "- **Health & Metrics**: Prometheus-compatible metrics and health checks\n\n"
        "## Quick Start\n"
        "1. Login: ``POST /auth/login`` with username/password\n"
        "2. Use the returned token in the ``Authorization`` header\n"
        "3. Explore endpoints via Swagger UI at ``/docs``\n\n"
        "## Support\n"
        "For issues, contact the platform team or open a GitHub issue."
    ),
    version="1.0.0",
    summary="Azure Firewall Rule Management Platform",
    contact={
        "name": "Platform Team",
        "email": "platform@example.com",
    },
    license_info={
        "name": "Proprietary",
    },
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=None,  # Using on_event for compatibility
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://api.example.com",
            "description": "Production environment",
        },
    ],
)


# ============================================================================
# Middleware Registration
# ============================================================================

# 1. Validation Middleware - validates request content
app.add_middleware(ValidationMiddleware)

# 2. Exception Handler Middleware - catches unhandled exceptions
app.add_middleware(ExceptionHandlerMiddleware)

# 3. Timing Middleware - measures request processing time
app.add_middleware(TimingMiddleware)

# 4. Request ID Middleware - adds unique request ID
app.add_middleware(RequestIDMiddleware)

# 5. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts if settings.debug else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Include Routers
# ============================================================================

# Include auth router first (must be before other routes for proper prefix matching)
app.include_router(auth_router, prefix="/api/v1")

# Include health check routes (before other /api/v1 routes)
app.include_router(health_router)

# Include main routers
app.include_router(rules_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(network_router, prefix="/api/v1")

# ============================================================================
# Metrics endpoint (standalone route outside /api/v1)
# ============================================================================
app.include_router(metrics_router)


# ============================================================================
# Custom OpenAPI Schema Generator
# ============================================================================

def custom_openapi():
    """Generate a custom OpenAPI schema with enhanced documentation.
    
    This function extends the default FastAPI schema with:
    - Global error code reference
    - Enhanced example data for all endpoints
    - Custom schema metadata
    """
    if app.openapi_schema:
        return app.openapi_schema

    # In FastAPI 0.104+, use app.openapi() directly instead of openapi(app)
    openapi_schema = app.openapi()

    # Add external documentation link
    openapi_schema.setdefault("info", {}).setdefault("x-api-info", {
        "documentation": "https://github.com/SinsalaRene/cline-example-project06/wiki/API",
        "swagger_ui_path": "/docs",
        "redoc_ui_path": "/redoc",
    })

    # Add error code reference to the schema
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["responses"] = ERROR_CODE_REFERENCE
    openapi_schema["components"]["schemas"]["Error"] = {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message", "timestamp"],
                "properties": {
                    "code": {"type": "string", "description": "Machine-readable error code"},
                    "message": {"type": "string", "description": "Human-readable error message"},
                    "path": {"type": "string", "description": "Request path where error occurred"},
                    "request_id": {"type": "string", "description": "Unique request identifier for tracing"},
                    "timestamp": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp"},
                    "details": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Additional error details (present for validation errors)"
                    }
                },
                "description": "Standard error response body"
            }
        },
        "description": "Global error response format"
    }
    
    # Add request ID header
    openapi_schema.setdefault("components", {}).setdefault("headers", {})
    openapi_schema["components"]["headers"]["RequestID"] = {
        "name": "X-Request-Id",
        "in": "header",
        "schema": {"type": "string", "format": "uuid"},
        "description": "Unique request identifier assigned to every request",
        "explode": False,
    }
    openapi_schema["components"]["headers"]["SpanId"] = {
        "name": "X-Span-Id",
        "in": "header",
        "schema": {"type": "string"},
        "description": "Distributed tracing span identifier",
        "explode": False,
    }

    # Add rate limit headers
    openapi_schema["components"]["headers"]["RateLimitLimit"] = {
        "name": "X-RateLimit-Limit",
        "in": "header",
        "schema": {"type": "integer"},
        "description": "Maximum number of requests allowed in the current window",
        "explode": False,
    }
    openapi_schema["components"]["headers"]["RateLimitRemaining"] = {
        "name": "X-RateLimit-Remaining",
        "in": "header",
        "schema": {"type": "integer"},
        "description": "Number of requests remaining in the current window",
        "explode": False,
    }

    # Add error responses to all paths
    common_error_responses = {
        "401": {
            "description": "Unauthorized - Invalid or missing authentication token",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "examples": {
                        "missing_token": ERROR_CODE_REFERENCE["AUTH_REQUIRED"]["example"],
                        "invalid_token": ERROR_CODE_REFERENCE["INVALID_TOKEN"]["example"],
                    },
                },
            },
        },
        "403": {
            "description": "Forbidden - Insufficient permissions",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "examples": {
                        "insufficient_permissions": ERROR_CODE_REFERENCE["INSUFFICIENT_PERMISSIONS"]["example"],
                    },
                },
            },
        },
        "422": {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "examples": {
                        "validation_error": ERROR_CODE_REFERENCE["VALIDATION_ERROR"]["example"],
                    },
                },
            },
        },
        "429": {
            "description": "Too Many Requests",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "examples": {
                        "rate_limit": ERROR_CODE_REFERENCE["RATE_LIMIT_EXCEEDED"]["example"],
                    },
                },
            },
        },
        "500": {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"},
                    "examples": {
                        "internal_error": ERROR_CODE_REFERENCE["INTERNAL_ERROR"]["example"],
                    },
                },
            },
        },
    }

    # Apply common error responses to all operations
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "responses" in operation:
                operation["responses"].update(common_error_responses)
    
    # Set tags descriptions
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and authorization endpoints"
        },
        {
            "name": "rules",
            "description": "Firewall rule management - create, list, update, delete, search, and bulk operations"
        },
        {
            "name": "approvals",
            "description": "Approval workflow management - request, approve, reject, escalate, and bulk operations"
        },
        {
            "name": "audit",
            "description": "Audit log management - view, search, filter, and export audit entries"
        },
        {
            "name": "health",
            "description": "Health check probes for Kubernetes and monitoring systems"
        },
        {
            "name": "metrics",
            "description": "Prometheus-compatible application and system metrics"
        },
    ]

    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi  # type: ignore[assignment]


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup."""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Application shutting down")


# ============================================================================
# Request/Response Hooks
# ============================================================================

@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    """Middleware to record request metrics.
    
    Records timing, request ID propagation, distributed tracing headers,
    and emits structured log entries for all HTTP requests.
    """
    start_time = time.perf_counter()

    # Create span ID for distributed tracing
    span_id = create_span_id()
    span_id_var.set(span_id)

    # Extract traceparent from headers
    traceparent = request.headers.get("traceparent", "N/A")
    traceparent_var.set(traceparent)

    # Process request
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        status_code = 500
        raise
    finally:
        # Record metrics
        duration = (time.perf_counter() - start_time) * 1000
        endpoint = request.url.path

        # Record request metric
        try:
            record_request_metric(
                method=request.method,
                endpoint=endpoint,
                status_code=status_code,
            )
        except Exception:
            pass  # Metrics should never crash the request

        # Log request
        if status_code >= 500:
            logger.error(
                f"HTTP {request.method} {endpoint} -> {status_code} in {duration:.1f}ms",
                extra={"request_id": getattr(request.state, "request_id", "N/A")},
            )
        elif status_code >= 400:
            logger.warning(
                f"HTTP {request.method} {endpoint} -> {status_code} in {duration:.1f}ms",
                extra={"request_id": getattr(request.state, "request_id", "N/A")},
            )

    # Set response headers
    response.headers["X-Request-Id"] = getattr(request.state, "request_id", "N/A")
    response.headers["X-Span-Id"] = span_id

    return response


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get(
    "/",
    tags=["root"],
    summary="API root - Get API information",
    description=(
        "Returns basic API information including name, version, current status, "
        "and environment. This is an informational endpoint, not an auth gate."
    ),
    responses={
        200: {
            "description": "API information",
            "content": {
                "application/json": {
                    "example": {
                        "name": "Azure Firewall Management API",
                        "version": "1.0.0",
                        "status": "running",
                        "environment": "development",
                        "timestamp": "2026-01-15T10:30:00+00:00",
                    }
                }
            },
        }
    },
)
async def root():
    """Root endpoint."""
    return {
        "name": "Azure Firewall Management API",
        "version": "1.0.0",
        "status": "running",
        "environment": "production" if not settings.debug else "development",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Global Exception Handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions globally with error tracking.
    
    Captures unhandled exceptions, reports them via the error tracking service,
    and returns a structured JSON error response.
    
    In production (non-debug mode), the detailed exception message is hidden
    from the client for security.
    """
    from app.error_tracking import capture_exception, ErrorCategory

    request_id = getattr(request.state, "request_id", "N/A")
    error_type = type(exc).__name__

    # Track the error
    try:
        capture_exception(
            error=exc,
            category=ErrorCategory.internal.value,
            severity="error",
            context={
                "endpoint": str(request.url.path),
                "method": request.method,
                "query_params": dict(request.query_params) if hasattr(request, "query_params") else {},
                "error_type": error_type,
            },
            request_id=request_id,
        )
    except Exception:
        logger.error(f"Failed to capture error: {exc}", exc_info=True)

    logger.error(
        f"[Request {request_id}] Unhandled global exception: {error_type}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": error_type,
                "message": "Internal server error" if not settings.debug else str(exc),
                "path": str(request.url.path),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )