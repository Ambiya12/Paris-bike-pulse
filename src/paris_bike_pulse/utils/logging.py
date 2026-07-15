"""Structured logging helpers for data pipelines."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TextIO

from paris_bike_pulse.config import Settings

PACKAGE_LOGGER_NAME = "paris_bike_pulse"
_RESERVED_FIELDS = frozenset(
    {
        *logging.LogRecord(
            name="",
            level=0,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        ).__dict__,
        "asctime",
        "exception",
        "level",
        "logger",
        "message",
        "timestamp",
    }
)


def _record_context(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED_FIELDS and not key.startswith("_")
    }


class JsonLogFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record and its contextual fields."""
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_record_context(record))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True)


class TextLogFormatter(logging.Formatter):
    """Format readable logs while preserving structured context."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Append contextual fields to a conventional text log line."""
        context = _record_context(record)
        message = super().format(record)
        if not context:
            return message

        serialized_context = json.dumps(
            context,
            default=str,
            ensure_ascii=False,
            sort_keys=True,
        )
        return f"{message} {serialized_context}"


class _ContextLoggerAdapter(logging.LoggerAdapter):
    def process(
        self,
        msg: object,
        kwargs: dict[str, object],
    ) -> tuple[object, dict[str, object]]:
        message_context = kwargs.get("extra", {})
        if not isinstance(message_context, dict):
            raise TypeError("log record extra context must be a dictionary")

        kwargs["extra"] = {**self.extra, **message_context}
        return msg, kwargs


def configure_logging(
    settings: Settings,
    *,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure the project logger from validated application settings."""
    handler = logging.StreamHandler(stream)
    if settings.log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(TextLogFormatter())

    project_logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    project_logger.handlers.clear()
    project_logger.addHandler(handler)
    project_logger.setLevel(settings.log_level)
    project_logger.propagate = False
    return project_logger


def get_pipeline_logger(
    name: str,
    *,
    pipeline_run_id: str,
    **context: object,
) -> logging.LoggerAdapter:
    """Return a project logger carrying pipeline and source context."""
    if not name.strip():
        raise ValueError("logger name must not be empty")
    if not pipeline_run_id.strip():
        raise ValueError("pipeline_run_id must not be empty")

    logger_name = name
    if name != PACKAGE_LOGGER_NAME and not name.startswith(f"{PACKAGE_LOGGER_NAME}."):
        logger_name = f"{PACKAGE_LOGGER_NAME}.{name}"

    logger = logging.getLogger(logger_name)
    return _ContextLoggerAdapter(
        logger,
        {"pipeline_run_id": pipeline_run_id, **context},
    )
