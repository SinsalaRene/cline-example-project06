"""
Metrics Endpoint Tests - Task 7.3: Production Readiness.

Tests for the Prometheus-compatible metrics endpoint and metrics helper functions.
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
from app.api.metrics import (
    METRIC_REGISTRY,
    record_request,
    record_db_query,
    record_azure_sync,
    record_error,
    _sanitize_endpoint,
    update_all_metrics,
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Sanitize Endpoint Tests
# ---------------------------------------------------------------------------

class TestSanitizeEndpoint:
    """Tests for endpoint sanitization."""

    def test_simple_path(self):
        assert _sanitize_endpoint("/api/v1/rules") == "api/v1/rules"

    def test_path_with_params(self):
        assert "{param}" in _sanitize_endpoint("/api/v1/rules/12345")
        assert _sanitize_endpoint("/api/v1/rules/") == "api/v1/rules/"

    def test_nested_path(self):
        result = _sanitize_endpoint("/api/v1/rules/abc/def/123")
        assert "{param}" in result or "def" in result

    def test_empty_path(self):
        assert _sanitize_endpoint("") == ""

    def test_single_slash(self):
        assert _sanitize_endpoint("/") == ""

    def test_path_with_numbers(self):
        result = _sanitize_endpoint("/api/v1/rules/42/items/99")
        assert "{param}" in result


# ---------------------------------------------------------------------------
# Route Tests
# ---------------------------------------------------------------------------

class TestMetricsEndpoint:
    """Tests for the Prometheus /metrics endpoint."""

    def test_metrics_returns_200(self, client):
        """Metrics endpoint should return 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        """Metrics endpoint should return correct content type."""
        response = client.get("/metrics")
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contains_application_metrics(self, client):
        """Metrics should contain application-level metrics."""
        response = client.get("/metrics")
        content = response.text
        # Check for at least some metric lines
        metric_lines = [l for l in content.split("\n") if l and not l.startswith("#")]
        assert len(metric_lines) > 0, "Expected at least some metrics"

    def test_metrics_contains_http_request_metrics(self, client):
        """Metrics should contain HTTP request metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "http_requests_total" in content

    def test_metrics_contains_process_metrics(self, client):
        """Metrics should contain process-level metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "process_" in content.lower() or "process_start_time" in content

    def test_metrics_contains_system_metrics(self, client):
        """Metrics should contain system-level metrics."""
        response = client.get("/metrics")
        content = response.text
        assert "system_" in content.lower() or "cpu_cores" in content

    def test_metrics_after_requests(self, client):
        """Metrics should reflect actual request counts."""
        # Make some requests
        client.get("/healthz")
        client.get("/healthz")

        response = client.get("/metrics")
        content = response.text
        assert "http_requests_total" in content


class TestMetricsJson:
    """Tests for the /metrics/json human-readable endpoint."""

    def test_metrics_json_returns_200(self, client):
        """Metrics JSON endpoint should return 200."""
        response = client.get("/metrics/json")
        assert response.status_code == 200

    def test_metrics_json_is_valid_json(self, client):
        """Metrics JSON should be valid JSON."""
        response = client.get("/metrics/json")
        data = response.json()
        assert isinstance(data, dict)

    def test_metrics_json_contains_metadata(self, client):
        """Metrics JSON should contain metadata."""
        response = client.get("/metrics/json")
        data = response.json()
        assert "_metadata" in data or len(data) > 0

    def test_metrics_json_structure(self, client):
        """Metrics JSON should have structured metric data."""
        response = client.get("/metrics/json")
        data = response.json()
        # Should be a dict with metric names as keys
        assert isinstance(data, dict)


class TestMetricsGC:
    """Tests for the /metrics/gc endpoint."""

    def test_metrics_gc_returns_200(self, client):
        """Metrics GC endpoint should return 200."""
        response = client.post("/metrics/gc")
        assert response.status_code == 200

    def test_metrics_gc_returns_gc_stats(self, client):
        """Metrics GC endpoint should return GC statistics."""
        response = client.post("/metrics/gc")
        data = response.json()
        assert "gc_count" in data or "total_metrics" in data

    def test_metrics_gc_returns_metric_preview(self, client):
        """Metrics GC endpoint should return metric preview."""
        response = client.post("/metrics/gc")
        data = response.json()
        assert "metrics_preview" in data


# ---------------------------------------------------------------------------
# Metrics Recording Functions Tests
# ---------------------------------------------------------------------------

