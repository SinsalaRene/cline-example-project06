"""
Metrics Endpoint - Production Readiness.

Prometheus-compatible metrics endpoint for application and system monitoring.
Exports metrics in Prometheus exposition format.
"""

import os
import sys
import time
import gc
import threading
import logging
import platform
from datetime import datetime, timezone

# Import psutil optionally - it may not be available in all environments
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from prometheus_client import (
    CollectorRegistry,
    Gauge,
    Counter,
    Histogram,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prometheus Registry & Metrics
# ---------------------------------------------------------------------------

# Use a dedicated registry to avoid conflicts with default registry
METRIC_REGISTRY = CollectorRegistry()

# ----- Application Lifecycles -----
_request_counter = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"],
    registry=METRIC_REGISTRY,
)

_request_duration_histogram = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=METRIC_REGISTRY,
)

_request_duration_summary = Summary(
    "http_request_duration_summary_seconds",
    "HTTP request duration summary (raw seconds)",
    ["method", "endpoint"],
    registry=METRIC_REGISTRY,
)

# ----- Database Metrics -----
_active_db_connections = Gauge(
    "db_pool_active_connections",
    "Number of active database connections",
    registry=METRIC_REGISTRY,
)

_db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    registry=METRIC_REGISTRY,
)

_db_query_count = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["query_type", "status"],
    registry=METRIC_REGISTRY,
)

# ----- Process / Runtime Metrics -----
_process_start_time = Gauge(
    "process_start_time_seconds",
    "Process start time in Unix epoch seconds",
    registry=METRIC_REGISTRY,
)

_process_memory_bytes = Gauge(
    "process_memory_bytes",
    "Process memory usage in bytes",
    registry=METRIC_REGISTRY,
)

_process_cpu_percent = Gauge(
    "process_cpu_percent",
    "Process CPU usage percentage",
    registry=METRIC_REGISTRY,
)

_process_open_fds = Gauge(
    "process_open_fds",
    "Number of open file descriptors",
    registry=METRIC_REGISTRY,
)

_process_threads = Gauge(
    "process_threads",
    "Number of threads in the process",
    registry=METRIC_REGISTRY,
)

_process_pid = Gauge(
    "process_pid",
    "Current process PID",
    registry=METRIC_REGISTRY,
)

# ----- System Metrics -----
_system_cpu_count = Gauge(
    "system_cpu_cores",
    "Total number of CPU cores",
    registry=METRIC_REGISTRY,
)

_system_memory_total_bytes = Gauge(
    "system_memory_total_bytes",
    "Total system memory in bytes",
    registry=METRIC_REGISTRY,
)

_system_memory_available_bytes = Gauge(
    "system_memory_available_bytes",
    "Available system memory in bytes",
    registry=METRIC_REGISTRY,
)

_system_disk_total_bytes = Gauge(
    "system_disk_total_bytes",
    "Total disk space in bytes",
    registry=METRIC_REGISTRY,
)

_system_disk_free_bytes = Gauge(
    "system_disk_free_bytes",
    "Free disk space in bytes",
    registry=METRIC_REGISTRY,
)

# ----- Custom Business Metrics -----
_azure_sync_success_count = Counter(
    "azure_sync_operations_total",
    "Total Azure sync operations completed",
    ["sync_type", "status"],
    registry=METRIC_REGISTRY,
)

_approval_queue_depth = Gauge(
    "approval_queue_depth",
    "Number of pending approval requests",
    registry=METRIC_REGISTRY,
)

# ----- Error Tracking -----
_errors_total = Counter(
    "errors_total",
    "Total number of errors by type and source",
    ["error_type", "source"],
    registry=METRIC_REGISTRY,
)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["metrics"])

# Track request start times for duration calculation
_request_start_times: dict = {}


def record_request(method: str, endpoint: str, status_code: int):
    """Record HTTP request metrics. Call this from middleware or after each request."""
    # Normalize endpoint for metrics
    _normalize_endpoint = _sanitize_endpoint(endpoint)

    _request_counter.labels(
        method=method,
        endpoint=_normalize_endpoint,
        status=str(status_code),
    ).inc()

    _request_duration_histogram.labels(
        method=method,
        endpoint=_normalize_endpoint,
    ).observe(0)  # Duration set in middleware

    _request_duration_summary.labels(
        method=method,
        endpoint=_normalize_endpoint,
    ).observe(0)  # Set by middleware


