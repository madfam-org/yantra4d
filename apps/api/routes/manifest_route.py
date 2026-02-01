"""
Manifest Blueprint
Serves GET /api/manifest — the project manifest as JSON.
"""
from flask import Blueprint, jsonify
from manifest import get_manifest

manifest_bp = Blueprint('manifest', __name__)


@manifest_bp.route('/api/manifest', methods=['GET'])
def serve_manifest():
    """Return the full project manifest."""
    return jsonify(get_manifest().as_json())
