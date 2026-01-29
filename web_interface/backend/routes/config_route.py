"""
Config Blueprint
Exposes dynamic configuration to the frontend.

Note: Most configuration is now served via /api/manifest (see manifest_route.py).
This endpoint is kept for backward compatibility.
"""
from flask import Blueprint, jsonify
from manifest import get_manifest

config_bp = Blueprint('config', __name__)


@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """Return dynamic configuration for the frontend."""
    manifest = get_manifest()
    return jsonify({
        "parts_map": manifest.get_parts_map(),
        "mode_map": manifest.get_mode_map(),
        "estimate_constants": manifest.estimate_constants,
    })
