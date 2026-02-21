"""
SCAD File CRUD API — read/write/create/delete .scad files within a project.
"""
import logging
from pathlib import Path

from flask import Blueprint, request, jsonify

from config import Config
from extensions import limiter
import rate_limits
from middleware.auth import require_tier
from utils.route_helpers import error_response, safe_join_path
from services.editor.git_operations import git_init

logger = logging.getLogger(__name__)

editor_bp = Blueprint("editor", __name__)

MAX_FILE_SIZE = 512 * 1024  # 512KB
ALLOWED_EXTENSIONS = {".scad"}


def _get_project_dir(slug: str, auto_git: bool = False) -> Path | None:
    """Resolve and validate project directory. Optionally auto-init git."""
    project_dir = (Config.PROJECTS_DIR / slug).resolve()
    if not project_dir.is_relative_to(Config.PROJECTS_DIR.resolve()):
        return None
    if not project_dir.is_dir():
        return None
    if auto_git and not (project_dir / ".git").is_dir():
        git_init(project_dir)
    return project_dir


def _validate_filepath(project_dir: Path, filepath: str) -> Path | None:
    """Validate file path: must be .scad, within project dir, no traversal."""
    resolved = safe_join_path(str(project_dir), filepath)
    if resolved is None:
        return None
    if resolved.suffix not in ALLOWED_EXTENSIONS:
        return None
    return resolved


@editor_bp.route("/api/projects/<slug>/files", methods=["GET"])
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
def list_files(slug):
    """List .scad files in a project."""
    project_dir = _get_project_dir(slug)
    if not project_dir:
        return error_response("Project not found", 404)

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
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
def read_file(slug, filepath):
    """Read a .scad file's content."""
    project_dir = _get_project_dir(slug)
    if not project_dir:
        return error_response("Project not found", 404)

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
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_WRITE)
def write_file(slug, filepath):
    """Write content to a .scad file."""
    project_dir = _get_project_dir(slug, auto_git=True)
    if not project_dir:
        return error_response("Project not found", 404)

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
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_CREATE)
def create_file(slug):
    """Create a new .scad file."""
    project_dir = _get_project_dir(slug, auto_git=True)
    if not project_dir:
        return error_response("Project not found", 404)

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
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_DELETE)
def delete_file(slug, filepath):
    """Delete a .scad file."""
    project_dir = _get_project_dir(slug, auto_git=True)
    if not project_dir:
        return error_response("Project not found", 404)

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
