"""
Azure Firewall Management API - Main Application.

FastAPI application for managing Azure firewall rules with approval workflows,
role-based access control, and audit trails.

Production-ready with health checks, metrics, structured logging, and error tracking.
"""

import os
import time
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.rules import router as rules_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
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

# ===========================================================================
# Application Factory & Configuration
# ===========================================================================

app = FastAPI(
    title="Azure Firewall Management API",
    description="API for managing Azure firewall rules with approval workflows and RBAC",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=None,  # Using on_event for compatibility
)

# ===========================================================================
# Middleware Registration
# ===========================================================================

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

# ===========================================================================
# Include Routers
# ===========================================================================

# Include auth router first (must be before other routes for proper prefix matching)
app.include_router(auth_router, prefix="/api/v1")

# Include health check routes (before other /api/v1 routes)
app.include_router(health_router)

# Include main routers
app.include_router(rules_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")

# ===========================================================================
# Metrics endpoint (standalone route outside /api/v1)
# ===========================================================================
app.include_router(metrics_router)

# ===========================================================================
# Startup
# ===========================================================================

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


# ===========================================================================
# Request/Response Hooks
# ===========================================================================

@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    """Middleware to record request metrics."""
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


# ===========================================================================
# Root Endpoint
# ===========================================================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Azure Firewall Management API",
        "version": "1.0.0",
        "status": "running",
        "environment": "production" if not settings.debug else "development",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ===========================================================================
# Global Exception Handler
# ===========================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions globally with error tracking."""
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