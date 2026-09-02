"""
Analysis Blueprint
Provides geometry analysis endpoints (wall thickness, etc.) for rendered meshes.
"""
import logging

from flask import Blueprint, g, jsonify, request

import rate_limits
from extensions import limiter
from middleware.auth import require_tier
from services.core.project_access import require_project_access
from services.engine.render_artifacts import find_latest_render_key
from services.geometry.overhang_analyzer import compute_overhang_angles
from services.geometry.thickness_analyzer import compute_wall_thickness
from services.storage import local_artifact
from utils.route_helpers import error_response, handle_exceptions
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)

#: Refused when the project has never been rendered on this deployment.
_NOT_RENDERED = "No rendered mesh found for project '%s'. Render first."


@analysis_bp.route('/api/projects/<slug>/analyze/thickness', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.ANALYSIS_THICKNESS)
@handle_exceptions
@require_project_access
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

    # trimesh loads a file, so the artifact has to become one. Under the
    # filesystem store that is the artifact's own path and nothing is copied;
    # under an object store it is a temporary download, removed on the way out.
    mesh_key = find_latest_render_key(slug)
    if mesh_key is None:
        return error_response(_NOT_RENDERED % slug, 409)

    try:
        with local_artifact(mesh_key) as mesh_path:
            if mesh_path is None:
                return error_response(_NOT_RENDERED % slug, 409)
            result = compute_wall_thickness(str(mesh_path), sample_count=sample_count)
    except FileNotFoundError:
        return error_response("Render file disappeared during analysis", 404)
    except Exception as e:
        logger.exception(
            "Thickness analysis failed for %s [request_id=%s]",
            slug, getattr(g, "request_id", None),
        )
        return error_response(f"Analysis failed: {e!s}", 500)

    return jsonify({
        "status": "success",
        "project": slug,
        "mesh_file": mesh_key.rsplit("/", 1)[-1],
        "analysis": result,
    })


@analysis_bp.route('/api/projects/<slug>/analyze/overhang', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.ANALYSIS_OVERHANG)
@handle_exceptions
@require_project_access
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

    mesh_key = find_latest_render_key(slug)
    if mesh_key is None:
        return error_response(_NOT_RENDERED % slug, 409)

    try:
        with local_artifact(mesh_key) as mesh_path:
            if mesh_path is None:
                return error_response(_NOT_RENDERED % slug, 409)
            result = compute_overhang_angles(
                str(mesh_path), sample_count=sample_count, threshold_deg=threshold_deg
            )
    except FileNotFoundError:
        return error_response("Render file disappeared during analysis", 404)
    except Exception as e:
        logger.exception(
            "Overhang analysis failed for %s [request_id=%s]",
            slug, getattr(g, "request_id", None),
        )
        return error_response(f"Analysis failed: {e!s}", 500)

    return jsonify({
        "status": "success",
        "project": slug,
        "mesh_file": mesh_key.rsplit("/", 1)[-1],
        "analysis": result,
    })
