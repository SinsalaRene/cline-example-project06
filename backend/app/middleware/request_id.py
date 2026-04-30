"""
Request ID middleware for tracking API requests.

Adds a unique request ID to every request/response pair for traceability.
If no X-Request-ID header is provided in the request, a UUID4 is generated automatically.
"""

import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a unique request ID to every request and response.

    The request ID is extracted from the X-Request-ID header if provided,
    otherwise a new UUID4 is generated. The same ID is added to the response
    as X-Request-ID header for client-side correlation.
    """

    REQUEST_ID_HEADER = "X-Request-ID"
    RESPONSE_ID_HEADER = "X-Request-ID"

    def __init__(self, app):
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
        """
        super().__init__(app)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process each request, adding a unique ID to the request and response.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/handler in the chain.

        Returns:
            Response: The HTTP response with request ID header.
        """
        # Get or generate request ID
        request_id = request.headers.get(self.REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())
            self.logger.info(f"Generated new request ID: {request_id}")

        # Attach request ID to request state for use in routes
        request.state.request_id = request_id

        # Log the request with its ID
        self.logger.info(
            f"[Request {request_id}] {request.method} {request.url.path}",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )

        # Process the request and get the response
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.RESPONSE_ID_HEADER] = request_id

        # Log the response with its ID
        self.logger.info(
            f"[Request {request_id}] Response: {response.status_code}",
            extra={"request_id": request_id, "status_code": response.status_code},
        )

        return response