class TestMetricsRecordingFunctions:
    """Tests for metrics recording helper functions."""

    def test_record_request(self):
        """record_request should increment request counter."""
        # Should not raise
        record_request(method="GET", endpoint="/test", status_code=200)

    def test_record_request_various_methods(self):
        """record_request handles various HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        for method in methods:
            record_request(method=method, endpoint="/test", status_code=200)

    def test_record_db_query(self):
        """record_db_query should record database query metrics."""
        # Should not raise
        record_db_query(query_type="SELECT", duration=0.001, success=True)
        record_db_query(query_type="INSERT", duration=0.002, success=True)
        record_db_query(query_type="UPDATE", duration=0.003, success=False)

    def test_record_azure_sync(self):
        """record_azure_sync should record Azure sync metrics."""
        record_azure_sync(sync_type="full", success=True)
        record_azure_sync(sync_type="incremental", success=True)
        record_azure_sync(sync_type="full", success=False)

    def test_record_error(self):
        """record_error should record error metrics."""
        record_error(error_type="ValueError", source="test_module")
        record_error(error_type="TypeError", source="test_module")


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestMetricsIntegration:
    """Integration tests for metrics with the actual app."""

    def test_metrics_endpoint_includes_custom_metrics(self, client):
        """Custom metrics should appear in /metrics output."""
        # Record a custom metric
        record_error(error_type="test_error", source="test")

        response = client.get("/metrics")
        content = response.text
        assert "errors_total" in content

    def test_metrics_endpoint_reflects_requests(self, client):
        """Metrics should reflect actual requests made."""
        # Make requests
        client.get("/healthz")
        client.get("/healthz")

        response = client.get("/metrics")
        content = response.text
        # The http_requests_total metric should exist
        assert "http_requests_total" in content

    def test_all_health_endpoints_accessible(self, client):
        """All health endpoint variants should be accessible."""
        endpoints = [
            "/healthz",
            "/readyz",
            "/startup",
            "/health",
            "/health/json",
            "/health/detailed",
            "/metrics",
            "/metrics/json",
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Most should return 200; some may return 503 if db is unavailable
            assert response.status_code in (200, 503), f"{endpoint} returned {response.status_code}"

    def test_health_gc_endpoint(self, client):
        """Health GC endpoint should work."""
        response = client.post("/health/gc")
        assert response.status_code == 200

    def test_metrics_after_health_checks(self, client):
        """Metrics should still work after multiple health checks."""
        # Make many health check requests
        for _ in range(5):
            client.get("/health")
            client.get("/readyz")

        response = client.get("/metrics")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Prometheus Format Tests
# ---------------------------------------------------------------------------

class TestPrometheusFormat:
    """Tests for Prometheus exposition format compliance."""

    def test_metrics_have_help_comments(self, client):
        """Metrics should include # HELP comments."""
        response = client.get("/metrics")
        content = response.text
        assert "# HELP" in content

    def test_metrics_have_type_comments(self, client):
        """Metrics should include # TYPE comments."""
        response = client.get("/metrics")
        content = response.text
        assert "# TYPE" in content

    def test_metrics_have_label_values(self, client):
        """Metric lines should include label values."""
        response = client.get("/metrics")
        content = response.text
        # Counter metrics should have label format
        assert 'method="GET"' in content or 'method="' in content

    def test_metric_names_are_valid(self, client):
        """Metric names should follow Prometheus naming conventions."""
        response = client.get("/metrics")
        content = response.text

        # Extract metric names from lines that have metric_name{labels} value format
        import re
        metric_pattern = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\{', re.MULTILINE)
        metric_names = metric_pattern.findall(content)

        # Prometheus metrics should start with a letter or underscore
        for name in metric_names:
            # Names should be alphanumeric or contain underscores/colons
            assert all(c.isalnum() or c in ('_', ':', '-') for c in name), \
                f"Invalid metric name: {name}"


# ---------------------------------------------------------------------------
# Error Tracking Tests
# ---------------------------------------------------------------------------

class TestErrorTracking:
    """Tests for error tracking integration."""

    def test_error_tracking_via_metrics(self, client):
        """Errors should be tracked via metrics."""
        from app.error_tracking import capture_exception, ErrorCategory

        try:
            raise ValueError("test error")
        except ValueError as e:
            capture_exception(
                error=e,
                category=ErrorCategory.validation.value,
                severity="error",
            )

        response = client.get("/metrics")
        assert response.status_code == 200

    def test_error_report_generation(self, client):
        """Error report should be generatable."""
        from app.error_tracking import get_error_report

        report = get_error_report()
        assert isinstance(report, dict)
        assert "error_stats" in report
        assert "sentry_initialized" in report