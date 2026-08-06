"""
SCAD File CRUD API — read/write/create/delete .scad files within a project.
"""
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

import rate_limits
from extensions import limiter
from middleware.auth import require_tier
from utils.project_resolver import require_project
from utils.route_helpers import error_response, safe_join_path
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

editor_bp = Blueprint("editor", __name__)

MAX_FILE_SIZE = 512 * 1024  # 512KB
ALLOWED_EXTENSIONS = {".scad"}


def _validate_filepath(project_dir: Path, filepath: str) -> Path | None:
    """Validate file path: must be .scad, within project dir, no traversal."""
    resolved = safe_join_path(str(project_dir), filepath)
    if resolved is None:
        return None
    if resolved.suffix not in ALLOWED_EXTENSIONS:
        return None
    return resolved


@editor_bp.route("/api/projects/<slug>/files", methods=["GET"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
@require_project()
def list_files(slug, project_dir):

    files = []
    for p in project_dir.rglob("*.scad"):
        rel = p.relative_to(project_dir)
        # Skip hidden dirs, node_modules, .git
        if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
            continue
        files.append({
            "path": str(rel),
            "name": p.name,
            "size": p.stat().st_size,
        })

    return jsonify(sorted(files, key=lambda f: f["path"]))


@editor_bp.route("/api/projects/<slug>/files/<path:filepath>", methods=["GET"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
@require_project()
def read_file(slug, filepath, project_dir):

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path", 400)
    if not resolved.is_file():
        return error_response("File not found", 404)

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to read file: {e}", 500)

    return jsonify({"path": filepath, "content": content, "size": len(content)})


@editor_bp.route("/api/projects/<slug>/files/<path:filepath>", methods=["PUT"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_WRITE)
@require_project(auto_git=True)
def write_file(slug, filepath, project_dir):

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path", 400)
    if not resolved.is_file():
        return error_response("File not found", 404)

    data = request.json
    if not data or "content" not in data:
        return error_response("content is required", 400)

    content = data["content"]
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        return error_response(f"File exceeds maximum size of {MAX_FILE_SIZE // 1024}KB", 400)

    try:
        resolved.write_text(content, encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to write file: {e}", 500)

    return jsonify({"path": filepath, "size": len(content)})


@editor_bp.route("/api/projects/<slug>/files", methods=["POST"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_CREATE)
@require_project(auto_git=True)
def create_file(slug, project_dir):

    data = request.json
    if not data or "path" not in data:
        return error_response("path is required", 400)

    filepath = data["path"]
    content = data.get("content", "")

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path (must be .scad)", 400)
    if resolved.exists():
        return error_response("File already exists", 409)

    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        return error_response(f"File exceeds maximum size of {MAX_FILE_SIZE // 1024}KB", 400)

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to create file: {e}", 500)

    return jsonify({"path": filepath, "size": len(content)}), 201


@editor_bp.route("/api/projects/<slug>/files/<path:filepath>", methods=["DELETE"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_DELETE)
@require_project(auto_git=True)
def delete_file(slug, filepath, project_dir):

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path", 400)
    if not resolved.is_file():
        return error_response("File not found", 404)

    try:
        resolved.unlink()
    except OSError as e:
        return error_response(f"Failed to delete file: {e}", 500)

    return jsonify({"deleted": filepath})
