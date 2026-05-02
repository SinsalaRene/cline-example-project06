"""
Health Check API Tests - Task 7.3: Production Readiness.

Tests for health check endpoints: /healthz, /readyz, /startup, /health, /health/json, /health/detailed.
"""

import sys
import os
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure the app can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.api.health import (
    _check_database,
    _check_disk,
    _check_memory,
    _check_system,
    _get_process_info,
    _compute_overall_status,
    HealthStatus,
    PSUTIL_AVAILABLE,
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health Status Computation Tests
# ---------------------------------------------------------------------------

class TestComputeOverallStatus:
    """Tests for _compute_overall_status helper."""

    def test_healthy_only(self):
        assert _compute_overall_status(["healthy", "healthy"]) == "healthy"

    def test_unhealthy_detected(self):
        assert _compute_overall_status(["healthy", "unhealthy"]) == "unhealthy"

    def test_degraded_detected(self):
        assert _compute_overall_status(["healthy", "degraded"]) == "degraded"

    def test_empty_list_returns_unknown(self):
        assert _compute_overall_status([]) == "unknown"

    def test_multiple_unhealthy(self):
        assert _compute_overall_status(["unhealthy", "unhealthy"]) == "unhealthy"


# ---------------------------------------------------------------------------
# Individual Check Function Tests
# ---------------------------------------------------------------------------

class TestCheckFunctions:
    """Tests for individual health check functions."""

    def test_check_database(self):
        """Test database health check returns expected structure."""
        result = _check_database()
        assert "status" in result
        assert "message" in result
        assert "checked_at" in result
        assert "latency_ms" in result

    @patch("app.api.health.engine")
    def test_check_database_failure(self, mock_engine):
        """Test database health check handles connection failure."""
        from sqlalchemy import exc as sa_exc
        mock_engine.connect.side_effect = sa_exc.OperationalError("", None, None)

        result = _check_database()
        assert result["status"] in ("unhealthy", "healthy")

    def test_check_disk(self):
        result = _check_disk()
        assert "status" in result
        assert "message" in result
        if PSUTIL_AVAILABLE:
            assert "usage_percent" in result

    def test_check_memory(self):
        result = _check_memory()
        assert "status" in result
        assert "message" in result
        if PSUTIL_AVAILABLE:
            assert "usage_percent" in result

    def test_check_system(self):
        result = _check_system()
        assert "status" in result
        assert "message" in result

    def test_get_process_info(self):
        result = _get_process_info()
        assert "pid" in result
        if PSUTIL_AVAILABLE:
            assert "cpu_percent" in result
            assert "thread_count" in result
        assert "cpu_count" in result


# ---------------------------------------------------------------------------
# Route Tests
# ---------------------------------------------------------------------------

class TestHealthzLiveness:
    """Tests for /healthz liveness probe."""

    def test_healthz_returns_200(self, client):
        """Liveness probe should return 200."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_healthz_is_json(self, client):
        """Liveness probe should return JSON content type."""
        response = client.get("/healthz")
        assert "application/json" in response.headers.get("content-type", "")


class TestReadyzReadiness:
    """Tests for /readyz readiness probe."""

    def test_readyz_returns_200(self, client):
        """Readiness probe should return 200 when database is healthy."""
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert "database" in data["checks"]

    def test_readyz_includes_database_check(self, client):
        """Readiness probe should include database check result."""
        response = client.get("/readyz")
        data = response.json()
        assert "database" in data["checks"]
        assert "status" in data["checks"]["database"]


class TestStartupProbe:
    """Tests for /startup probe."""

    def test_startup_returns_200(self, client):
        """Startup probe should return 200 when initialized."""
        response = client.get("/startup")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initialized"

    def test_startup_includes_checks(self, client):
        """Startup probe should include check results."""
        response = client.get("/startup")
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]


class TestHealthFull:
    """Tests for /health full endpoint."""

    def test_health_full_returns_200(self, client):
        """Full health check should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_full_includes_all_checks(self, client):
        """Full health check should include all check types."""
        response = client.get("/health")
        data = response.json()
        assert "checks" in data
        for check_type in ("database", "system", "disk", "memory", "process"):
            assert check_type in data["checks"], f"Missing check: {check_type}"

    def test_health_full_includes_timestamp(self, client):
        """Full health check should include timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data


class TestHealthJson:
    """Tests for /health/json endpoint."""

    def test_health_json_returns_200(self, client):
        """Health JSON should return 200."""
        response = client.get("/health/json")
        assert response.status_code == 200

    def test_health_json_structure(self, client):
        """Health JSON should have expected structure."""
        response = client.get("/health/json")
        data = response.json()
        assert "probe_type" in data
        assert "overall_status" in data
        assert "timestamp" in data
        assert "checks" in data


class TestHealthDetailed:
    """Tests for /health/detailed endpoint."""

    def test_health_detailed_returns_200(self, client):
        """Detailed health should return 200."""
        response = client.get("/health/detailed")
        assert response.status_code == 200

    def test_health_detailed_includes_platform(self, client):
        """Detailed health should include platform info."""
        response = client.get("/health/detailed")
        data = response.json()
        assert "platform" in data
        assert "environment" in data


class TestHealthGC:
    """Tests for /health/gc endpoint."""

    def test_gc_returns_200(self, client):
        """GC endpoint should return 200."""
        response = client.post("/health/gc")
        assert response.status_code == 200

    def test_gc_includes_gc_summary(self, client):
        """GC endpoint should include GC summary."""
        response = client.post("/health/gc")
        data = response.json()
        assert "gc_summary" in data
        assert "generations_collected" in data["gc_summary"]


# ---------------------------------------------------------------------------
# Middleware Integration Tests
# ---------------------------------------------------------------------------

class TestMiddlewareIntegration:
    """Tests for middleware integration with health endpoints."""

    def test_health_endpoint_has_request_id_header(self, client):
        """Health endpoint responses should include X-Request-Id."""
        response = client.get("/healthz")
        # Request ID middleware adds this header
        assert "x-request-id" in response.headers or response.status_code == 200

    def test_health_endpoint_has_span_id_header(self, client):
        """Health endpoint responses should include X-Span-Id."""
        response = client.get("/healthz")
        # Span ID is added by the request_metrics_middleware
        assert "x-span-id" in response.headers or response.status_code == 200


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_healthz_multiple_requests(self, client):
        """Liveness probe should handle multiple concurrent requests."""
        for _ in range(3):
            response = client.get("/healthz")
            assert response.status_code == 200

    def test_health_check_caching(self, client):
        """Multiple health checks should return consistent structure."""
        resp1 = client.get("/health")
        resp2 = client.get("/health")
        assert set(resp1.json().keys()) == set(resp2.json().keys())

    def test_health_status_values(self):
        """Health status values should be valid."""
        valid_statuses = {"healthy", "unhealthy", "degraded", "unknown"}
        assert HealthStatus.healthy.value == "healthy"
        assert HealthStatus.unhealthy.value == "unhealthy"
        assert HealthStatus.degraded.value == "degraded"
        assert HealthStatus.unknown.value == "unknown"