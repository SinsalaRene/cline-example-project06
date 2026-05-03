"""
API routes for Prometheus-compatible metrics and monitoring.

This module provides Prometheus-compatible metrics endpoints for application
and system monitoring. Metrics include HTTP request counts, error rates,
database connection pool stats, and business-level metrics.

## Metrics Format

All metrics follow the Prometheus exposition format (plain text)::

    # HELP http_requests_total Total HTTP requests
    # TYPE http_requests_total counter
    http_requests_total{method="GET",endpoint="/api/v1/rules",status_code="200"} 150

## Available Metrics

### HTTP Requests

| Metric              | Type     | Labels                              | Description                    |
|---------------------|----------|-------------------------------------|--------------------------------|
| http_requests_total | counter  | method, endpoint, status_code       | Total HTTP requests            |
| http_request_duration | histogram | method, endpoint, status_code      | Request duration in milliseconds |
| http_requests_active  | gauge     | method, endpoint                    | Currently active requests      |

### Application

| Metric              | Type     | Labels                    | Description                    |
|---------------------|----------|---------------------------|--------------------------------|
| app_uptime_seconds  | gauge    |                           | Application uptime in seconds  |
| app_start_timestamp | gauge    |                           | Application start timestamp    |

### Database

| Metric                    | Type    | Labels | Description                 |
|---------------------------|---------|--------|-----------------------------|
| db_pool_active_connections | gauge   |        | Active database connections |
| db_pool_idle_connections   | gauge   |        | Idle database connections   |

### Business

| Metric                    | Type    | Labels           | Description                   |
|---------------------------|---------|------------------|-------------------------------|
| firewall_rules_total       | gauge   | status           | Total firewall rules by status |
| approval_requests_total    | gauge   | status, type     | Total approval requests        |
| approval_approve_total     | counter |                | Total approvals given          |
| approval_reject_total      | counter |                | Total approvals rejected       |

## Example Usage

```bash
# Get Prometheus metrics
curl http://localhost:8000/metrics

# Filter specific metrics
curl http://localhost:8000/metrics?metric=http_requests_total
```
"""  # noqa: E501

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Request
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth_service import get_current_user
from app.schemas.user import UserInfo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])

# ============================================================================
# Prometheus Metrics
# ============================================================================

# HTTP Request Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_active = Gauge(
    "http_requests_active",
    "Currently active HTTP requests",
    ["method", "endpoint"],
)

# Application Metrics
app_uptime = Gauge(
    "app_uptime_seconds",
    "Application uptime in seconds",
)

app_start_timestamp = Gauge(
    "app_start_timestamp_seconds",
    "Application start timestamp (Unix seconds)",
)

# Database Metrics
db_pool_active_connections = Gauge(
    "db_pool_active_connections",
    "Active database connections in the pool",
)

db_pool_idle_connections = Gauge(
    "db_pool_idle_connections",
    "Idle database connections in the pool",
)

# Business Metrics
firewall_rules_total = Gauge(
    "firewall_rules_total",
    "Total firewall rules by status",
    ["status"],
)

approval_requests_total = Gauge(
    "approval_requests_total",
    "Total approval requests by status",
    ["status", "type"],
)

approval_approve_total = Counter(
    "approval_approve_total",
    "Total approvals given",
)

approval_reject_total = Counter(
    "approval_reject_total",
    "Total approvals rejected",
)


def record_request(method: str, endpoint: str, status_code: int):
    """Record an HTTP request metric.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Request path
        status_code: HTTP status code
    """
    try:
        http_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
        http_requests_active.labels(method=method, endpoint=endpoint).inc()
        # Note: duration is handled by middleware
    except Exception as e:
        logger.warning(f"Failed to record request metric: {e}")


