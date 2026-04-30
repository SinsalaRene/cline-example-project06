"""
Azure Firewall Management API - Main Application.

FastAPI application for managing Azure firewall rules with approval workflows,
role-based access control, and audit trails.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.database import init_db
from app.api.rules import router as rules_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.auth.router import router as auth_router

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.middleware.exception_handler import ExceptionHandlerMiddleware
from app.middleware.validation import ValidationMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Azure Firewall Management API",
    description="API for managing Azure firewall rules with approval workflows and RBAC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ===========================================================================
# Middleware Registration Order (last added = innermost = first to execute)
#
# Middleware execution order in FastAPI/Starlette:
# 1. Request enters from outermost middleware first
# 2. Each middleware processes the request in order
# 3. When middleware calls `await call_next(request)`, it returns after
#    the inner middleware has processed the request
# 4. Response flows back from innermost to outermost
#
# Our order:
#   ValidationMiddleware    -> validates content-type, body size, JSON
#   ExceptionHandlerMiddleware -> catches unhandled exceptions
#   TimingMiddleware        -> measures request duration
#   RequestIDMiddleware     -> adds unique request ID to requests/responses
#   CORSMiddleware          -> handles CORS headers
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


# Include auth router (must be before other routes for proper prefix matching)
app.include_router(auth_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup."""
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Azure Firewall Management API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(rules_router, prefix="/api/v1")
app.include_router(approvals_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions globally."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(
        f"[Request {request_id}] Unhandled global exception: {type(exc).__name__}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "path": str(request.url.path),
                "request_id": request_id,
                "detail": str(exc) if settings.debug else None,
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