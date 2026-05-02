"""
Structured Logging - Production Readiness.

Provides structured JSON logging with request correlation IDs,
log levels, and integration-ready output for log aggregation systems
(ELK, CloudWatch, Datadog, etc.).
"""

import os
import sys
import json
import logging
import traceback
import uuid
import time
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from contextvars import ContextVar
from pathlib import Path

# Context variable for request correlation
request_id_var: ContextVar[str] = ContextVar("request_id", default="N/A")
span_id_var: ContextVar[str] = ContextVar("span_id", default="N/A")
traceparent_var: ContextVar[str] = ContextVar("traceparent", default="N/A")


class RequestCorrelationFilter(logging.Filter):
    """Adds request correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to the log record."""
        record.request_id = request_id_var.get()
        record.span_id = span_id_var.get()
        record.traceparent = traceparent_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs as JSON lines suitable for ingestion by log aggregation
    systems (ELK, CloudWatch, Datadog, Fluentd, etc.).
    """

    def __init__(self, include_exception: bool = True, include_context: bool = True):
        """Initialize the JSON formatter."""
        super().__init__()
        self.include_exception = include_exception
        self.include_context = include_context
        self._thread_id = threading.current_thread().ident

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pid": os.getpid(),
            "tid": threading.current_thread().ident,
            "request_id": getattr(record, "request_id", request_id_var.get()),
            "span_id": getattr(record, "span_id", span_id_var.get()),
            "traceparent": getattr(record, "traceparent", traceparent_var.get()),
        }

        # Add exception info
        if record.exc_info and self.include_exception:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stack_trace": "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None,
            }

        # Add extra fields from record
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["extra"] = record.extra_data

        # Add process info
        if self.include_context:
            log_entry["process"] = {
                "name": record.name.split(".")[0] if "." in record.name else record.name,
                "module": record.module,
            }

        # Remove standard traceback from message if it's already in exception
        if record.exc_info and record.exc_info[2]:
            # Stack trace is already captured above
            pass

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter with color support.
    
    Uses ANSI colors for log levels and structured output.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",        # Green
        "WARNING": "\033[33m",     # Yellow
        "ERROR": "\033[31m",       # Red
        "CRITICAL": "\033[35m",    # Magenta
        "RESET": "\033[0m",        # Reset
    }

    USE_COLORS = sys.stderr.isatty()

    def __init__(self, include_request_id: bool = True):
        """Initialize the console formatter."""
        super().__init__()
        self.include_request_id = include_request_id

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record for human consumption."""
        color = ""
        reset = ""

        if self.USE_COLORS:
            color = self.COLORS.get(record.levelname, "")
            reset = self.COLORS["RESET"]

        # Build the message
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        level = record.levelname.ljust(8)

        request_id = getattr(record, "request_id", request_id_var.get())
        request_id_str = f" [req={request_id}]" if request_id != "N/A" else ""

        message = record.getMessage()

        # Build the formatted output
        parts = [
            f"{color}[{timestamp}] {level}{reset}",
            f"[{record.name}]",
        ]

        if self.include_request_id and request_id_str:
            parts.append(request_id_str)

        output = " ".join(parts)
        output += f" - {message}"

        # Add exception info
        if record.exc_info:
            output += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return output


def setup_logging(
    level: str = "INFO",
    json_format: Optional[bool] = None,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    enable_console: bool = True,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting (None = auto-detect based on environment)
        log_file: Path to log file
        log_dir: Directory for log files
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Enable console output
        
    Returns:
        None
    """
    # Determine if we should use JSON formatting
    if json_format is None:
        # Use JSON format in production / Docker environments
        json_format = os.getenv("LOG_FORMAT", "json") in ("json", "structured") or \
                      os.getenv("ENVIRONMENT", "development") != "development"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Add request correlation filter
    correlation_filter = RequestCorrelationFilter()

    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = ConsoleFormatter()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter if json_format else ConsoleFormatter())
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)

    # File handler (rotating)
    if log_file or log_dir:
        log_dir_path = Path(log_dir) if log_dir else Path(".")
        log_dir_path.mkdir(parents=True, exist_ok=True)

        if log_file:
            log_path = log_dir_path / log_file
        else:
            log_path = log_dir_path / "application.log"

        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(correlation_filter)
        root_logger.addHandler(file_handler)

    # Ensure application loggers inherit from root
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger configured for this application."""
    logger = logging.getLogger(name)
    return logger


def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    extra: Optional[dict] = None,
) -> None:
    """
    Log an HTTP request in a structured format.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        extra: Additional context to log
    """
    log_data = {
        "type": "http_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "request_id": request_id_var.get(),
    }

    if extra:
        log_data["extra"] = extra

    # Use INFO for normal requests, WARNING for 4xx, ERROR for 5xx
    if status_code >= 500:
        logger.error(json.dumps(log_data, default=str))
    elif status_code >= 400:
        logger.warning(json.dumps(log_data, default=str))
    else:
        logger.info(json.dumps(log_data, default=str))


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[dict] = None,
    level: int = logging.ERROR,
) -> None:
    """
    Log an error with structured context.
    
    Args:
        logger: Logger instance
        error: The exception that occurred
        context: Additional context about the error
        level: Logging level
    """
    error_data = {
        "type": "error",
        "error_type": type(error).__name__,
        "message": str(error),
        "request_id": request_id_var.get(),
    }

    if context:
        error_data["context"] = context

    # Add traceback if available
    import traceback as _traceback
    tb = _traceback.format_exc()
    if tb and tb != "NoneType: None\n":
        error_data["traceback"] = tb

    logger.log(
        level,
        json.dumps(error_data, default=str),
        exc_info=True,
    )


def create_span_id() -> str:
    """Create a span ID for distributed tracing."""
    return uuid.uuid4().hex[:16]


def get_traceparent() -> str:
    """Get the current traceparent header value."""
    return traceparent_var.get()


def set_traceparent(traceparent: str) -> None:
    """Set the traceparent header value."""
    traceparent_var.set(traceparent)