def _sanitize_endpoint(endpoint: str) -> str:
    """Sanitize endpoint paths for Prometheus label values."""
    # Preserve trailing slash if present
    has_trailing_slash = endpoint.endswith("/")
    # Remove leading/trailing slashes for processing
    endpoint = endpoint.strip("/")
    # Replace path parameters with generic labels
    parts = endpoint.split("/")
    sanitized = []
    for part in parts:
        if part and part.replace("-", "").replace("_", "").isdigit():
            sanitized.append("{param}")
        else:
            sanitized.append(part)
    result = "/".join(sanitized) if sanitized else ""
    if has_trailing_slash and result:
        result += "/"
    return result


def record_db_query(query_type: str, duration: float, success: bool = True):
    """Record database query metrics."""
    status_label = "success" if success else "error"
    _db_query_duration.labels(query_type=query_type).observe(duration)
    _db_query_count.labels(query_type=query_type, status=status_label).inc()


def record_azure_sync(sync_type: str, success: bool = True):
    """Record Azure sync operation metrics."""
    status_label = "success" if success else "error"
    _azure_sync_success_count.labels(sync_type=sync_type, status=status_label).inc()


def record_error(error_type: str, source: str):
    """Record error metrics."""
    _errors_total.labels(error_type=error_type, source=source).inc()


def refresh_process_metrics():
    """Refresh process-level metrics from the current OS process."""
    if not PSUTIL_AVAILABLE:
        logger.debug("psutil not available, skipping process metrics refresh")
        return
    try:
        process = psutil.Process(os.getpid())

        _process_start_time.set(process.create_time())
        _process_memory_bytes.set(process.memory_info().rss)
        _process_cpu_percent.set(process.cpu_percent())
        _process_threads.set(process.num_threads())
        _process_pid.set(os.getpid())

        # Open file descriptors (Linux/macOS)
        try:
            _process_open_fds.set(len(process.open_files()) + process.num_fds())
        except (AttributeError, OSError):
            _process_open_fds.set(len(process.open_files()))
    except Exception as e:
        logger.error(f"Failed to refresh process metrics: {e}")


def refresh_system_metrics():
    """Refresh system-level metrics."""
    if not PSUTIL_AVAILABLE:
        logger.debug("psutil not available, skipping system metrics refresh")
        return
    try:
        _system_cpu_count.set(psutil.cpu_count())

        vm = psutil.virtual_memory()
        _system_memory_total_bytes.set(vm.total)
        _system_memory_available_bytes.set(vm.available)

        disk = psutil.disk_usage("/")
        _system_disk_total_bytes.set(disk.total)
        _system_disk_free_bytes.set(disk.free)
    except Exception as e:
        logger.error(f"Failed to refresh system metrics: {e}")


def refresh_db_metrics():
    """Refresh database pool metrics."""
    try:
        from app.database import get_engine
        engine = get_engine()
        pool = engine.pool
        # SQLAlchemy pools have different interfaces depending on the DB dialect
        try:
            checkedin = getattr(pool, '_checkedin', 0)
            active = pool.size() - checkedin if checkedin >= 0 else 0
            _active_db_connections.set(active)
        except Exception:
            _active_db_connections.set(0)
    except Exception as e:
        logger.error(f"Failed to refresh DB metrics: {e}")


def update_all_metrics():
    """Update all non-counter metrics (called periodically or on-demand)."""
    refresh_process_metrics()
    refresh_system_metrics()
    refresh_db_metrics()


