import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Dict, Iterator, Optional
from uuid import uuid4


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_klr_logging_configured", False):
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root._klr_logging_configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields) -> None:
    logger.log(level, event, extra={"event": event, "fields": fields})


def ensure_trace_id(trace_id: Optional[str] = None) -> str:
    return trace_id or uuid4().hex[:12]


@contextmanager
def stage_timer(timings_ms: Dict[str, float], stage_name: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        timings_ms[stage_name] = round((perf_counter() - start) * 1000, 2)
