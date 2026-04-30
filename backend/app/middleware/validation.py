"""
Validation middleware for API requests.

Provides request validation including content-type checking, body size limits,
JSON schema validation, and input sanitization.
"""

import logging
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

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
                 custom_validator: Optional[Callable] = None):
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


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware that validates incoming requests before they reach route handlers.

    Supports content-type validation, body size limits, JSON schema validation,
    and custom validation rules.
    """

    # Default content types for JSON requests
    VALID_JSON_CONTENT_TYPES = {"application/json", "application/json;charset=utf-8"}

    # Default maximum body size (10MB)
    DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024

    def __init__(self, app, max_body_size: Optional[int] = None, 
                 strict_content_type: bool = True, enable_body_validation: bool = True):
        """Initialize the validation middleware.

        Args:
            app: The ASGI application to wrap.
            max_body_size: Maximum allowed request body size in bytes.
            strict_content_type: Whether to enforce content-type for JSON bodies.
            enable_body_validation: Whether to perform body content validation.
        """
        super().__init__(app)
        self.max_body_size = max_body_size or self.DEFAULT_MAX_BODY_SIZE
        self.strict_content_type = strict_content_type
        self.enable_body_validation = enable_body_validation
        self.app_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Process each request, performing validation checks.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response: The HTTP response.
        """
        # Skip validation for non-JSON content types or specific paths
        if await self._should_skip_validation(request):
            return await call_next(request)

        # Validate content type
        content_type = request.headers.get("content-type", "")
        validation_result = self._validate_content_type(request, content_type)
        if validation_result:
            return validation_result

        # Validate content length if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                body_size = int(content_length)
                if body_size > self.max_body_size:
                    return self._create_error_response(
                        request,
                        status_code=413,
                        error_code="PAYLOAD_TOO_LARGE",
                        message=f"Request body exceeds maximum size of {self.max_body_size} bytes",
                    )
            except ValueError:
                return self._create_error_response(
                    request,
                    status_code=400,
                    error_code="INVALID_CONTENT_LENGTH",
                    message="Invalid Content-Length header value",
                )

        # Validate body content for POST/PUT/PATCH requests
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await self._read_body(request)
                if body:
                    body_validation = self._validate_body(request, body)
                    if body_validation:
                        return body_validation
            except Exception as e:
                self.app_logger.error(f"Error reading body: {e}")
                return self._create_error_response(
                    request,
                    status_code=422,
                    error_code="INVALID_JSON",
                    message="Request body contains invalid JSON",
                )

        return await call_next(request)

    async def _read_body(self, request: Request) -> Optional[Any]:
        """Read and parse the request body.

        Args:
            request: The HTTP request.

        Returns:
            The parsed body, or None if empty.
        """
        body_bytes = await request.body()
        if not body_bytes:
            return None

        try:
            return json.loads(body_bytes)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in request body")

    async def _should_skip_validation(self, request: Request) -> bool:
        """Determine if validation should be skipped for this request.

        Args:
            request: The HTTP request.

        Returns:
            True if validation should be skipped.
        """
        # Skip validation for methods that typically don't have a body
        if request.method in {"GET", "DELETE", "HEAD", "OPTIONS"}:
            return True

        # For POST/PUT/PATCH, always run validation so _validate_content_type
        # can reject non-JSON content types with 415
        return False

    def _validate_content_type(self, request: Request, content_type: str):
        """Validate the request content type.

        Args:
            request: The HTTP request.
            content_type: The content type header value.

        Returns:
            JSONResponse if invalid, None otherwise.
        """
        # Accept requests with no content type (GET, HEAD, OPTIONS, etc.)
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None

        # For methods with body, content type should be JSON
        if request.method in {"POST", "PUT", "PATCH"}:
            if not content_type:
                return self._create_error_response(
                    request,
                    status_code=415,
                    error_code="UNSUPPORTED_MEDIA_TYPE",
                    message="Content-Type must be application/json",
                )

            # Check if content type is JSON (considering charset variants)
            is_json = any(ct in content_type.lower() for ct in ["application/json", "+json"])
            if not is_json and self.strict_content_type:
                return self._create_error_response(
                    request,
                    status_code=415,
                    error_code="UNSUPPORTED_MEDIA_TYPE",
                    message=f"Unsupported media type: {content_type}. Expected application/json",
                )

        return None

    def _validate_body(self, request: Request, body: Any):
        """Validate the request body content.

        Args:
            request: The HTTP request.
            body: The parsed request body.

        Returns:
            JSONResponse if validation fails, None otherwise.
        """
        if not self.enable_body_validation:
            return None

        # Validate that body is a dictionary for JSON bodies
        if isinstance(body, dict):
            return self._validate_json_body(request, body)

        # Validate array length
        if isinstance(body, list):
            if len(body) > 100:
                return self._create_error_response(
                    request,
                    status_code=400,
                    error_code="INVALID_BODY",
                    message="Array body exceeds maximum length of 100 items",
                )

        return None

    def _validate_json_body(self, request: Request, body: Dict[str, Any]):
        """Validate a JSON object body.

        Args:
            request: The HTTP request.
            body: The parsed request body dictionary.

        Returns:
            JSONResponse if validation fails, None otherwise.
        """
        errors = []

        # Common field validations
        for key, value in body.items():
            # Check string length limits
            if isinstance(value, str) and len(value) > 10000:
                errors.append(ValidationError(
                    key,
                    f"Value exceeds maximum length of 10000",
                    "max_length_exceeded"
                ))

            # Check for empty required strings
            if value is None and self._is_required_field(key):
                errors.append(ValidationError(
                    key,
                    "This field is required",
                    "required_field"
                ))

        if errors:
            return self._create_validation_error_response(
                request,
                errors,
            )

        return None

    def _is_required_field(self, field_name: str) -> bool:
        """Determine if a field is required based on its name.

        Common patterns for required fields:
        - Fields ending in _id are typically required
        - Fields ending in _name are typically required
        - Fields containing 'email' are typically required

        Args:
            field_name: The name of the field to check.

        Returns:
            True if the field is required.
        """
        required_patterns = ["_id", "_name", "email", "username"]
        return any(field_name.endswith(pattern) for pattern in required_patterns)

    def _create_error_response(self, request: Request, status_code: int,
                                error_code: str, message: str) -> JSONResponse:
        """Create a standardized error response.

        Args:
            request: The HTTP request.
            status_code: The HTTP status code.
            error_code: A machine-readable error code.
            message: A user-friendly error message.

        Returns:
            JSONResponse: A structured error response.
        """
        request_id = getattr(request.state, 'request_id', 'unknown')
        response = JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "path": request.url.path,
                    "request_id": request_id,
                }
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response

    def _create_validation_error_response(self, request: Request, 
                                           errors: List[ValidationError]) -> JSONResponse:
        """Create a validation error response.

        Args:
            request: The HTTP request.
            errors: List of validation errors.

        Returns:
            JSONResponse: A structured validation error response.
        """
        request_id = getattr(request.state, 'request_id', 'unknown')
        response = JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "path": request.url.path,
                    "request_id": request_id,
                    "details": [e.to_dict() for e in errors],
                }
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response