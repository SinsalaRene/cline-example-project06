"""
Error Tracking - Production Readiness.

Provides centralized error tracking, reporting, and alerting with support
for Sentry, custom error handlers, and error analytics.
"""

import os
import sys
import traceback
import uuid
import time
import threading
import logging
import json
import traceback as tb_module
from datetime import datetime, timezone
from typing import Any, Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextvars import ContextVar
from functools import wraps
import inspect

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class ErrorCategory(str, Enum):
    """Error categories for grouping."""
    validation = "validation"
    authentication = "authentication"
    authorization = "authorization"
    database = "database"
    external_service = "external_service"
    timeout = "timeout"
    resource_not_found = "resource_not_found"
    rate_limit = "rate_limit"
    internal = "internal"
    business_logic = "business_logic"
    unknown = "unknown"


@dataclass
class ErrorReport:
    """Structured error report."""
    id: str
    timestamp: str
    severity: str
    category: str
    error_type: str
    message: str
    stack_trace: Optional[str]
    request_id: str
    endpoint: str
    method: str
    status_code: Optional[int]
    user_id: Optional[str]
    metadata: Dict[str, Any]
    context: Dict[str, Any]
    handled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class ErrorStats:
    """Error statistics."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_source: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[ErrorReport] = field(default_factory=list)
    error_rate_per_minute: float = 0.0
    first_error_at: Optional[str] = None
    last_error_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Error Handler Registry
# ---------------------------------------------------------------------------

class ErrorHandlerRegistry:
    """Registry for error handlers and reporters."""

    def __init__(self):
        self._handlers: Dict[str, list] = {}
        self._reporters: List[Callable] = []
        self._error_store: List[ErrorReport] = []
        self._stats = ErrorStats()
        self._lock = threading.Lock()
        self._max_store_size = int(os.getenv("ERROR_STORE_SIZE", "1000"))

    def register_handler(self, category: str, handler: Callable):
        """Register a handler for a specific error category."""
        if category not in self._handlers:
            self._handlers[category] = []
        self._handlers[category].append(handler)

    def register_reporter(self, reporter: Callable):
        """Register an error reporter (e.g., Sentry, Slack)."""
        self._reporters.append(reporter)

    def unregister_reporter(self, reporter: Callable):
        """Unregister an error reporter."""
        if reporter in self._reporters:
            self._reporters.remove(reporter)

    def add_error(self, error_report: ErrorReport) -> None:
        """Add an error report to the store."""
        with self._lock:
            # Update stats
            self._stats.total_errors += 1
            self._stats.errors_by_category[error_report.category] = \
                self._stats.errors_by_category.get(error_report.category, 0) + 1
            self._stats.errors_by_severity[error_report.severity] = \
                self._stats.errors_by_severity.get(error_report.severity, 0) + 1
            self._stats.last_error_at = datetime.now(timezone.utc).isoformat()

            if not self._stats.first_error_at:
                self._stats.first_error_at = error_report.timestamp

            # Store error
            self._error_store.append(error_report)

            # Limit store size
            if len(self._error_store) > self._max_store_size:
                self._error_store = self._error_store[-self._max_store_size:]

            # Call handlers
            self._call_handlers(error_report.category, error_report)

            # Call reporters
            self._call_reporters(error_report)

    def _call_handlers(self, category: str, error_report: ErrorReport) -> None:
        """Call all handlers for an error category."""
        handlers = self._handlers.get(category, [])
        for handler in handlers:
            try:
                handler(error_report)
            except Exception as e:
                logger.error(f"Error handler failed: {e}", exc_info=True)

    def _call_reporters(self, error_report: ErrorReport) -> None:
        """Call all registered reporters."""
        for reporter in self._reporters:
            try:
                reporter(error_report)
            except Exception as e:
                logger.error(f"Error reporter failed: {e}", exc_info=True)

    def get_stats(self) -> ErrorStats:
        """Get error statistics."""
        return self._stats

    def get_error_store(self) -> List[ErrorReport]:
        """Get stored errors."""
        return self._error_store[:]

    def clear_store(self) -> None:
        """Clear error store."""
        with self._lock:
            self._error_store.clear()


# Global error handler registry
_error_registry = ErrorHandlerRegistry()


# ---------------------------------------------------------------------------
# Sentry Integration (optional)
# ---------------------------------------------------------------------------

_sentry_initialized = False


def initialize_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    release: str = "1.0.0",
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.0,
) -> bool:
    """
    Initialize Sentry error tracking.
    
    Args:
        dsn: Sentry DSN (defaults to SENTRY_DSN env var)
        environment: Environment name
        release: Release/version string
        traces_sample_rate: Sample rate for tracing (0.0 to 1.0)
        profiles_sample_rate: Sample rate for profiling
        
    Returns:
        True if Sentry was initialized successfully, False otherwise
    """
    global _sentry_initialized

    if _sentry_initialized:
        return True

    try:
        import sentry_sdk  # type: ignore

        dsn = dsn or os.environ.get("SENTRY_DSN")
        if not dsn:
            logger.info("SENTRY_DSN not set, skipping Sentry initialization")
            return False

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            enable_tracing=True,
        )
        _sentry_initialized = True
        logger.info("Sentry initialized successfully")
        return True

    except ImportError:
        logger.info("sentry-sdk not installed, skipping Sentry initialization")
        return False
    except Exception as e:
        logger.warning(f"Failed to initialize Sentry: {e}")
        return False


def capture_exception(
    error: Exception,
    category: str = ErrorCategory.internal.value,
    severity: str = ErrorSeverity.error.value,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Optional[str]:
    """
    Capture and report an exception.
    
    Args:
        error: The exception to capture
        category: Error category
        severity: Error severity
        context: Additional context
        user_id: User ID if applicable
        request_id: Request ID if available
        
    Returns:
        The error report ID, or None if capturing failed
    """
    import traceback
    import sys

    request_id = request_id or _get_request_id()
    error_id = str(uuid.uuid4())

    # Format stack trace
    tb_lines = traceback.format_exception(type(error), error, error.__traceback__)

    # Create report
    report = ErrorReport(
        id=error_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity=severity,
        category=category,
        error_type=type(error).__name__,
        message=str(error),
        stack_trace="".join(tb_lines) if tb_lines else None,
        request_id=request_id,
        endpoint="",
        method="",
        status_code=None,
        user_id=user_id,
        metadata=context or {},
        context=context or {},
    )

    # Add to registry
    _error_registry.add_error(report)

    # Send to Sentry if available
    try:
        import sentry_sdk  # type: ignore
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error_id", error_id)
            scope.set_tag("category", category)
            scope.set_tag("severity", severity)
            scope.set_tag("request_id", request_id)
            if user_id:
                scope.set_user({"id": user_id})
            if context:
                scope.set_context("error_context", context)
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass  # Sentry not installed
    except Exception as e:
        logger.error(f"Failed to send error to Sentry: {e}", exc_info=True)

    return error_id


def capture_message(
    message: str,
    category: str = ErrorCategory.internal.value,
    severity: str = ErrorSeverity.warning.value,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Optional[str]:
    """
    Capture a log message as an error report.
    
    Args:
        message: The message to capture
        category: Error category
        severity: Error severity
        context: Additional context
        user_id: User ID if applicable
        request_id: Request ID if available
        
    Returns:
        The error report ID, or None if capturing failed
    """
    request_id = request_id or _get_request_id()
    error_id = str(uuid.uuid4())

    report = ErrorReport(
        id=error_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        severity=severity,
        category=category,
        error_type="Message",
        message=message,
        stack_trace=None,
        request_id=request_id,
        endpoint="",
        method="",
        status_code=None,
        user_id=user_id,
        metadata=context or {},
        context=context or {},
    )

    _error_registry.add_error(report)

    # Send to Sentry if available
    try:
        import sentry_sdk  # type: ignore
        sentry_sdk.capture_message(message)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to send message to Sentry: {e}", exc_info=True)

    return error_id


def _get_request_id() -> str:
    """Get the current request ID from context."""
    try:
        from app.logging import request_id_var
        return request_id_var.get()
    except Exception:
        return "N/A"


# ---------------------------------------------------------------------------
# Decorator-based Error Handling
# ---------------------------------------------------------------------------

def track_errors(
    error_category: str = ErrorCategory.internal.value,
    severity: str = ErrorSeverity.error.value,
    capture_user: bool = True,
):
    """
    Decorator to track errors in functions/methods.
    
    Usage:
        @track_errors(error_category=ErrorCategory.database.value)
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_id = _get_request_id()
            user_id = None
            if capture_user:
                try:
                    # Try to get user from context
                    from app.logging import request_id_var
                    user_id = getattr(request_id_var.get(), "user_id", None)
                except Exception:
                    pass

            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    error=e,
                    category=error_category,
                    severity=severity,
                    context={
                        "function": func.__name__,
                        "module": func.__module__,
                        "args": str(args)[:1000] if args else "",
                        "kwargs": str(kwargs)[:1000] if kwargs else "",
                    },
                    user_id=user_id,
                    request_id=request_id,
                )
                raise  # Re-raise the exception

        return wrapper
    return decorator


