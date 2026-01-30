"""
Shared route helpers for consistent error handling, STL cleanup, and path safety.
"""
import logging
import os
from pathlib import Path
from typing import Optional

from flask import jsonify

from config import Config

logger = logging.getLogger(__name__)


def cleanup_old_stl_files(parts: list[str], static_folder: str) -> None:
    """Remove old STL preview files for the given parts."""
    for part in parts:
        old_path = os.path.join(static_folder, f"{Config.STL_PREFIX}{part}.stl")
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


def error_response(message: str, status_code: int = 500):
    """Return a standardized JSON error response."""
    logger.error(f"[{status_code}] {message}")
    return jsonify({"status": "error", "error": message}), status_code
