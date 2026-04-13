"""
Simulate Blueprint
Provides foundational FEA stress simulation endpoints.
"""
import glob
import logging
import os

from flask import Blueprint, g, request, jsonify

from config import Config
from extensions import limiter
from middleware.auth import require_tier
from services.geometry.stress_analyzer import compute_stress_field
from utils.route_helpers import error_response, handle_exceptions
from utils.validators import require_valid_slug
import rate_limits

logger = logging.getLogger(__name__)

simulate_bp = Blueprint('simulate', __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)
_MESH_EXTENSIONS = (".glb", ".stl", ".3mf")

def _find_latest_render(slug: str) -> str | None:
    prefix = f"{slug}_{Config.STL_PREFIX}"
    candidates: list[str] = []

    for ext in _MESH_EXTENSIONS:
        pattern = os.path.join(STATIC_FOLDER, f"{prefix}*{ext}")
        candidates.extend(glob.glob(pattern))

    if not candidates:
        return None

    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]

@simulate_bp.route('/api/projects/<slug>/simulate/stress', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.ANALYSIS_THICKNESS)
@handle_exceptions
def simulate_stress(slug: str):
    """Run FEA Stress simulation overlay on latest render."""
    data = request.get_json(silent=True) or {}
    
    mesh_path = _find_latest_render(slug)
    if mesh_path is None:
        return error_response(f"No rendered mesh found for project '{slug}'.", 409)

    try:
        force_x = data.get("force_x", 0.0)
        force_y = data.get("force_y", -10.0)
        force_z = data.get("force_z", 0.0)
        
        result = compute_stress_field(mesh_path, force_vector=(force_x, force_y, force_z))
    except FileNotFoundError:
        return error_response("Render file disappeared during simulation", 404)
    except Exception as e:
        logger.exception("FEA simulation failed for %s", slug)
        return error_response(f"Simulation failed: {str(e)}", 500)

    return jsonify({
        "status": "success",
        "project": slug,
        "mesh_file": os.path.basename(mesh_path),
        "simulation": result,
    })
