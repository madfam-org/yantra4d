"""
Render Blueprint
Handles /api/estimate, /api/render, /api/render-stream endpoints.

Route-level concerns only: request parsing, auth, rate limiting, and response
formatting. All render logic is delegated to the render orchestrator service.
"""
import logging

from flask import Blueprint, Response, jsonify, request

import rate_limits
from extensions import limiter
from manifest import get_manifest
from middleware.auth import optional_auth
from services.core.tier_service import (
    check_feature,
    get_render_limit,
    get_render_limit_for_project,
    resolve_tier,
)
from services.engine.render_orchestrator import (
    RenderPayloadError,
    cancel_all_renders,
    extract_render_payload,
    render_parts_stream,
    render_parts_sync,
    resolve_engine_config,
)
from utils.route_helpers import error_response, handle_exceptions, require_json_body

logger = logging.getLogger(__name__)

render_bp = Blueprint('render', __name__)


def _make_rate_limit_headers(tier: str) -> dict:
    """Build X-RateLimit-* headers for the response."""
    return {
        "X-RateLimit-Limit": str(get_render_limit(tier)),
        "X-RateLimit-Tier": tier,
        "X-RateLimit-Type": "backend",
    }


def _get_tiered_limit() -> str:
    """Return dynamic rate limit string based on user tier (backend renders only).

    Checks for per-project guest_render_limit override in the project manifest.
    """
    claims = getattr(request, "auth_claims", None)
    tier = resolve_tier(claims)
    manifest = None
    try:
        body = request.get_json(silent=True) or {}
        project_slug = body.get("project")
        if project_slug:
            manifest = get_manifest(project_slug)
    except Exception:
        pass
    return f"{get_render_limit_for_project(tier, manifest)}/hour"


def _rate_limit_key() -> str:
    """Return a per-user or per-IP rate limit bucket key."""
    claims = getattr(request, "auth_claims", None)
    if claims:
        return f"user:{claims.get('sub', '')}"
    return f"ip:{request.remote_addr}"


@render_bp.route('/api/estimate', methods=['POST'])
@optional_auth
@limiter.limit(rate_limits.ESTIMATE)
@require_json_body
def estimate_render_time():
    """Estimate render time based on parameters before actually rendering."""
    data = request.json
    project_slug = data.get('project')
    manifest = get_manifest(project_slug)
    mode_id = data.get('mode')
    scad_file = data.get('scad_file')

    # Resolve mode_id from scad_file for backward compat
    if not mode_id and scad_file:
        for m in manifest.modes:
            if m["scad_file"] == scad_file:
                mode_id = m["id"]
                break
    if not mode_id:
        mode_id = manifest.modes[0]["id"]

    num_units = manifest.calculate_estimate_units(mode_id, data)
    num_parts = len(manifest.get_parts_for_mode(mode_id))
    
    # Slicer-grade heuristic using theoretical volumetric flow
    volumetric_flow_rate = 8.0  # mm^3/s (typical FDM)
    material_density = 1.24     # g/cm^3 (PLA average)
    spool_cost = 25.00          # USD per kg
    
    theoretical_volume_mm3 = num_units * 0.20 
    theoretical_weight_g = (theoretical_volume_mm3 / 1000.0) * material_density
    path_time_seconds = (theoretical_volume_mm3 / volumetric_flow_rate) + (num_parts * 180.0)
    est_cost = (theoretical_weight_g / 1000.0) * spool_cost

    return jsonify({
        "estimated_seconds": round(path_time_seconds, 1),
        "estimated_weight_g": round(theoretical_weight_g, 2),
        "estimated_cost_usd": round(est_cost, 2),
        "num_parts": num_parts,
        "metrics": "slicer_grade_heuristic"
    })


@render_bp.route('/api/render', methods=['POST'])
@optional_auth
@limiter.limit(_get_tiered_limit, key_func=_rate_limit_key)
@require_json_body
@handle_exceptions
def render_stl():
    """Synchronous render endpoint."""
    data = request.json
    tier = resolve_tier(getattr(request, "auth_claims", None))
    payload = extract_render_payload(data)

    if isinstance(payload, RenderPayloadError):
        return error_response(payload.message, 400)

    if payload['export_format'] in {'step', 'gltf', 'glb', '3mf', 'obj', 'off'} and not check_feature(tier, "premium_export"):
        return error_response(f"Export format '{payload['export_format']}' requires Pro tier or above.", 403)

    # Resolve engine configuration
    engine, scad_path, actual_format, engine_error = resolve_engine_config(data, payload, tier)
    if engine_error:
        return error_response(engine_error[0], engine_error[1])

    try:
        generated_parts, log_or_error, cache_stats = render_parts_sync(
            data, payload, engine, scad_path, actual_format, tier,
        )
    except OSError as e:
        return error_response(str(e))

    if generated_parts is None:
        if log_or_error == "Render worker unavailable or not healthy":
            return error_response(
                log_or_error,
                503,
                error_code="render_worker_unavailable",
            )
        return error_response(log_or_error)

    cache_hits, cache_total = cache_stats
    resp = jsonify({
        "status": "success",
        "parts": generated_parts,
        "log": log_or_error,
    })
    for k, v in _make_rate_limit_headers(tier).items():
        resp.headers[k] = v
    resp.headers["X-Cache"] = "HIT" if (cache_total > 0 and cache_hits == cache_total) else "MISS"
    return resp


@render_bp.route('/api/render-stream', methods=['POST'])
@optional_auth
@limiter.limit(_get_tiered_limit, key_func=_rate_limit_key)
@require_json_body
def render_stl_stream():
    """Stream render progress via Server-Sent Events (SSE)."""
    data = request.json
    payload = extract_render_payload(data)

    if isinstance(payload, RenderPayloadError):
        return error_response(payload.message, 400)

    tier = resolve_tier(getattr(request, "auth_claims", None))
    if payload['export_format'] in {'step', 'gltf', 'glb', '3mf', 'obj', 'off'} and not check_feature(tier, "premium_export"):
        return error_response(f"Export format '{payload['export_format']}' requires Pro tier or above.", 403)

    # Resolve engine configuration
    engine, scad_path, actual_format, engine_error = resolve_engine_config(data, payload, tier)
    if engine_error:
        return error_response(engine_error[0], engine_error[1])

    return Response(
        render_parts_stream(data, payload, engine, scad_path, actual_format),
        mimetype='text/event-stream',
    )


@render_bp.route('/api/render-cancel', methods=['POST'])
@optional_auth
def cancel_render_endpoint():
    """Cancel the active render process."""
    cancelled = cancel_all_renders()
    return jsonify({
        "status": "cancelled" if cancelled else "no_active_render",
        "cancelled": cancelled,
    })
