"""
Config Blueprint
Exposes dynamic configuration to the frontend.

Note: Most configuration is now served via /api/manifest (see manifest_route.py).
This endpoint is kept for backward compatibility and is scheduled for removal.

Deprecation timeline:
  - Deprecated: 2026-03-06
  - Sunset: 2026-06-01
  - Successor: GET /api/manifest
"""
from flask import Blueprint, jsonify, make_response, request

from manifest import get_manifest
from services.core.project_access import check_project_access, is_private_project

config_bp = Blueprint('config', __name__)

@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """Return dynamic configuration for the frontend (deprecated)."""
    slug = request.args.get("project")
    if not slug:
        from config import Config
        if Config.MULTI_PROJECT:
            return jsonify({"error": "project query param required"}), 400

    # Deprecated or not, this is manifest content: same gate as /api/manifest.
    denied = check_project_access(slug)
    if denied is not None:
        return denied

    try:
        manifest = get_manifest(slug)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 404

    resp = make_response(jsonify({
        "parts_map": manifest.get_parts_map(),
        "mode_map": manifest.get_mode_map(),
        "estimate_constants": manifest.estimate_constants,
    }))
    if is_private_project(slug, manifest):
        resp.headers["Cache-Control"] = "private, no-store"
    resp.headers["Deprecation"] = "true"
    resp.headers["Sunset"] = "2026-06-01"
    resp.headers["Link"] = '</api/manifest>; rel="successor-version"'
    return resp
