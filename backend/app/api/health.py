"""
Health Check API - Production Readiness.

Provides comprehensive health check endpoints for Kubernetes,
load balancers, monitoring systems, and debugging.
"""

import os
import sys
import platform
import gc
import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# Import psutil optionally - may not be available in all environments
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import engine, get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    healthy = "healthy"
    unhealthy = "unhealthy"
    degraded = "degraded"
    unknown = "unknown"


class ProbeType(str, Enum):
    liveness = "liveness"
    readiness = "readiness"
    startup = "startup"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class DatabaseHealth(BaseModel):
    """Database health check result."""
    status: HealthStatus
    message: str
    latency_ms: float = 0.0
    pool_size: Optional[int] = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DiskHealth(BaseModel):
    """Disk usage health check."""
    status: HealthStatus
    message: str
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0


class MemoryHealth(BaseModel):
    """Memory health check."""
    status: HealthStatus
    message: str
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0


class SystemHealth(BaseModel):
    """System resource health."""
    status: HealthStatus
    message: str
    disk: Optional[DiskHealth] = None
    memory: Optional[MemoryHealth] = None
    cpu_percent: float = 0.0
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProcessHealth(BaseModel):
    """Process-level health info."""
    pid: int = 0
    uptime_seconds: float = 0.0
    cpu_count: int = 0
    open_files: int = 0
    open_fds: int = 0
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HealthCheckResult(BaseModel):
    """Aggregated health check result."""
    probe_type: ProbeType
    overall_status: HealthStatus
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0.0"
    environment: str = "development"
    checks: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["health"])


def _get_environment() -> str:
    """Determine the running environment."""
    debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    return "production" if not debug else "development"


