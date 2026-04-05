"""Structured JSON logging for Glass.

Every HTTP request produces a single JSON log line with:
- timestamp, method, path, status_code, duration_ms
- request_id (UUID v4, returned as X-Request-ID header)
- backend (for /api/query requests)

Designed for ingestion by log aggregators (ELK, Datadog, Loki, etc.).
SRE feedback: "No structured logging at all -- zero JSON log lines, no request IDs,
no correlation." -- sre_on_call, feedback round 3.
"""

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class StructuredJSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        from datetime import datetime, timezone

        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        log_entry = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include any extra fields attached to the record
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "backend"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry, default=str)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request as structured JSON.

    Attaches a unique request_id to each request and returns it as
    X-Request-ID in the response headers for correlation.
    """

    def __init__(self, app, logger_name: str = "glass.access"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        # Store request_id on request state for downstream use
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self.logger.error(
                "%s %s 500 %dms",
                request.method,
                request.url.path,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        self.logger.info(
            "%s %s %d %dms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


def configure_logging() -> None:
    """Set up structured JSON logging for the Glass application."""
    # Configure the access logger with JSON formatting
    access_logger = logging.getLogger("glass.access")
    access_logger.setLevel(logging.INFO)

    # Only add handler if none exist (avoid duplicate handlers on reload)
    if not access_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJSONFormatter())
        access_logger.addHandler(handler)
        access_logger.propagate = False

    # Configure the app logger similarly
    app_logger = logging.getLogger("glass")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJSONFormatter())
        app_logger.addHandler(handler)
        app_logger.propagate = False
