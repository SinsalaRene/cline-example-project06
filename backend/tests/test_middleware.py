"""
Tests for middleware: Request ID, timing, exception handler, and validation.

Tests cover:
- Request ID middleware generates/propagates request IDs
- Timing middleware logs request duration
- Exception handler middleware catches and formats exceptions
- Validation middleware validates content-type, body size, JSON
"""

import os
import time
import pytest
import json
from unittest.mock import patch, MagicMock
from io import BytesIO

# Set minimal environment variables before importing app modules
os.environ.setdefault("AZURE_TENANT_ID", "test-tenant-id")
os.environ.setdefault("AZURE_CLIENT_ID", "test-client-id")
os.environ.setdefault("AZURE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("AZURE_SUBSCRIPTION_ID", "test-subscription-id")
os.environ.setdefault("AZURE_RESOURCE_GROUP", "test-resource-group")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-must-be-at-least-256-bits")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DEBUG", "true")


class TestRequestIDMiddleware:
    """Test request ID middleware functionality."""

    def test_request_id_generated_when_missing(self):
        """Test that a request ID is generated when not provided."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from app.middleware.request_id import RequestIDMiddleware

        def homepage(request):
            return PlainTextResponse("OK")

        routes = [Route("/", homepage)]
        app = Starlette(routes=routes)
        app.add_middleware(RequestIDMiddleware)

        client = TestClient(app)
        response = client.get("/")

        # Response should include request ID header
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"]

    def test_request_id_preserved_from_request(self):
        """Test that the middleware preserves the request's X-Request-ID."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from app.middleware.request_id import RequestIDMiddleware

        def homepage(request):
            return PlainTextResponse("OK")

        routes = [Route("/", homepage)]
        app = Starlette(routes=routes)
        app.add_middleware(RequestIDMiddleware)

        client = TestClient(app)
        custom_id = "test-request-id-12345"
        response = client.get("/", headers={"X-Request-ID": custom_id})

        # Response should include the same request ID
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == custom_id

    def test_request_state_contains_request_id(self):
        """Test that request state contains the request ID."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from app.middleware.request_id import RequestIDMiddleware

        def state_check(request):
            request_id = getattr(request.state, 'request_id', None)
            return JSONResponse({"request_id": request_id})

        routes = [Route("/", state_check)]
        app = Starlette(routes=routes)
        app.add_middleware(RequestIDMiddleware)

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert response.json()["request_id"] is not None
        assert response.json()["request_id"] != "no-request-id"

    def test_request_id_is_valid_uuid(self):
        """Test that generated request IDs are valid UUIDs."""
        import uuid
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from app.middleware.request_id import RequestIDMiddleware

        def return_id(request):
            request_id = getattr(request.state, 'request_id', None)
            return JSONResponse({"request_id": request_id})

        routes = [Route("/", return_id)]
        app = Starlette(routes=routes)
        app.add_middleware(RequestIDMiddleware)

        client = TestClient(app)
        response = client.get("/")

        request_id = response.json()["request_id"]
        # Should be a valid UUID4
        parsed = uuid.UUID(request_id)
        assert str(parsed) == request_id


class TestTimingMiddleware:
    """Test timing middleware functionality."""

    def test_timing_header_present(self):
        """Test that timing middleware adds response-time header."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from app.middleware.timing import TimingMiddleware

        def homepage(request):
            return PlainTextResponse("OK")

        routes = [Route("/", homepage)]
        app = Starlette(routes=routes)
        app.add_middleware(TimingMiddleware)

        client = TestClient(app)
        response = client.get("/")

        assert "X-Response-Time" in response.headers
        # The header should contain a valid time value
        assert "ms" in response.headers["X-Response-Time"]

    def test_timing_duration_is_positive(self):
        """Test that the reported duration is positive."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from app.middleware.timing import TimingMiddleware

        def homepage(request):
            return PlainTextResponse("OK")

        routes = [Route("/", homepage)]
        app = Starlette(routes=routes)
        app.add_middleware(TimingMiddleware)

        client = TestClient(app)
        response = client.get("/")

        # Parse the duration from the header
        duration_str = response.headers["X-Response-Time"]
        # Extract numeric value before 'ms'
        duration_ms = float(duration_str.replace("ms", "").strip())
        assert duration_ms >= 0

    def test_timing_logs_request(self, caplog):
        """Test that timing middleware logs request details."""
        import logging
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from app.middleware.timing import TimingMiddleware

        def homepage(request):
            return PlainTextResponse("OK")

        routes = [Route("/", homepage)]
        app = Starlette(routes=routes)
        app.add_middleware(TimingMiddleware)

        with caplog.at_level(logging.INFO):
            client = TestClient(app)
            response = client.get("/")
            assert response.status_code == 200

        # Should have logged the request
        assert any("GET /" in record.message for record in caplog.records)


class TestExceptionHandlerMiddleware:
    """Test exception handler middleware functionality."""

    def test_catches_unhandled_exception(self):
        """Test that exception handler catches unhandled exceptions."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.exception_handler import ExceptionHandlerMiddleware

        def failing_endpoint(request):
            raise ValueError("Test error message")

        routes = [Route("/fail", failing_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ExceptionHandlerMiddleware)

        client = TestClient(app)
        try:
            response = client.get("/fail")
        except:
            response = client.get("/fail")
        assert response.status_code == 400  # ValueError -> 400
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "invalid_value"

    def test_error_response_structure(self):
        """Test that error responses have the expected structure."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.exception_handler import ExceptionHandlerMiddleware

        def failing_endpoint(request):
            raise TypeError("Type mismatch error")

        routes = [Route("/fail", failing_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ExceptionHandlerMiddleware)

        client = TestClient(app)
        try:
            response = client.get("/fail")
        except:
            response = client.get("/fail")
        error_data = response.json()["error"]
        assert "code" in error_data
        assert "message" in error_data
        assert "path" in error_data
        assert "request_id" in error_data

    def test_different_exception_codes(self):
        """Test that different exception types produce different error codes."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.exception_handler import ExceptionHandlerMiddleware

        # Test ValueError -> invalid_value
        def value_error_endpoint(request):
            raise ValueError("value error")

        routes = [Route("/ve", value_error_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ExceptionHandlerMiddleware)

        client = TestClient(app)
        try:
            response = client.get("/ve")
        except:
            response = client.get("/ve")
        assert response.json()["error"]["code"] == "invalid_value"

    def test_key_error_returns_404(self):
        """Test that KeyError returns 404."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.exception_handler import ExceptionHandlerMiddleware

        def key_error_endpoint(request):
            raise KeyError("missing key")

        routes = [Route("/ke", key_error_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ExceptionHandlerMiddleware)

        client = TestClient(app)
        try:
            response = client.get("/ke")
        except:
            response = client.get("/ke")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "missing_field"

    def test_error_includes_request_id(self):
        """Test that error responses include the request ID."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.exception_handler import ExceptionHandlerMiddleware
        from app.middleware.request_id import RequestIDMiddleware

        def failing_endpoint(request):
            raise ValueError("test")

        routes = [Route("/fail", failing_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(ExceptionHandlerMiddleware)

        client = TestClient(app)
        try:
            response = client.get("/fail")
        except:
            response = client.get("/fail")
        request_id = response.json()["error"]["request_id"]
        assert request_id is not None
        assert request_id != "unknown"

    def test_health_check_skip(self):
        """Test that health checks are skipped when configured."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.exception_handler import ExceptionHandlerMiddleware

        def failing_endpoint(request):
            raise ValueError("should not happen")

        routes = [Route("/health", failing_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ExceptionHandlerMiddleware, include_health=True)

        client = TestClient(app)
        try:
            response = client.get("/health")
        except:
            response = client.get("/health")
        # Should return error since health is included
        assert response.status_code == 400


class TestValidationMiddleware:
    """Test validation middleware functionality."""

    def test_content_type_validation(self):
        """Test that POST without content-type returns 415."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        from app.middleware.validation import ValidationMiddleware

        async def json_endpoint(request):
            body = await request.json()
            return JSONResponse({"received": body})

        routes = [Route("/echo", json_endpoint, methods=["POST"])]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)

        client = TestClient(app)
        try:
            response = client.post("/echo", content=b'{"test": "data"}', headers={"Content-Type": ""})
        except:
            response = client.post("/echo", content=b'{"test": "data"}', headers={"Content-Type": ""})
        assert response.status_code == 415

    def test_unsupported_media_type(self):
        """Test that unsupported content types return 415."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        from app.middleware.validation import ValidationMiddleware

        async def json_endpoint(request):
            body = await request.json()
            return JSONResponse({"received": body})

        routes = [Route("/json", json_endpoint, methods=["POST"])]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)

        client = TestClient(app)
        try:
            response = client.post(
                "/json",
                content=b"not json",
                headers={"Content-Type": "text/plain"}
            )
        except:
            response = client.post(
                "/json",
                content=b"not json",
                headers={"Content-Type": "text/plain"}
            )
        assert response.status_code == 415

    def test_valid_json_content_type(self):
        """Test that valid JSON content type is accepted."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        from app.middleware.validation import ValidationMiddleware

        async def json_endpoint(request):
            body = await request.json()
            return JSONResponse({"received": body})

        routes = [Route("/json", json_endpoint, methods=["POST"])]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)

        client = TestClient(app)
        response = client.post(
            "/json",
            content=b'{"test": "data"}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200

    def test_json_validation_error(self):
        """Test that invalid JSON returns 422."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        from app.middleware.validation import ValidationMiddleware

        async def json_endpoint(request):
            body = await request.json()
            return JSONResponse({"received": body})

        routes = [Route("/json", json_endpoint, methods=["POST"])]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)

        client = TestClient(app)
        try:
            response = client.post(
                "/json",
                content=b'{invalid json',
                headers={"Content-Type": "application/json"}
            )
        except:
            response = client.post(
                "/json",
                content=b'{invalid json',
                headers={"Content-Type": "application/json"}
            )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_JSON"

    def test_payload_too_large(self):
        """Test that oversized payloads are rejected."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        from app.middleware.validation import ValidationMiddleware

        async def echo_endpoint(request):
            body = await request.json()
            return JSONResponse({"received": True})

        routes = [Route("/echo", echo_endpoint, methods=["POST"])]
        app = Starlette(routes=routes)
        # Set very small max body size
        app.add_middleware(ValidationMiddleware, max_body_size=100)

        client = TestClient(app)
        # Send a payload larger than max_body_size
        large_data = b"x" * 200
        try:
            response = client.post(
                "/echo",
                content=large_data,
                headers={"Content-Type": "application/json", "Content-Length": str(len(large_data))}
            )
        except:
            response = client.post(
                "/echo",
                content=large_data,
                headers={"Content-Type": "application/json", "Content-Length": str(len(large_data))}
            )
        assert response.status_code == 413

    def test_validation_error_response_format(self):
        """Test that validation errors have proper structure."""
        from app.middleware.validation import ValidationError

        error = ValidationError("email", "Invalid email format", "validation_error")
        error_dict = error.to_dict()

        assert error_dict["field"] == "email"
        assert error_dict["message"] == "Invalid email format"
        assert error_dict["type"] == "validation_error"

    def test_validation_context(self):
        """Test ValidationContext functionality."""
        from app.middleware.validation import ValidationContext, ValidationRule, ValidationError

        context = ValidationContext()
        assert context.has_errors is False

        context.add_error("name", "Name is required")
        assert context.has_errors is True

        errors = context.get_error_dict()
        assert "validation_errors" in errors
        assert "error_count" in errors
        assert errors["error_count"] == 1

    def test_validation_rule(self):
        """Test ValidationRule functionality."""
        from app.middleware.validation import ValidationRule

        rule = ValidationRule(
            field="email",
            required=True,
            max_length=254,
            pattern=r"^[^@]+@[^@]+\.[^@]+$"
        )

        assert rule.field == "email"
        assert rule.required is True
        assert rule.max_length == 254
        assert rule.pattern == r"^[^@]+@[^@]+\.[^@]+$"

    def test_get_requests_skip_validation(self):
        """Test that GET requests skip body validation."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        from app.middleware.validation import ValidationMiddleware

        async def json_endpoint(request):
            # Don't try to read JSON body for GET requests
            return JSONResponse({"received": True, "method": "GET"})

        routes = [Route("/json", json_endpoint, methods=["GET", "POST"])]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)

        # GET should not require content-type
        client = TestClient(app)
        response = client.get("/json")
        # GET should succeed (may return 422 if no JSON body, but won't be 415)
        assert response.status_code != 415


class TestMiddlewareIntegration:
    """Test that all middleware works together correctly."""

    def test_request_flow_through_all_middleware(self):
        """Test that a request flows through all middleware layers."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from app.middleware.request_id import RequestIDMiddleware
        from app.middleware.timing import TimingMiddleware
        from app.middleware.validation import ValidationMiddleware

        async def test_endpoint(request):
            request_id = getattr(request.state, 'request_id', None)
            return JSONResponse({
                "status": "ok",
                "request_id": request_id,
            })

        routes = [Route("/test", test_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)
        app.add_middleware(TimingMiddleware)
        app.add_middleware(RequestIDMiddleware)

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["request_id"] is not None
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers

    def test_error_propagation_through_middleware(self):
        """Test that errors propagate correctly through middleware layers."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from app.middleware.request_id import RequestIDMiddleware
        from app.middleware.timing import TimingMiddleware
        from app.middleware.exception_handler import ExceptionHandlerMiddleware
        from app.middleware.validation import ValidationMiddleware

        def failing_endpoint(request):
            raise RuntimeError("Integration test failure")

        routes = [Route("/fail", failing_endpoint)]
        app = Starlette(routes=routes)
        app.add_middleware(ValidationMiddleware)
        app.add_middleware(ExceptionHandlerMiddleware)
        app.add_middleware(TimingMiddleware)
        app.add_middleware(RequestIDMiddleware)

        client = TestClient(app)
        try:
            response = client.get("/fail")
        except:
            response = client.get("/fail")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "request_id" in data["error"]
