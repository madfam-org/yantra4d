"""
Project source CRUD API — read/write/create/delete editable files in a project.

Handles OpenSCAD scripts and node-graph documents. A graph document is
validated against the transpiler's own rules before it is written, so the
editor cannot leave a cartridge in a state that fails at render time.
"""
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

import rate_limits
from extensions import limiter
from middleware.auth import require_tier
from services.core.project_access import require_project_access
from utils.project_resolver import require_project
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


def _manifest_parameters(slug: str) -> list:
    """The cartridge's declared parameters, or [] if the manifest is unreadable.

    A graph's `{"param": id}` and `{"expr": "..."}` values name manifest
    parameters, so validating a save without them would reject every
    well-formed expression. A manifest that cannot be read degrades to [] —
    the render path validates against the real manifest regardless, so the
    editor is never the last line of defence.
    """
    try:
        from manifest import get_manifest

        return get_manifest(slug).parameters or []
    except Exception:  # a broken manifest must not block the editor
        logger.warning("Could not read parameters for %s while validating a graph", slug)
        return []


def _graph_rejection(resolved: Path, content: str, slug: str) -> str | None:
    """Return why this graph document must not be saved, or None if it is fine.

    The transpiler is the authority: validating here means the editor reports a
    dangling input, a cycle or a bad expression immediately, instead of the
    author discovering it when a render fails.
    """
    if not resolved.name.endswith(GRAPH_SUFFIX):
        return None
    import json

    from services.engine.graph_engine import (
        GraphError,
        extract_bindings,
        parameter_defaults,
        transpile,
    )

    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        return f"That is not valid JSON: {exc}"
    parameters = _manifest_parameters(slug)
    try:
        transpile(
            document,
            extract_bindings(parameters),
            resolved.name,
            parameter_defaults(parameters),
        )
    except GraphError as exc:
        return str(exc)
    return None


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
@require_project(auto_git=True)
@require_project_access
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

    rejection = _graph_rejection(resolved, content, slug)
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
@require_project(auto_git=True)
@require_project_access
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

    rejection = _graph_rejection(resolved, content, slug)
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
@require_project(auto_git=True)
@require_project_access
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