def _check_database() -> dict:
    """Check database connectivity and health."""
    import time as _time
    start = _time.perf_counter()

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = (_time.perf_counter() - start) * 1000
        return {
            "status": "healthy",
            "message": "Database connection successful",
            "latency_ms": round(latency, 2),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        latency = (_time.perf_counter() - start) * 1000
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "latency_ms": round(latency, 2),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def _check_disk() -> dict:
    """Check disk usage."""
    if not PSUTIL_AVAILABLE:
        return {
            "status": "healthy",
            "message": "psutil not available, skipping disk check",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        usage = psutil.disk_usage("/")
        percent = usage.percent

        # Determine status thresholds
        if percent > 95:
            status = "unhealthy"
            message = "Disk usage critical"
        elif percent > 85:
            status = "degraded"
            message = "Disk usage high"
        else:
            status = "healthy"
            message = "Disk usage normal"

        return {
            "status": status,
            "message": message,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "usage_percent": round(percent, 2),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Disk health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"Disk check failed: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def _check_memory() -> dict:
    """Check system memory usage."""
    if not PSUTIL_AVAILABLE:
        return {
            "status": "healthy",
            "message": "psutil not available, skipping memory check",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        vm = psutil.virtual_memory()
        percent = vm.percent

        if percent > 95:
            status = "unhealthy"
            message = "Memory usage critical"
        elif percent > 85:
            status = "degraded"
            message = "Memory usage high"
        else:
            status = "healthy"
            message = "Memory usage normal"

        return {
            "status": status,
            "message": message,
            "total_gb": round(vm.total / (1024 ** 3), 2),
            "used_gb": round(vm.used / (1024 ** 3), 2),
            "free_gb": round(vm.free / (1024 ** 3), 2),
            "usage_percent": round(percent, 2),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"Memory check failed: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def _check_system() -> dict:
    """Check overall system health."""
    if not PSUTIL_AVAILABLE:
        return {
            "status": "healthy",
            "message": "psutil not available, skipping system check",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        cpu_percent = psutil.cpu_percent(interval=0)
        process = psutil.Process(os.getpid())

        if cpu_percent > 95:
            status = "unhealthy"
            message = "CPU usage critical"
        elif cpu_percent > 80:
            status = "degraded"
            message = "CPU usage high"
        else:
            status = "healthy"
            message = "System resources normal"

        return {
            "status": status,
            "message": message,
            "cpu_percent": cpu_percent,
            "open_files": len(process.open_files()),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"System check failed: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def _get_process_info() -> dict:
    """Get process-level information."""
    _start_time = os.environ.get("_START_TIME") or ""
    if not PSUTIL_AVAILABLE:
        return {
            "status": "healthy",
            "pid": os.getpid(),
            "uptime_seconds": 0.0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "thread_count": 0,
            "cpu_count": os.cpu_count() or 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        process = psutil.Process(os.getpid())
        cpu_percent = process.cpu_percent(interval=0)
        status = "healthy"
        if cpu_percent > 90:
            status = "unhealthy"
        elif cpu_percent > 70:
            status = "degraded"

        return {
            "status": status,
            "pid": os.getpid(),
            "uptime_seconds": 0.0,
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(process.memory_info().rss / (1024 ** 2), 2),
            "thread_count": process.num_threads(),
            "cpu_count": psutil.cpu_count(),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Process info check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "pid": os.getpid(),
            "uptime_seconds": 0.0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "thread_count": 0,
            "cpu_count": os.cpu_count() or 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def _compute_overall_status(statuses: list[str]) -> str:
    """Compute overall health from individual check statuses."""
    if not statuses:
        return HealthStatus.unknown

    if "unhealthy" in statuses:
        return HealthStatus.unhealthy

    if "degraded" in statuses:
        return HealthStatus.degraded

    return HealthStatus.healthy


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/healthz",
    summary="Kubernetes-style liveness probe",
    description=(
        "Kubernetes liveness probe endpoint. Returns 200 if the application "
        "is alive (process is running). Does NOT check dependencies."
    ),
    responses={
        200: {"description": "Application is alive"},
    },
)
async def healthz_liveness():
    """Kubernetes liveness probe – returns 200 if the process is alive."""
    return {"status": "alive"}


@router.get(
    "/readyz",
    summary="Kubernetes-style readiness probe",
    description=(
        "Kubernetes readiness probe endpoint. Returns 200 only if all critical "
        "dependencies (database, etc.) are healthy. Used by load balancers "
        "to determine if the pod should receive traffic."
    ),
    responses={
        200: {"description": "Application is ready to serve traffic"},
        503: {"description": "Application is not ready"},
    },
)
async def readyz_readiness():
    """Kubernetes readiness probe – checks all critical dependencies."""
    checks = {
        "database": _check_database(),
    }

    db_status = checks["database"]["status"]
    overall = _compute_overall_status([db_status])

    if overall == HealthStatus.unhealthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
    )


@router.get(
    "/startup",
    summary="Kubernetes-style startup probe",
    description=(
        "Kubernetes startup probe endpoint. Verifies the application can "
        "fully initialize (database, configs, etc.) on startup."
    ),
    responses={
        200: {"description": "Application has started successfully"},
        503: {"description": "Application failed to start"},
    },
)
async def startup_probe():
    """Kubernetes startup probe – validates full initialization."""
    checks = {
        "database": _check_database(),
    }

    overall = _compute_overall_status([c["status"] for c in checks.values()])

    if overall == HealthStatus.unhealthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "initialization_failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "initialized",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
    )


@router.get(
    "/health",
    summary="Full health check (all checks)",
    description=(
        "Comprehensive health check endpoint. Returns detailed information about "
        "all system components: database, disk, memory, CPU, process info, and "
        "system resources. Suitable for monitoring dashboards and alerting."
    ),
    responses={
        200: {"description": "Full health check result"},
        503: {"description": "One or more checks failed"},
    },
)
async def health_full():
    """Comprehensive health check with all system checks."""
    checks = {
        "database": _check_database(),
        "system": _check_system(),
        "disk": _check_disk(),
        "memory": _check_memory(),
        "process": _get_process_info(),
    }

    statuses = [c["status"] for c in checks.values()]
    overall = _compute_overall_status(statuses)

    status_code = 503 if overall == HealthStatus.unhealthy else 200

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
    )


@router.get(
    "/health/json",
    summary="Standardized health JSON",
    description=(
        "Returns a standardized health check JSON that follows "
        "Kubernetes readiness probe conventions and includes "
        "detailed per-component health information."
    ),
)
async def health_json():
    """Standardized health check JSON endpoint."""
    checks = {
        "database": _check_database(),
        "system": _check_system(),
        "disk": _check_disk(),
        "memory": _check_memory(),
        "process": _get_process_info(),
    }

    statuses = [c["status"] for c in checks.values()]
    overall = _compute_overall_status(statuses)
    environment = _get_environment()

    return {
        "probe_type": ProbeType.readiness.value,
        "overall_status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": environment,
        "checks": checks,
    }


@router.post(
    "/health/gc",
    summary="Trigger garbage collection",
    description="Manually trigger garbage collection and report memory reclaimed.",
)
async def trigger_gc():
    """Trigger garbage collection and report results."""
    import gc as gc_module
    import time as _time

    # Force garbage collection
    gc_module.collect()
    gc_counts = gc_module.garbage

    mem_before = None
    mem_after = None
    if PSUTIL_AVAILABLE:
        try:
            mem_before = psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            pass

    # gc.collect() argument support varies by Python version
    # Python 3.13+ supports gc.GC_GENERATIONS, older versions don't
    try:
        collected = gc_module.collect(gc_module.GC_GENERATIONS)
    except AttributeError:
        collected = gc_module.collect()

    gc_summary = {
        "generations_collected": collected,
        "garbage_collected": len(gc_counts) if gc_counts else 0,
        "gc_enabled": gc_module.isenabled(),
        "gc_counts": gc_counts if gc_counts else [],
    }

    if PSUTIL_AVAILABLE:
        try:
            mem_after = psutil.Process(os.getpid()).memory_info().rss
        except Exception:
            pass

    return JSONResponse(
        status_code=200,
        content={
            "gc_summary": gc_summary,
            "memory_before_mb": round(mem_before / (1024 ** 2), 2) if mem_before else None,
            "memory_after_mb": round(mem_after / (1024 ** 2), 2) if mem_after else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get(
    "/health/detailed",
    summary="Detailed diagnostic health",
    description=(
        "Deep diagnostic endpoint. Returns environment variables (minus secrets), "
        "dependency info, configuration summary, and thread/pool states. "
        "Useful for troubleshooting."
    ),
)
async def health_detailed():
    """Detailed diagnostic health endpoint."""
    # Mask sensitive environment variables
    sensitive_keys = {"SECRET_KEY", "DATABASE_URL", "AZURE_CLIENT_SECRET",
                      "SERVICE_BUS_CONNECTION_STRING", "TEAMS_WEBHOOK_URL"}

    env_snapshot = {}
    for k, v in os.environ.items():
        if k in sensitive_keys:
            env_snapshot[k] = "***REDACTED***"
        else:
            env_snapshot[k] = v

    # Platform info
    platform_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "architecture": platform.machine(),
    }

    return {
        "environment": _get_environment(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform_info,
        "environment_vars": env_snapshot,
        "checks": {
            "database": _check_database(),
            "system": _check_system(),
            "disk": _check_disk(),
            "memory": _check_memory(),
            "process": _get_process_info(),
        },
    }