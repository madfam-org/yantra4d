"""
Shared route helpers for consistent error handling, STL cleanup, and path safety.
"""
import functools
import logging
import os
import re
from pathlib import Path
from typing import Optional

from flask import g, jsonify, request

from config import Config

logger = logging.getLogger(__name__)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9_]+")


def _derive_error_code(message: str) -> str:
    """Derive a machine-readable error code from a human message.

    Lowercases, replaces spaces/non-alphanumeric with underscores,
    collapses runs, and strips leading/trailing underscores.
    """
    code = message.lower().replace(" ", "_")
    code = _NON_ALNUM_RE.sub("_", code)
    code = re.sub(r"_+", "_", code).strip("_")
    return code


def cleanup_old_stl_files(parts: list[str], static_folder: str, prefix: str | None = None, export_format: str = "stl") -> None:
    """Remove old render files for the given parts and export format."""
    stl_prefix = prefix or Config.STL_PREFIX
    for part in parts:
        old_path = os.path.join(static_folder, f"{stl_prefix}{part}.{export_format}")
        try:
            os.remove(old_path)
        except OSError:
            pass


def safe_join_path(base_dir: str, filename: str) -> Optional[Path]:
    """Safely join a base directory with a filename, guarding against path traversal.

    Returns the resolved Path if safe, or None if the path escapes base_dir.
    """
    resolved = Path(os.path.join(base_dir, filename)).resolve()
    if not resolved.is_relative_to(Path(base_dir).resolve()):
        return None
    return resolved


def error_response(message: str, status_code: int = 500, error_code: str | None = None):
    """Return a standardized JSON error response with request tracing.

    Args:
        message: Human-readable error description.
        status_code: HTTP status code (default 500).
        error_code: Machine-readable code. When *None* one is auto-derived
            from *message* (lowercased, spaces to underscores, non-alnum stripped).
    """
    request_id = getattr(g, "request_id", None)
    logger.error("[%s] [%s] %s", status_code, request_id or "-", message)
    derived_code = error_code if error_code is not None else _derive_error_code(message)
    body: dict = {"status": "error", "error": message, "error_code": derived_code}
    if request_id:
        body["request_id"] = request_id
    return jsonify(body), status_code


def require_json_body(f):
    """Decorator: reject request with 400 if body is not a JSON object."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        data = request.json
        if not data:
            return error_response("Request body must be JSON", 400)
        if not isinstance(data, dict):
            return error_response("Request body must be a JSON object", 400)
        return f(*args, **kwargs)
    return decorated


def handle_exceptions(f):
    """Decorator: catch unhandled exceptions, log them, and return a structured error."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            request_id = getattr(g, "request_id", None)
            logger.exception(
                "Unhandled exception in %s [request_id=%s]", f.__name__, request_id
            )
            return error_response(
                "Internal server error",
                500,
                error_code="INTERNAL_ERROR",
            )
    return decorated
