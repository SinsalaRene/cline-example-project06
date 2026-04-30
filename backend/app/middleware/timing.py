"""
Timing and logging middleware for API requests.

Measures request processing time and logs comprehensive timing information
including method, path, status code, duration, and request ID.
"""

import time
import logging
from typing import Set
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware that measures and logs request processing time.

    Adds timing information to every request/response cycle, logging
    the duration in milliseconds. Sensitive headers are redacted
    from logs to protect credentials.
    """

    # Headers to redact in logs
    REDACTED_HEADERS: Set[str] = {"authorization", "cookie", "x-api-key", "x-secret-key"}

    # Fields to redact from request body
    SENSITIVE_FIELDS: Set[str] = {"password", "secret", "token", "key", "authorization"}

    # Logging format with timing context
    LOG_FORMAT = "[{request_id}] {method} {path} -> {status_code} ({duration_ms:.2f}ms)"

    def __init__(self, app):
        """Initialize the timing middleware.

        Args:
            app: The ASGI application to wrap.
        """
        super().__init__(app)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process each request, timing its execution.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response: The HTTP response.
        """
        # Record start time
        start_time = time.perf_counter()

        # Get request ID for correlation
        request_id = getattr(request.state, 'request_id', 'no-request-id')

        # Log the request with timing context
        self._log_request(request, request_id)

        # Process the request
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(
                f"[{request_id}] {request.method} {request.url.path} -> ERROR ({duration_ms:.2f}ms)",
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            log_method = self.logger.error
        elif status_code >= 400:
            log_method = self.logger.warning
        else:
            log_method = self.logger.info

        # Log the response with timing
        log_method(
            self.LOG_FORMAT.format(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            ),
            extra={"request_id": request_id},
        )

        # Add timing headers to response
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

    def _log_request(self, request: Request, request_id: str) -> None:
        """Log the incoming request details.

        Args:
            request: The HTTP request.
            request_id: The request ID for correlation.
        """
        # Get relevant headers (excluding sensitive ones)
        headers_to_log = {
            k: self._redact_value(k, v)
            for k, v in request.headers.items()
            if k.lower() not in self.REDACTED_HEADERS
        }

        self.logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "headers": headers_to_log,
                "query_params": dict(request.query_params),
            },
        )

    def _redact_value(self, header_name: str, value: str) -> str:
        """Redact sensitive header values.

        Args:
            header_name: The name of the header.
            value: The value of the header.

        Returns:
            str: The redacted value or original value.
        """
        if header_name.lower() in self.REDACTED_HEADERS:
            return "***REDACTED***"
        return value