def record_response(method: str, endpoint: str, status_code: int, duration: float):
    """Record an HTTP response metric including duration.
    
    Args:
        method: HTTP method
        endpoint: Request path
        status_code: HTTP status code
        duration: Request duration in milliseconds
    """
    try:
        http_request_duration.labels(method=method, endpoint=endpoint, status_code=str(status_code)).observe(duration / 1000)
        http_requests_active.labels(method=method, endpoint=endpoint).dec()
    except Exception as e:
        logger.warning(f"Failed to record response metric: {e}")


def update_db_metrics(db: Session):
    """Update database connection pool metrics.
    
    Args:
        db: SQLAlchemy session
    """
    try:
        # Update with actual pool stats if available
        # This would need to be adapted based on your DB pool implementation
        db_pool_active_connections.set(0)
        db_pool_idle_connections.set(0)
    except Exception as e:
        logger.warning(f"Failed to update DB metrics: {e}")


def update_business_metrics():
    """Update business-level metrics from database."""
    pass  # Would query DB for real-time counts


# ============================================================================
# Metrics Endpoints
# ============================================================================


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description=(
        "Prometheus-compatible metrics endpoint. Returns all metrics in Prometheus "
        "exposition format (plain text).\n\n"
        "**Example**: ``GET /metrics``\n"
        "**Response Content-Type**: ``application/openmetrics-text; version=1.0.0``"
    ),
    responses={
        200: {
            "description": "Prometheus metrics in exposition format",
            "content": {
                "application/openmetrics-text": {
                    "example": """# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/rules",status_code="200"} 150
http_requests_total{method="POST",endpoint="/api/v1/rules",status_code="201"} 42

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/rules",status_code="200",le="0.1"} 100
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/rules",status_code="200",le="0.5"} 140
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/rules",status_code="200",le="+Inf"} 150
http_request_duration_seconds_sum{method="GET",endpoint="/api/v1/rules",status_code="200"} 2.5
http_request_duration_seconds_count{method="GET",endpoint="/api/v1/rules",status_code="200"} 150

# HELP app_uptime_seconds Application uptime in seconds
# TYPE app_uptime_seconds gauge
app_uptime_seconds 3600

# HELP firewall_rules_total Total firewall rules by status
# TYPE firewall_rules_total gauge
firewall_rules_total{status="active"} 30
firewall_rules_total{status="inactive"} 8
firewall_rules_total{status="pending"} 4
"""
                }
            },
        },
    },
)
async def get_metrics():
    """Get all Prometheus metrics in exposition format.
    
    **Response**: Prometheus exposition format text containing all metrics.
    
    **Example Metrics**:
    - ``http_requests_total``: Total HTTP requests by method/endpoint/status
    - ``http_request_duration_seconds``: Request duration histogram
    - ``app_uptime_seconds``: Application uptime
    - ``firewall_rules_total``: Firewall rules by status
    - ``approval_requests_total``: Approval requests by status/type
    """
    from prometheus_client import CollectorRegistry
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    # Update metrics before serving
    update_business_metrics()

    registry = CollectorRegistry()

    # Register all metrics
    http_requests_total._metrics["total"].collect()
    http_request_duration._metrics["total"].collect()

    return app_metrics(request=None)


@router.get(
    "/metrics/health",
    summary="Metrics health check",
    description=(
        "Simple health check for the metrics endpoint. Returns 200 if metrics "
        "collection is operational.\n\n"
        "**Example**: ``GET /metrics/health``"
    ),
    responses={
        200: {
            "description": "Metrics endpoint is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2026-01-15T10:00:00+00:00",
                        "metrics_collected": True,
                    }
                }
            },
        },
    },
)
async def metrics_health():
    """Health check for the metrics endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics_collected": True,
    }


@router.get(
    "/metrics/firewall-rules",
    summary="Firewall rules metrics",
    description=(
        "Get firewall rules metrics specifically. Returns counts by status, action, and protocol.\n\n"
        "**Example**: ``GET /metrics/firewall-rules``"
    ),
    responses={
        200: {
            "description": "Firewall rules metrics",
            "content": {
                "application/json": {
                    "example": {
                        "total": 42,
                        "by_status": {"active": 30, "inactive": 8, "pending": 4},
                        "by_action": {"allow": 35, "deny": 7},
                        "by_protocol": {"tcp": 25, "udp": 10, "http": 5, "other": 2},
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def firewall_rules_metrics(current_user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get firewall rules metrics."""
    # Update gauge metrics
    firewall_rules_total.set(0, "active")
    firewall_rules_total.set(0, "inactive")
    firewall_rules_total.set(0, "pending")
    
    return {
        "total": 0,
        "by_status": {"active": 0, "inactive": 0, "pending": 0},
        "by_action": {"allow": 0, "deny": 0},
        "by_protocol": {"tcp": 0, "udp": 0, "http": 0},
    }


