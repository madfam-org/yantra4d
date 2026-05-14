"""
Download Blueprint
Provides auth-gated endpoints for downloading STL and SCAD files.
"""
import logging

from flask import Blueprint, request, send_file, Response

from config import Config
from services.engine.render_orchestrator import ALLOWED_EXPORT_FORMATS
from manifest import get_manifest
from middleware.auth import optional_auth
from utils.route_helpers import safe_join_path, error_response, handle_exceptions
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

download_bp = Blueprint('download', __name__)
_ALLOWED_FORMATS = {fmt.lower() for fmt in ALLOWED_EXPORT_FORMATS} | {"stl", "scad"}
_ALLOWED_FORMATS.add("off")


def _check_access(manifest_data, action: str, claims) -> tuple | None:
    """Check access_control for the given action. Returns error response tuple or None if allowed."""
    access_control = manifest_data.get("access_control", {})
    level = access_control.get(action, "public")

    if level == "authenticated" and claims is None:
        return error_response("Authentication required", 401)

    return None


def _download_render_file(slug: str, filename: str, file_format: str, claims) -> Response | tuple[Response, int]:
    """Download a render artifact by file format and filename."""
    normalized_format = file_format.lower().lstrip(".")
    if normalized_format == "scad":
        return download_scad(slug, filename)

    if normalized_format not in _ALLOWED_FORMATS:
        return error_response(f"Unsupported format: {file_format}", 400)

    if not filename.lower().endswith(f".{normalized_format}"):
        return error_response(f"Filename must end with .{normalized_format}", 400)

    # Early path-traversal check using safe_join_path against project dir
    if not safe_join_path(str(Config.PROJECTS_DIR / slug), filename):
        return error_response("Invalid filename", 400)

    try:
        m = get_manifest(slug)
    except Exception:
        return error_response(f"Project '{slug}' not found", 404)

    # Check access control; keep backward compatibility with `download_stl`.
    access_control = m._data.get("access_control", {})
    format_action = f"download_{normalized_format}"
    if format_action in access_control:
        denied = _check_access(m._data, format_action, claims)
    elif "download" in access_control:
        denied = _check_access(m._data, "download", claims)
    else:
        denied = _check_access(m._data, "download_stl", claims)
    if denied:
        return denied

    # Try static dir first (rendered previews), then exports dir
    project_dir = Config.PROJECTS_DIR / slug
    for base_dir in [Config.STATIC_DIR, project_dir / "exports"]:
        safe_path = safe_join_path(str(base_dir), filename)
        if safe_path and safe_path.exists() and safe_path.suffix.lower() == f".{normalized_format}":
            return send_file(safe_path, as_attachment=True, download_name=filename)

    return error_response("File not found", 404)


@download_bp.route('/api/projects/<slug>/download/stl/<filename>', methods=['GET'])
@require_valid_slug
@optional_auth
@handle_exceptions
def download_stl(slug: str, filename: str) -> Response | tuple[Response, int]:
    """Backward-compatible STL download endpoint."""
    return _download_render_file(slug, filename, "stl", getattr(request, "auth_claims", None))


@download_bp.route('/api/projects/<slug>/download/<file_format>/<filename>', methods=['GET'])
@require_valid_slug
@optional_auth
@handle_exceptions
def download_by_format(slug: str, file_format: str, filename: str) -> Response | tuple[Response, int]:
    """Download a rendered artifact in a requested geometry format."""
    return _download_render_file(slug, filename, file_format, getattr(request, "auth_claims", None))


@download_bp.route('/api/projects/<slug>/download/scad/<filename>', methods=['GET'])
@require_valid_slug
@optional_auth
@handle_exceptions
def download_scad(slug: str, filename: str) -> Response | tuple[Response, int]:
    """Download a SCAD source file for a project."""
    # Early path-traversal check using safe_join_path against project dir
    if not safe_join_path(str(Config.PROJECTS_DIR / slug), filename):
        return error_response("Invalid filename", 400)

    try:
        m = get_manifest(slug)
    except Exception:
        return error_response(f"Project '{slug}' not found", 404)

    denied = _check_access(m._data, "download_scad", getattr(request, 'auth_claims', None))
    if denied:
        return denied

    # Validate against manifest's allowed files whitelist
    allowed_files = m.get_allowed_files()
    if filename not in allowed_files:
        return error_response("File not available for download", 403)

    project_dir = Config.PROJECTS_DIR / slug
    safe_path = safe_join_path(str(project_dir), filename)
    if safe_path and safe_path.exists() and safe_path.suffix.lower() == '.scad':
        return send_file(safe_path, as_attachment=True, download_name=filename)

    return error_response("File not found", 404)
