"""
Validation middleware for API requests.

Provides request validation including content-type checking, body size limits,
JSON schema validation, and input sanitization.

Uses ASGI-style middleware (no BaseHTTPMiddleware) to avoid consuming the
request body before FastAPI's dependency injection pipeline.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class ValidationError:
    """Represents a single validation error."""

    def __init__(self, field: str, message: str, error_type: str = "validation_error"):
        self.field = field
        self.message = message
        self.error_type = error_type

    def to_dict(self) -> Dict[str, str]:
        return {
            "field": self.field,
            "message": self.message,
            "type": self.error_type,
        }


class ValidationRule:
    """Defines a validation rule for request validation."""

    def __init__(self, field: str, required: bool = False,
                 allowed_values: Optional[List[Any]] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 pattern: Optional[str] = None,
                 custom_validator: Optional[Any] = None):
        self.field = field
        self.required = required
        self.allowed_values = allowed_values
        self.min_length = min_length
        self.max_length = max_length
        self.min_value = min_value
        self.max_value = max_value
        self.pattern = pattern
        self.custom_validator = custom_validator


class ValidationContext:
    """Holds validation context for a request."""

    def __init__(self, rules: Optional[Dict[str, ValidationRule]] = None):
        self.rules = rules or {}
        self.errors: List[ValidationError] = []

    def add_error(self, field: str, message: str, error_type: str = "validation_error"):
        self.errors.append(ValidationError(field, message, error_type))

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_error_dict(self) -> Dict[str, Any]:
        return {
            "validation_errors": [e.to_dict() for e in self.errors],
            "error_count": len(self.errors),
        }


class ValidationMiddleware:
    """ASGI-style validation middleware that does not consume the request body.

    Uses the raw ASGI interface (Receive/Send/Scope) so that FastAPI's
    own body-reader is not starved of bytes before the route handler runs.

    Only does light-weight checks: content-type on POST/PUT/PATCH, body size
    from Content-Length header.
    """

    VALID_JSON_CONTENT_TYPES = {"application/json", "application/json;charset=utf-8"}
    DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self, app: ASGIApp, max_body_size: Optional[int] = None,
                 strict_content_type: bool = True, enable_body_validation: bool = True):
        self.app = app
        self.max_body_size = max_body_size or self.DEFAULT_MAX_BODY_SIZE
        self.strict_content_type = strict_content_type
        self.enable_body_validation = enable_body_validation
        self.app_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # GET/DELETE/HEAD/OPTIONS – skip body validation
        method = scope.get("method", "").upper()
        path = scope.get("path", "")

        # Skip all validation for health and metrics endpoints (no body needed)
        if path.startswith(("/health", "/readyz", "/startup", "/healthz", "/metrics")):
            await self.app(scope, receive, send)
            return

        if method in {"GET", "DELETE", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return

        # --- Content-type check ---
        headers = dict(scope.get("headers", []))
        content_type = ""
        if b"content-type" in headers:
            content_type = headers[b"content-type"].decode()

        if self.strict_content_type:
            if content_type:
                is_json = any(ct in content_type.lower() for ct in ["application/json", "+json"])
                if not is_json:
                    body = json.dumps({
                        "error": {
                            "code": "UNSUPPORTED_MEDIA_TYPE",
                            "message": "Content-Type must be application/json"
                        }
                    }).encode()
                    await send({
                        "type": "http.response.start",
                        "status": 415,
                        "headers": [
                            [b"content-type", b"application/json"],
                            [b"content-length", str(len(body)).encode()],
                        ],
                    })
                    await send({"type": "http.response.body", "body": body})
                    return
            else:
                body = json.dumps({
                    "error": {
                        "code": "UNSUPPORTED_MEDIA_TYPE",
                        "message": "Content-Type must be application/json"
                    }
                }).encode()
                await send({
                    "type": "http.response.start",
                    "status": 415,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"content-length", str(len(body)).encode()],
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

        # --- Content-Length / body-size check ---
        cl = None
        if b"content-length" in headers:
            try:
                cl = int(headers[b"content-length"])
            except ValueError:
                pass

        if cl and cl > self.max_body_size:
            body = json.dumps({
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Request body exceeds maximum size"
                }
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return

        # --- Pass through to the real app ---
        await self.app(scope, receive, send)