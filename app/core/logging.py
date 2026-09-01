"""Structured logging configuration.

Production emits JSON so that log shippers can index fields without regex
rules. Local development emits single-line text to stay readable.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from types import TracebackType

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


def configure_logging(level: str, fmt: str) -> None:
    """Install the root handler used by the whole process."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn installs its own handlers; route them through ours so access
    # lines and application lines share one format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True


@contextmanager
def request_scope(**fields: object) -> Iterator[None]:
    """Attach contextual fields to every log line emitted inside the block.

    Uses a LoggerAdapter-free approach so that third-party loggers also pick
    the fields up without needing to be wrapped.
    """
    if not fields:
        yield
        return

    previous = logging.Logger.makeRecord

    def makeRecord(
        self: logging.Logger,
        name: str,
        level: int,
        fn: str,
        lno: int,
        msg: object,
        args: tuple[object, ...] | Mapping[str, object],
        exc_info: tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None] | None,
        func: str | None = None,
        extra: Mapping[str, object] | None = None,
        sinfo: str | None = None,
    ) -> logging.LogRecord:
        merged = {**(extra or {}), **fields}
        return previous(self, name, level, fn, lno, msg, args, exc_info, func, merged, sinfo)

    logging.Logger.makeRecord = makeRecord  # type: ignore[method-assign]
    try:
        yield
    finally:
        logging.Logger.makeRecord = previous  # type: ignore[method-assign]
