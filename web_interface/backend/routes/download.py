"""
Download Blueprint
Provides auth-gated endpoints for downloading STL and SCAD files.
"""
import logging

from flask import Blueprint, request, send_file, jsonify

from config import Config
from manifest import get_manifest
from middleware.auth import optional_auth
from services.route_helpers import safe_join_path

logger = logging.getLogger(__name__)

download_bp = Blueprint('download', __name__)


def _check_access(manifest_data, action: str, claims) -> tuple | None:
    """Check access_control for the given action. Returns error response tuple or None if allowed."""
    access_control = manifest_data.get("access_control", {})
    level = access_control.get(action, "public")

    if level == "authenticated" and claims is None:
        return jsonify({"error": "Authentication required", "action": action}), 401

    return None


@download_bp.route('/api/projects/<slug>/download/stl/<filename>', methods=['GET'])
@optional_auth
def download_stl(slug, filename):
    """Download an STL file for a project."""
    # Validate filename
    if '..' in filename or filename.startswith('/'):
        return jsonify({"error": "Invalid filename"}), 400

    try:
        m = get_manifest(slug)
    except Exception:
        return jsonify({"error": f"Project '{slug}' not found"}), 404

    # Check access control
    denied = _check_access(m._data, "download_stl", getattr(request, 'auth_claims', None))
    if denied:
        return denied

    # Try static dir first (rendered previews), then exports dir
    project_dir = Config.PROJECTS_DIR / slug
    for base_dir in [Config.STATIC_DIR, project_dir / "exports"]:
        safe_path = safe_join_path(str(base_dir), filename)
        if safe_path and safe_path.exists() and safe_path.suffix.lower() == '.stl':
            return send_file(safe_path, as_attachment=True, download_name=filename)

    return jsonify({"error": "File not found"}), 404


@download_bp.route('/api/projects/<slug>/download/scad/<filename>', methods=['GET'])
@optional_auth
def download_scad(slug, filename):
    """Download a SCAD source file for a project."""
    # Validate filename
    if '..' in filename or filename.startswith('/'):
        return jsonify({"error": "Invalid filename"}), 400

    try:
        m = get_manifest(slug)
    except Exception:
        return jsonify({"error": f"Project '{slug}' not found"}), 404

    denied = _check_access(m._data, "download_scad", getattr(request, 'auth_claims', None))
    if denied:
        return denied

    # Validate against manifest's allowed files whitelist
    allowed_files = m.get_allowed_files()
    if filename not in allowed_files:
        return jsonify({"error": "File not available for download"}), 403

    project_dir = Config.PROJECTS_DIR / slug
    safe_path = safe_join_path(str(project_dir), filename)
    if safe_path and safe_path.exists() and safe_path.suffix.lower() == '.scad':
        return send_file(safe_path, as_attachment=True, download_name=filename)

    return jsonify({"error": "File not found"}), 404
