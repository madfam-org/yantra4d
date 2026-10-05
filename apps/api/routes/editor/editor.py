"""
Project source CRUD API — read/write/create/delete editable files in a project.

Handles OpenSCAD scripts and node-graph documents. A graph document is
validated against the transpiler's own rules before it is written, so the
editor cannot leave a cartridge in a state that fails at render time.
"""
import functools
import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

import rate_limits
from extensions import limiter
from middleware.auth import require_tier
from services.core.project_access import require_project_access
from utils.project_resolver import find_project_dir, require_project
from utils.route_helpers import error_response, safe_join_path
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

editor_bp = Blueprint("editor", __name__)

MAX_FILE_SIZE = 512 * 1024  # 512KB
# ``.graph.json`` is matched on the full suffix chain, not ``Path.suffix``
# (which would see only ``.json``), so an arbitrary ``.json`` stays rejected.
ALLOWED_EXTENSIONS = {".scad"}
GRAPH_SUFFIX = ".graph.json"


def _validate_filepath(project_dir: Path, filepath: str) -> Path | None:
    """Validate file path: must be .scad, within project dir, no traversal."""
    resolved = safe_join_path(str(project_dir), filepath)
    if resolved is None:
        return None
    if resolved.suffix not in ALLOWED_EXTENSIONS and not resolved.name.endswith(GRAPH_SUFFIX):
        return None
    return resolved


def _graph_rejection(resolved: Path, content: str) -> str | None:
    """Return why this graph document must not be saved, or None if it is fine.

    The transpiler is the authority: validating here means the editor reports a
    dangling input or a cycle immediately, instead of the author discovering it
    when a render fails.
    """
    if not resolved.name.endswith(GRAPH_SUFFIX):
        return None
    from services.engine.graph_engine import GraphError, transpile

    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        return f"That is not valid JSON: {exc}"
    try:
        transpile(document, {}, resolved.name)
    except GraphError as exc:
        return str(exc)
    return None


# ── Read-only commons cartridges ──────────────────────────────────────────────
#
# The API writes only into a cartridge it created for someone: a fork
# (POST /api/projects/<slug>/fork) or an imported repository
# (POST /api/github/import). Both record that in project.meta.json
# `source.type`. A built-in commons cartridge has no project.meta.json; it, and
# any cartridge whose source type is missing, unreadable or unknown, is
# read-only through the API — fork it to edit a copy. The Studio offers
# "Fork to edit" for exactly these; this is the same rule on the server.

#: `source.type` values whose cartridges the API may write.
WRITABLE_SOURCE_TYPES = frozenset({"fork", "github"})

#: Error code the Studio branches on. Stable API surface — do not rename.
READ_ONLY_ERROR_CODE = "read_only_cartridge"


def _project_source_type(project_dir: Path) -> str | None:
    """`source.type` from project.meta.json, or None when there is none."""
    meta_path = project_dir / "project.meta.json"
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    source = meta.get("source") if isinstance(meta, dict) else None
    kind = source.get("type") if isinstance(source, dict) else None
    return kind if isinstance(kind, str) else None


def read_only_cartridge_response(project_dir: Path):
    """403 `read_only_cartridge` unless the API may write this cartridge, else None."""
    if _project_source_type(project_dir) in WRITABLE_SOURCE_TYPES:
        return None
    return error_response(
        "This is a built-in cartridge and is read-only. Fork it to edit your own copy.",
        403, error_code=READ_ONLY_ERROR_CODE,
    )


def require_writable_cartridge(fn):
    """Decorator for every route that writes into an existing ``<slug>`` cartridge.

    Place it below ``require_project_access`` (privacy is settled first, so a
    private project still answers ``project_locked``) and above
    ``require_project(auto_git=True)`` (so nothing — not even the ``.git`` that
    auto_git creates — is written into a read-only cartridge). An unknown slug
    passes through to the route's own 404.
    """
    @functools.wraps(fn)
    def wrapper(*args, slug: str, **kwargs):
        project_dir = find_project_dir(slug)
        if project_dir is not None:
            refused = read_only_cartridge_response(project_dir)
            if refused is not None:
                return refused
        return fn(*args, slug=slug, **kwargs)
    return wrapper


@editor_bp.route("/api/projects/<slug>/files", methods=["GET"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
@require_project()
@require_project_access
def list_files(slug, project_dir):

    files = []
    for p in sorted([*project_dir.rglob("*.scad"), *project_dir.rglob(f"*{GRAPH_SUFFIX}")]):
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
@require_project_access
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
@require_project_access
@require_writable_cartridge
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

    rejection = _graph_rejection(resolved, content)
    if rejection:
        return error_response(rejection, 400)

    try:
        resolved.write_text(content, encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to write file: {e}", 500)

    return jsonify({"path": filepath, "size": len(content)})


@editor_bp.route("/api/projects/<slug>/files", methods=["POST"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_CREATE)
@require_project_access
@require_writable_cartridge
@require_project(auto_git=True)
def create_file(slug, project_dir):

    data = request.json
    if not data or "path" not in data:
        return error_response("path is required", 400)

    filepath = data["path"]
    content = data.get("content", "")

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path (must be .scad or .graph.json)", 400)
    if resolved.exists():
        return error_response("File already exists", 409)

    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        return error_response(f"File exceeds maximum size of {MAX_FILE_SIZE // 1024}KB", 400)

    rejection = _graph_rejection(resolved, content)
    if rejection:
        return error_response(rejection, 400)

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
@require_project_access
@require_writable_cartridge
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