# Initialize start time
_process_start_time.set(time.time())


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/metrics",
    summary="Prometheus-compatible metrics endpoint",
    description=(
        "Exports application and system metrics in Prometheus exposition format. "
        "Suitable for scraping by Prometheus, Grafana, or other monitoring systems. "
        "Returns metrics in plaintext format compatible with Prometheus text "
        "exposition format v1.0.0."
    ),
)
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    # Update all gauge/observer metrics before exporting
    update_all_metrics()

    return Response(
        content=generate_latest(METRIC_REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get(
    "/metrics/json",
    summary="Metrics as JSON (human-readable)",
    description=(
        "Returns metrics as a human-readable JSON document. "
        "Useful for debugging and manual inspection. "
        "Not suitable for Prometheus scraping."
    ),
)
async def metrics_json():
    """Metrics exported as JSON for human-readable inspection."""
    update_all_metrics()

    # Build JSON-friendly metric representation
    raw_output = generate_latest(METRIC_REGISTRY).decode("utf-8")

    metrics_dict: dict = {}
    current_metric: str | None = None
    current_value: float | None = None
    current_labels: dict = {}

    for line in raw_output.split("\n"):
        line = line.strip()

        # Skip empty lines and non-help/type comments
        if not line:
            continue
        if line.startswith("#") and not line.startswith("# HELP") and not line.startswith("# TYPE"):
            continue

        try:
            # Parse TYPE line
            if line.startswith("# TYPE"):
                parts = line.split()
                if len(parts) >= 3:
                    metric_name = parts[2]
                    metrics_dict[metric_name] = {
                        "type": parts[3] if len(parts) > 3 else "unknown",
                        "values": [],
                    }
                continue

            # Parse HELP line
            if line.startswith("# HELP"):
                parts = line.split(" ", 3)
                if len(parts) >= 4:
                    metric_name = parts[2]
                    if metric_name in metrics_dict:
                        metrics_dict[metric_name]["help"] = parts[3] if len(parts) > 3 else ""
                continue

            # Skip any other comment lines
            if line.startswith("#"):
                continue

            # This is an actual metric value line
            if "{" in line:
                parts = line.split("{", 1)
                metric_name = parts[0].strip()
                labels_part = parts[1].rsplit("}", 1)
                if len(labels_part) < 2:
                    continue
                labels_str = labels_part[0]
                value_str = labels_part[1].strip()

                # Parse labels
                labels: dict = {}
                if labels_str:
                    for label in labels_str.split(","):
                        label = label.strip()
                        if "=" in label:
                            k, v = label.split("=", 1)
                            labels[k.strip()] = v.strip('"')

                try:
                    value = float(value_str)
                except (ValueError, IndexError):
                    continue
                current_metric = metric_name
                current_value = value
                current_labels = labels

                if metric_name not in metrics_dict:
                    metrics_dict[metric_name] = {"type": "unknown", "values": []}
                metrics_dict[metric_name]["values"].append({
                    "value": value,
                    "labels": labels,
                })
            else:
                # Simple metric without labels
                parts = line.split()
                if len(parts) < 2:
                    continue
                metric_name = parts[0]
                try:
                    value = float(parts[1])
                except ValueError:
                    continue
                metrics_dict[metric_name] = {
                    "type": "unknown",
                    "values": [{"value": value, "labels": {}}],
                }
        except KeyError:
            # Skip malformed metric lines
            continue

    metrics_dict["_metadata"] = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
    }

    return metrics_dict


@router.post(
    "/metrics/gc",
    summary="Force GC and report metrics",
    description=(
        "Force garbage collection, then update all metrics and return "
        "GC statistics alongside the current metrics state."
    ),
)
async def metrics_gc():
    """Force GC and report GC stats alongside metrics."""
    gc_before = gc.collect()
    update_all_metrics()

    raw_output = generate_latest(METRIC_REGISTRY).decode("utf-8")

    # Count lines = number of metrics
    metric_lines = [l for l in raw_output.split("\n") if l and not l.startswith("#")]
    total_metrics = len(metric_lines)

    gc_stats = {
        "gc_count": gc_before,
        "total_metrics": total_metrics,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        **gc_stats,
        "metrics_preview": dict(list(_parse_metrics_preview(raw_output).items())[:50]),
    }


def _parse_metrics_preview(raw: str) -> dict:
    """Quick parse of a subset of metrics for preview."""
    preview = {}
    for line in raw.split("\n"):
        if not line or line.startswith("#"):
            continue
        try:
            parts = line.split()
            if len(parts) < 2:
                continue
            metric_name = parts[0].split("{")[0]
            value = float(parts[-1])
            if metric_name and value is not None and metric_name not in preview:
                preview[metric_name] = value
        except (ValueError, IndexError):
            continue
    return preview


# Initialize process PID metric
_process_pid.set(os.getpid())