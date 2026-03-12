from __future__ import annotations

import logging
import logging.config
from datetime import datetime, timezone
from typing import Any

import orjson

from app.core.config import AppSettings
from app.core.request_context import get_request_id

_RESERVED_LOG_RECORD_KEYS = set(logging.makeLogRecord({}).__dict__.keys())


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_KEYS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return orjson.dumps(payload).decode("utf-8")


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        base = (
            f"{timestamp} {record.levelname:<8} {record.name} "
            f"[request_id={getattr(record, 'request_id', '-')}] {record.getMessage()}"
        )
        if record.exc_info:
            return f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(settings: AppSettings) -> None:
    formatter_class = "app.core.logging.JsonFormatter"
    if settings.log_format == "console":
        formatter_class = "app.core.logging.ConsoleFormatter"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {
                    "()": "app.core.logging.RequestContextFilter",
                },
            },
            "formatters": {
                "default": {
                    "()": formatter_class,
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_context"],
                },
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["default"],
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": settings.log_level, "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "level": settings.log_level, "propagate": False},
                "uvicorn.access": {"handlers": ["default"], "level": settings.log_level, "propagate": False},
            },
        }
    )
