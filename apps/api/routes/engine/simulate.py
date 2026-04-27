"""
Simulate Blueprint
Provides foundational FEA stress simulation endpoints.
"""
import glob
import logging
import os

from flask import Blueprint, request, jsonify

from config import Config
from extensions import limiter
from middleware.auth import require_tier
from services.geometry.stress_analyzer import compute_stress_field
from tasks.simulation_tasks import queue_simulation, get_job_status
from tasks.optimization_tasks import queue_optimization, get_opt_status
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

@simulate_bp.route('/api/projects/<slug>/simulate/physics', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@handle_exceptions
def start_physics_simulation(slug: str):
    """Trigges a full GPU-bound PPF Physics simulation returning sequence frames."""
    data = request.get_json(silent=True) or {}
    
    parts = data.get("parts", [])
    kinematics = data.get("kinematics", {})
    
    if not parts or not kinematics:
        return error_response("Missing parts or kinematics manifest payload.", 400)
        
    try:
        # Dispatch the simulation job to GPU worker queue
        job_id = queue_simulation(slug, parts, kinematics)
    except Exception as e:
        logger.exception("Failed to dispatch simulation job")
        return error_response(f"Job dispatch failed: {str(e)}", 500)
        
    return jsonify({
        "status": "success",
        "message": "Physics simulation queued.",
        "job_id": job_id
    }), 202

@simulate_bp.route('/api/projects/<slug>/simulate/physics/<job_id>', methods=['GET'])
@require_valid_slug
@handle_exceptions
def get_physics_simulation_status(slug: str, job_id: str):
    """Polls the status of the asynchronous physics simulation task."""
    status_data = get_job_status(job_id)
    
    if not status_data:
        return error_response("Job not found.", 404)
        
    if status_data.get("slug") != slug:
        return error_response("Job does not belong to this project.", 403)
        
    return jsonify({
        "status": status_data["status"],
        "progress": status_data["progress"],
        "frames": status_data["frames"],
        "error": status_data["error"]
    })

@simulate_bp.route('/api/projects/<slug>/simulate/optimize', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@handle_exceptions
def start_optimization(slug: str):
    """Trigges a generative topology optimization task."""
    data = request.get_json(silent=True) or {}
    original_params = data.get("params", {})
    
    if not original_params:
        return error_response("Missing base parameters for optimization constraint.", 400)
    
    try:
        job_id = queue_optimization(slug, original_params)
    except Exception as e:
        logger.exception("Failed to dispatch topology optimizer")
        return error_response(f"Job dispatch failed: {str(e)}", 500)
        
    return jsonify({
        "status": "success",
        "job_id": job_id
    }), 202

@simulate_bp.route('/api/projects/<slug>/simulate/optimize/<job_id>', methods=['GET'])
@require_valid_slug
@handle_exceptions
def get_optimization_status(slug: str, job_id: str):
    """Polls the multi-generation optimization track."""
    status_data = get_opt_status(job_id)
    
    if not status_data:
        return error_response("Optimization job not found.", 404)
        
    if status_data.get("slug") != slug:
        return error_response("Optimization job does not belong to this project.", 403)
        
    return jsonify({
        "status": status_data["status"],
        "progress": status_data["progress"],
        "best_params": status_data["best_params"],
        "logs": status_data["logs"],
        "error": status_data["error"]
    })