def handle_errors(
    error_category: str = ErrorCategory.internal.value,
    severity: str = ErrorSeverity.error.value,
    fallback: Optional[Callable] = None,
):
    """
    Decorator to handle errors in functions/methods with optional fallback.
    
    Usage:
        @handle_errors(error_category=ErrorCategory.validation.value)
        def validate_data(data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Call fallback if provided
                if fallback:
                    try:
                        return fallback(*args, **kwargs)
                    except Exception as fb_error:
                        logger.error(f"Fallback failed: {fb_error}", exc_info=True)

                # Capture error
                capture_exception(
                    error=e,
                    category=error_category,
                    severity=severity,
                    context={"function": func.__name__, "module": func.__module__},
                )

                # Re-raise if not handled gracefully
                raise

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# FastAPI Exception Handler
# ---------------------------------------------------------------------------

def create_exception_handlers(error_category_map: Optional[Dict[str, str]] = None) -> Dict:
    """
    Create FastAPI exception handlers for centralized error tracking.
    
    Args:
        error_category_map: Mapping of exception type names to categories
        
    Returns:
        Dict of exception handlers
    """
    category_map = error_category_map or {
        "ValidationError": ErrorCategory.validation.value,
        "HTTPException": ErrorCategory.validation.value,
        "AuthorizationError": ErrorCategory.authorization.value,
        "AuthenticationError": ErrorCategory.authentication.value,
        "NotFoundError": ErrorCategory.resource_not_found.value,
        "TimeoutError": ErrorCategory.timeout.value,
        "ConnectionError": ErrorCategory.external_service.value,
        "DatabaseError": ErrorCategory.database.value,
    }

    def _get_category(exception: Exception) -> str:
        """Determine category for an exception."""
        exc_type_name = type(exception).__name__
        for type_name, category in category_map.items():
            if type_name in exc_type_name:
                return category
        return ErrorCategory.internal.value

    def exception_handler(request, exc: Exception) -> Response:
        """Handle exceptions and track them."""
        from fastapi import Request, Response
        import traceback

        error_type = type(exc).__name__
        category = _get_category(exc)
        request_id = _get_request_id()
        user_id = getattr(request.state, "user_id", None)

        # Capture error
        capture_exception(
            error=exc,
            category=category,
            severity=ErrorSeverity.error.value if isinstance(exc, Exception) else ErrorSeverity.warning.value,
            context={
                "endpoint": str(request.url.path),
                "method": request.method,
                "error_type": error_type,
            },
            user_id=str(user_id) if user_id else None,
            request_id=request_id,
        )

        # Return appropriate response
        status_code = getattr(exc, "status_code", 500)
        message = str(exc) if len(str(exc)) < 500 else str(exc)[:500] + "...[truncated]"

        return Response(
            content=json.dumps({
                "error": {
                    "code": error_type,
                    "message": message,
                    "category": category,
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }),
            status_code=status_code,
            media_type="application/json",
        )

    return {"exception_handler": exception_handler}


def setup_error_tracking() -> None:
    """Set up error tracking system."""
    # Initialize from Sentry if available
    dsn = os.environ.get("SENTRY_DSN")
    if dsn:
        initialize_sentry(dsn=dsn)

    logger.info("Error tracking setup complete")


def get_error_stats() -> ErrorStats:
    """Get current error statistics."""
    return _error_registry.get_stats()


def get_error_report() -> Dict:
    """Get comprehensive error report."""
    stats = _error_registry.get_stats()

    report = {
        "error_stats": {
            "total_errors": stats.total_errors,
            "errors_by_category": stats.errors_by_category,
            "errors_by_severity": stats.errors_by_severity,
            "errors_by_source": stats.errors_by_source,
            "first_error_at": stats.first_error_at,
            "last_error_at": stats.last_error_at,
        },
        "recent_errors": [e.to_dict() for e in _error_registry.get_error_store()[-10:]],
        "sentry_initialized": _sentry_initialized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return report