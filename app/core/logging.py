"""Structured logging configuration.

Production emits JSON so that log shippers can index fields without regex
rules. Local development emits single-line text to stay readable.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from opentelemetry import trace

_RESERVED = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Anything attached via `extra=` is promoted to a top-level field.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Render log records as `LEVEL message key=value` lines."""

    def format(self, record: logging.LogRecord) -> str:
        extra = " ".join(
            f"{key}={value!r}" for key, value in record.__dict__.items() if key not in _RESERVED and key != "message"
        )
        base = f"{record.levelname:<7} {record.getMessage()}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return f"{base} {extra}".rstrip()


def configure_logging(
    level: str, fmt: str, *, service: str = "vue-h5-template-ai-service", environment: str = "development"
) -> None:
    """Install the root handler used by the whole process."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter(service, environment))
    handler.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for name in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)

    # Uvicorn installs its own handlers; route them through ours so access
    # lines and application lines share one format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True


_context: ContextVar[dict[str, object] | None] = ContextVar("log_context", default=None)


class ContextFilter(logging.Filter):
    def __init__(self, service: str, environment: str) -> None:
        super().__init__()
        self.service, self.environment = service, environment

    def filter(self, record: logging.LogRecord) -> bool:
        fields = {"service": self.service, "environment": self.environment, **(_context.get() or {})}
        current = trace.get_current_span().get_span_context()
        if current.is_valid:
            fields["traceId"] = format(current.trace_id, "032x")
        for key, value in fields.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


@contextmanager
def request_scope(**fields: object) -> Iterator[None]:
    """Task-local context, inherited by provider tasks without global patches."""
    token = _context.set({**(_context.get() or {}), **fields})
    try:
        yield
    finally:
        _context.reset(token)


def correlation_headers() -> dict[str, str]:
    request_id = (_context.get() or {}).get("requestId")
    return {"X-Request-ID": str(request_id)} if request_id else {}
