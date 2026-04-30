"""
Exception handler middleware for API requests.

Provides comprehensive exception handling with structured error responses,
stack trace logging, and configurable error formats per environment.
"""

import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware that catches unhandled exceptions and returns structured error responses.

    In debug mode, includes detailed stack traces and error details.
    In production mode, returns generic error messages for security.
    """

    # Default error response for unexpected server errors
    DEFAULT_ERROR_CODE = "INTERNAL_SERVER_ERROR"
    DEFAULT_ERROR_MESSAGE = "Internal server error"
    DEFAULT_STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Validation error mapping
    VALIDATION_ERROR_MAP = {
        "ValueError": "invalid_value",
        "TypeError": "invalid_type",
        "KeyError": "missing_field",
        "IndexError": "invalid_index",
    }

    def __init__(self, app, include_health: bool = False, log_exceptions: bool = True):
        """Initialize the exception handler middleware.

        Args:
            app: The ASGI application to wrap.
            include_health: Whether to include health check paths in error handling.
            log_exceptions: Whether to log exceptions to the logger.
        """
        super().__init__(app)
        self.include_health = include_health
        self.log_exceptions_enabled = log_exceptions
        self.app_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Process each request, catching unhandled exceptions.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response: The HTTP response, with error details if an exception occurred.
        """
        # Skip health check if configured
        path = request.url.path
        if path in ("/health", "/readiness", "/liveness") and not self.include_health:
            return await call_next(request)

        try:
            return await call_next(request)
        except Exception as exc:
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exception: Exception) -> JSONResponse:
        """Handle an exception and return a structured JSON error response.

        Args:
            request: The HTTP request that caused the exception.
            exception: The exception that was raised.

        Returns:
            JSONResponse: A structured error response.
        """
        request_id = getattr(request.state, 'request_id', 'unknown')
        error_code = self._get_error_code(exception)
        status_code = self._get_status_code(exception)

        # Log the exception with full context
        self.app_logger.error(
            f"[Request {request_id}] Unhandled exception: {type(exception).__name__}: {exception}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error_type": type(exception).__name__,
                "error_code": error_code,
                "traceback": traceback.format_exc(),
            },
        )

        # Build error response content
        response_content = {
            "error": {
                "code": error_code,
                "message": self._get_error_message(exception),
                "path": request.url.path,
            }
        }

        # Include request ID in response for tracing
        response_content["error"]["request_id"] = request_id

        # Include traceback and details in debug mode
        from app.config import settings
        if settings.debug:
            response_content["error"]["traceback"] = traceback.format_exc()
            response_content["error"]["detail"] = str(exception)

        return JSONResponse(
            status_code=status_code,
            content=response_content,
            headers={"X-Request-ID": request_id} if hasattr(request.state, 'request_id') else None,
        )

    def _get_error_code(self, exception: Exception) -> str:
        """Get an error code based on the exception type.

        Args:
            exception: The exception that was raised.

        Returns:
            str: A machine-readable error code.
        """
        exception_type = type(exception).__name__

        # Check against our error code mapping
        for base_type, code in self.VALIDATION_ERROR_MAP.items():
            if exception_type == base_type:
                return code

        # Handle common exception types
        if isinstance(exception, ValueError):
            return "invalid_value"
        if isinstance(exception, TypeError):
            return "invalid_type"
        if isinstance(exception, KeyError):
            return "missing_field"
        if isinstance(exception, IndexError):
            return "invalid_index"

        # Default to internal server error
        return self.DEFAULT_ERROR_CODE

    def _get_status_code(self, exception: Exception) -> int:
        """Get the HTTP status code for the exception.

        Args:
            exception: The exception that was raised.

        Returns:
            int: The HTTP status code.
        """
        # Handle common exception types with specific status codes
        if isinstance(exception, ValueError):
            return status.HTTP_400_BAD_REQUEST
        if isinstance(exception, TypeError):
            return status.HTTP_400_BAD_REQUEST
        if isinstance(exception, KeyError):
            return status.HTTP_404_NOT_FOUND
        if isinstance(exception, IndexError):
            return status.HTTP_404_NOT_FOUND

        # Default to 500 for unhandled exceptions
        return self.DEFAULT_STATUS_CODE

    def _get_error_message(self, exception: Exception) -> str:
        """Get a user-friendly error message.

        Args:
            exception: The exception that was raised.

        Returns:
            str: A user-friendly error message.
        """
        from app.config import settings

        if settings.debug:
            return str(exception) if str(exception) else self.DEFAULT_ERROR_MESSAGE

        return self.DEFAULT_ERROR_MESSAGE