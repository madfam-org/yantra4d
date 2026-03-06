"""Structured logging configuration with JSON and text formatters."""
import json
import logging
import os

from flask import g


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects for structured log ingestion."""

    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach request_id when running inside a Flask request context.
        try:
            log_entry["request_id"] = g.request_id
        except (RuntimeError, AttributeError):
            pass
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(debug: bool = False):
    """Configure the root logger based on LOG_FORMAT env var.

    Args:
        debug: When True the root logger level is set to DEBUG, otherwise INFO.

    Environment:
        LOG_FORMAT: ``json`` for structured JSON output (production),
                    ``text`` (default) for human-readable lines.
    """
    log_format = os.getenv("LOG_FORMAT", "text")
    level = logging.DEBUG if debug else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicate output.
    root.handlers.clear()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root.addHandler(handler)
