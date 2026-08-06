"""
Materials Blueprint
Handles /api/materials endpoints for returning nanoscale properties.
"""
import logging

from flask import Blueprint, jsonify

from services.core.material_service import discover_materials, get_material
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)

materials_bp = Blueprint('materials', __name__)

@materials_bp.route('/api/materials', methods=['GET'])
def list_materials():
    """Return list of all available material hyperobjects."""
    try:
        materials = discover_materials()
        resp = jsonify(materials)
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp
    except Exception as e:
        logger.error(f"Failed to list materials: {e}")
        return error_response(str(e), 500)


@materials_bp.route('/api/materials/<slug>', methods=['GET'])
def get_material_by_slug(slug):
    """Return specific material manifest."""
    try:
        manifest = get_material(slug)
        resp = jsonify(manifest)
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp
    except RuntimeError as e:
        return error_response(str(e), 404)