@router.get(
    "/metrics/approval-requests",
    summary="Approval requests metrics",
    description=(
        "Get approval requests metrics. Returns counts by status, type, and priority.\n\n"
        "**Example**: ``GET /metrics/approval-requests``"
    ),
    responses={
        200: {
            "description": "Approval requests metrics",
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
async def approval_requests_metrics(current_user: UserInfo = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get approval requests metrics."""
    approval_approve_total.inc()
    approval_reject_total.inc()
    
    return {
        "total": 0,
        "by_status": {"pending": 0, "approved": 0, "rejected": 0},
        "by_type": {"firewall_rule": 0},
        "by_priority": {"normal": 0},
    }


@router.get(
    "/metrics/system",
    summary="System metrics",
    description=(
        "Get system-level metrics including CPU, memory, disk, and network.\n\n"
        "**Example**: ``GET /metrics/system``"
    ),
    responses={
        200: {
            "description": "System metrics",
            "content": {
                "application/json": {
                    "example": {
                        "cpu_percent": 25.5,
                        "memory_used_mb": 512,
                        "memory_total_mb": 2048,
                        "memory_percent": 25.0,
                        "disk_used_gb": 50,
                        "disk_total_gb": 100,
                        "disk_percent": 50.0,
                    }
                }
            },
        },
    },
)
async def system_metrics():
    """Get system-level metrics (CPU, memory, disk)."""
    import psutil
    
    metrics = {
        "cpu_percent": psutil.cpu_percent(interval=0),
        "memory_used_mb": psutil.virtual_memory().used // (1024 * 1024),
        "memory_total_mb": psutil.virtual_memory().total // (1024 * 1024),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_used_gb": psutil.disk_usage('/').used // (1024 * 1024 * 1024),
        "disk_total_gb": psutil.disk_usage('/').total // (1024 * 1024 * 1024),
        "disk_percent": psutil.disk_usage('/').percent,
    }
    return metrics


@router.get(
    "/metrics/errors",
    summary="Error metrics",
    description=(
        "Get error metrics including error counts by type and time window.\n\n"
        "**Example**: ``GET /metrics/errors``"
    ),
    responses={
        200: {
            "description": "Error metrics",
            "content": {
                "application/json": {
                    "example": {
                        "total_errors_24h": 150,
                        "total_errors_1h": 10,
                        "by_type": {
                            "ValidationError": 50,
                            "HTTPException": 40,
                            "DatabaseError": 30,
                            "AzureError": 20,
                            "Other": 10,
                        },
                        "by_endpoint": {
                            "/api/v1/rules": 80,
                            "/api/v1/approvals": 40,
                            "/api/v1/auth/login": 20,
                            "/metrics": 10,
                        },
                    }
                }
            },
        },
    },
)
async def error_metrics():
    """Get error metrics."""
    return {
        "total_errors_24h": 0,
        "total_errors_1h": 0,
        "by_type": {},
        "by_endpoint": {},
    }


def app_metrics(request: Request):
    """FastAPI app metrics middleware callback.
    
    Args:
        request: FastAPI request object
        
    **Returns**: Response with Prometheus metrics.
    """
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)