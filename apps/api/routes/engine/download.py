"""
Download Blueprint
Provides auth-gated endpoints for downloading STL and SCAD files.
"""
import logging

from flask import Blueprint, Response, request, send_file

from manifest import get_manifest
from middleware.auth import (
    effective_tier,
    export_format_denied_response,
    optional_auth,
)
from services.core.project_access import check_project_access
from services.core.tier_service import export_format_allowed
from services.engine.render_orchestrator import ALLOWED_EXPORT_FORMATS
from services.storage.serving import send_artifact_download
from utils.project_resolver import find_project_dir
from utils.route_helpers import error_response, handle_exceptions, safe_join_path
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
    # Privacy outranks the per-action access_control below: a private project
    # is not downloadable at all, whatever its download_* levels say.
    denied = check_project_access(slug)
    if denied is not None:
        return denied

    normalized_format = file_format.lower().lstrip(".")
    if normalized_format == "scad":
        return download_scad(slug, filename)

    if normalized_format not in _ALLOWED_FORMATS:
        return error_response(f"Unsupported format: {file_format}", 400)

    if not filename.lower().endswith(f".{normalized_format}"):
        return error_response(f"Filename must end with .{normalized_format}", 400)

    # Early path-traversal check using safe_join_path against project dir
    project_dir = find_project_dir(slug)
    if project_dir is None:
        return error_response(f"Project '{slug}' not found", 404)
    if not safe_join_path(str(project_dir), filename):
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

    # Export-format tier gate, at RETRIEVAL as well as at generation.
    # Generation is gated in routes/engine/render.py, but rendered artifacts are
    # named `{prefix}{part}.{format}` / by a 10-character param hash and live for
    # the 24 h render-GC window, so a caller who learns (or guesses) a filename
    # could fetch a `step`/`glb` export their tier may not produce. `stl` stays
    # open because tiers.json lists it for guest. `scad` never reaches here — it
    # is source, not an export, and is gated by the manifest allowlist above.
    #
    # This runs before the store is consulted, so an object-storage artifact is
    # gated exactly as a file on disk is: the tier check is not something the
    # backend can move past.
    if not export_format_allowed(effective_tier(), normalized_format):
        return export_format_denied_response(normalized_format)

    # Rendered previews first, then the project's checked-in exports.
    #
    # Previews go through the artifact store, so this endpoint keeps working
    # once artifacts live in a bucket instead of on the pod's disk — and it
    # keeps *streaming* them rather than redirecting, so every access check
    # above (privacy, then access_control, then the tier gate) still runs on
    # every byte served. Handing out a bucket URL would skip all of them. Under
    # the default filesystem store this is the same safe_join_path + send_file
    # it always was.
    artifact = send_artifact_download(filename, normalized_format)
    if artifact is not None:
        return artifact

    # Exports are authored files committed alongside the cartridge, not render
    # output, so they stay on the project directory where they live.
    exports_dir = project_dir / "exports"
    safe_path = safe_join_path(str(exports_dir), filename)
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
    denied = check_project_access(slug)
    if denied is not None:
        return denied

    # Early path-traversal check using safe_join_path against project dir
    project_dir = find_project_dir(slug)
    if project_dir is None:
        return error_response(f"Project '{slug}' not found", 404)
    if not safe_join_path(str(project_dir), filename):
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

    safe_path = safe_join_path(str(project_dir), filename)
    if safe_path and safe_path.exists() and safe_path.suffix.lower() == '.scad':
        return send_file(safe_path, as_attachment=True, download_name=filename)

    return error_response("File not found", 404)
