"""
Analysis Blueprint
Provides geometry analysis endpoints (wall thickness, etc.) for rendered meshes.
"""
import glob
import logging
import os

from flask import Blueprint, g, request, jsonify

from config import Config
from extensions import limiter
from middleware.auth import require_tier
from services.geometry.thickness_analyzer import compute_wall_thickness
from services.geometry.overhang_analyzer import compute_overhang_angles
from utils.route_helpers import error_response, handle_exceptions
from utils.validators import require_valid_slug
import rate_limits

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)

# Supported mesh extensions in order of preference (GLB first since renders
# auto-convert STL to GLB for web delivery).
_MESH_EXTENSIONS = (".glb", ".stl", ".3mf")


def _find_latest_render(slug: str) -> str | None:
    """Locate the most recently modified render output for a project.

    Render files follow the naming convention:
        {slug}_preview_{hash}_{part}.{ext}
    stored in Config.STATIC_DIR.  We pick the newest file matching the
    project slug prefix across all supported mesh extensions.
    """
    prefix = f"{slug}_{Config.STL_PREFIX}"
    candidates: list[str] = []

    for ext in _MESH_EXTENSIONS:
        pattern = os.path.join(STATIC_FOLDER, f"{prefix}*{ext}")
        candidates.extend(glob.glob(pattern))

    if not candidates:
        return None

    # Return the most recently modified file.
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


@analysis_bp.route('/api/projects/<slug>/analyze/thickness', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.ANALYSIS_THICKNESS)
@handle_exceptions
def analyze_thickness(slug: str):
    """Run wall-thickness analysis on the latest render output for a project.

    Accepts optional JSON body:
        sample_count (int): number of surface samples (default 5000, max 50000)

    Returns JSON with thickness statistics, sample points, and thin-wall count.
    """
    data = request.get_json(silent=True) or {}

    sample_count = data.get("sample_count", 5000)
    if not isinstance(sample_count, int) or sample_count < 100:
        sample_count = 5000
    sample_count = min(sample_count, 50_000)

    mesh_path = _find_latest_render(slug)
    if mesh_path is None:
        return error_response(
            f"No rendered mesh found for project '{slug}'. Render first.",
            409,
        )

    try:
        result = compute_wall_thickness(mesh_path, sample_count=sample_count)
    except FileNotFoundError:
        return error_response("Render file disappeared during analysis", 404)
    except Exception as e:
        logger.exception(
            "Thickness analysis failed for %s [request_id=%s]: %s",
            slug, getattr(g, "request_id", None), e,
        )
        return error_response(f"Analysis failed: {str(e)}", 500)

    return jsonify({
        "status": "success",
        "project": slug,
        "mesh_file": os.path.basename(mesh_path),
        "analysis": result,
    })


@analysis_bp.route('/api/projects/<slug>/analyze/overhang', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.ANALYSIS_OVERHANG)
@handle_exceptions
def analyze_overhang(slug: str):
    """Run overhang angle analysis on the latest render output for a project.

    Accepts optional JSON body:
        sample_count (int): number of surface samples (default 5000, max 50000)
        threshold_deg (float): overhang angle threshold in degrees (default 45, range 20-80)

    Returns JSON with overhang statistics, sample points, and overhang count.
    """
    data = request.get_json(silent=True) or {}

    sample_count = data.get("sample_count", 5000)
    if not isinstance(sample_count, int) or sample_count < 100:
        sample_count = 5000
    sample_count = min(sample_count, 50_000)

    threshold_deg = data.get("threshold_deg", 45)
    if not isinstance(threshold_deg, (int, float)):
        threshold_deg = 45
    threshold_deg = max(20, min(80, float(threshold_deg)))

    mesh_path = _find_latest_render(slug)
    if mesh_path is None:
        return error_response(
            f"No rendered mesh found for project '{slug}'. Render first.",
            409,
        )

    try:
        result = compute_overhang_angles(
            mesh_path, sample_count=sample_count, threshold_deg=threshold_deg
        )
    except FileNotFoundError:
        return error_response("Render file disappeared during analysis", 404)
    except Exception as e:
        logger.exception(
            "Overhang analysis failed for %s [request_id=%s]: %s",
            slug, getattr(g, "request_id", None), e,
        )
        return error_response(f"Analysis failed: {str(e)}", 500)

    return jsonify({
        "status": "success",
        "project": slug,
        "mesh_file": os.path.basename(mesh_path),
        "analysis": result,
    })
