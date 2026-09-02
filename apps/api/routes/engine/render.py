"""
Render Blueprint
Handles /api/estimate, /api/render, /api/render-stream endpoints.

Route-level concerns only: request parsing, auth, rate limiting, and response
formatting. All render logic is delegated to the render orchestrator service.
"""
import json
import logging

from flask import Blueprint, Response, jsonify, request

import rate_limits
from extensions import limiter
from manifest import get_manifest
from middleware.auth import (
    effective_tier,
    export_format_denied_response,
    optional_auth,
    require_render_scope,
    require_role,
)
from services.core.project_access import check_project_access
from services.core.tier_service import (
    export_format_allowed,
    get_render_limit,
    get_render_limit_for_project,
    is_unlimited,
    resolve_tier,
)
from services.engine.render_orchestrator import (
    RenderPayloadError,
    cancel_all_renders,
    cancel_render_jobs,
    cancel_request,
    extract_render_payload,
    render_parts_stream,
    render_parts_sync,
    resolve_engine_config,
)
from utils.route_helpers import error_response, handle_exceptions, require_json_body

logger = logging.getLogger(__name__)

render_bp = Blueprint('render', __name__)


def _make_rate_limit_headers(tier: str) -> dict:
    """Build X-RateLimit-* headers for the response.

    An unlimited tier reports the word ``unlimited`` rather than ``-1``, which
    a client would parse as a number and count down from. Remaining/Reset are
    deliberately absent: flask-limiter emits those only for a limit it is
    actually tracking, and there is nothing to remain out of.
    """
    limit = get_render_limit(tier)
    return {
        "X-RateLimit-Limit": "unlimited" if is_unlimited(limit) else str(limit),
        "X-RateLimit-Tier": tier,
        "X-RateLimit-Type": "backend",
    }


def _effective_tier() -> str:
    """Gating tier for this request — see middleware.auth.effective_tier.

    Delegates so the render-time and retrieval-time export-format gates resolve
    a caller's tier through one implementation.
    """
    return effective_tier(resolve_tier)


def _project_render_limit() -> int:
    """Renders-per-hour for this request: the tier's, or the project's guest override."""
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
    return get_render_limit_for_project(tier, manifest)


def _get_tiered_limit() -> str:
    """Return dynamic rate limit string based on user tier (backend renders only).

    Checks for per-project guest_render_limit override in the project manifest.
    """
    limit = _project_render_limit()
    if is_unlimited(limit):
        return rate_limits.UNLIMITED_PLACEHOLDER
    return f"{limit}/hour"


def _render_limit_exempt() -> bool:
    """``exempt_when`` for the render limiters: True when this tier has no cap.

    flask-limiter parses a decorated limit string into a bucket *before* it
    consults ``exempt_when``, so "unlimited" cannot be expressed as "-1/hour" —
    the parse raises. Nor can the limit be dropped: a decorated limit is what
    suppresses the app-wide default ("500 per hour"), so returning nothing
    would silently cap an unlimited tier at the default instead. The supported
    pair is therefore a syntactically valid placeholder that is never enforced
    plus this predicate, which makes the limiter skip the bucket entirely.
    """
    return is_unlimited(_project_render_limit())


def _rate_limit_key() -> str:
    """Return a per-user or per-IP rate limit bucket key."""
    claims = getattr(request, "auth_claims", None)
    if claims:
        return f"user:{claims.get('sub', '')}"
    return f"ip:{request.remote_addr}"


@render_bp.route('/api/estimate', methods=['POST'])
@optional_auth
@require_render_scope
@limiter.limit(rate_limits.ESTIMATE)
@require_json_body
def estimate_render_time():
    """Estimate render time based on parameters before actually rendering."""
    data = request.json
    project_slug = data.get('project')

    # The estimate is computed from the manifest, so it answers the same gate
    # as the manifest itself.
    denied = check_project_access(project_slug)
    if denied is not None:
        return denied

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
@require_render_scope
@limiter.limit(_get_tiered_limit, key_func=_rate_limit_key, exempt_when=_render_limit_exempt)
@require_json_body
@handle_exceptions
def render_stl():
    """Synchronous render endpoint."""
    data = request.json
    denied = check_project_access(data.get("project"))
    if denied is not None:
        return denied
    tier = _effective_tier()
    payload = extract_render_payload(data)

    if isinstance(payload, RenderPayloadError):
        return error_response(payload.message, 400)

    # Gate on the tier's export_formats list — the same source the UI unlocks
    # buttons from — rather than the blanket premium_export boolean over a
    # hardcoded set, which 403'd formats the essentials tier advertises.
    export_format = payload['export_format']
    if not export_format_allowed(tier, export_format):
        return export_format_denied_response(export_format)

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
        # Echoed so a caller can correlate — and, when it supplied its own,
        # confirm the handle it can cancel with.
        "request_id": payload.get("request_id"),
    })
    for k, v in _make_rate_limit_headers(tier).items():
        resp.headers[k] = v
    resp.headers["X-Cache"] = "HIT" if (cache_total > 0 and cache_hits == cache_total) else "MISS"
    return resp


@render_bp.route('/api/render-stream', methods=['POST'])
@optional_auth
@require_render_scope
@limiter.limit(_get_tiered_limit, key_func=_rate_limit_key, exempt_when=_render_limit_exempt)
@require_json_body
def render_stl_stream():
    """Stream render progress via Server-Sent Events (SSE)."""
    data = request.json
    denied = check_project_access(data.get("project"))
    if denied is not None:
        return denied
    payload = extract_render_payload(data)

    if isinstance(payload, RenderPayloadError):
        return error_response(payload.message, 400)

    tier = _effective_tier()
    # Gate on the tier's export_formats list — the same source the UI unlocks
    # buttons from — rather than the blanket premium_export boolean over a
    # hardcoded set, which 403'd formats the essentials tier advertises.
    export_format = payload['export_format']
    if not export_format_allowed(tier, export_format):
        return export_format_denied_response(export_format)

    # Resolve engine configuration
    engine, scad_path, actual_format, engine_error = resolve_engine_config(data, payload, tier)
    if engine_error:
        return error_response(engine_error[0], engine_error[1])

    return Response(
        render_parts_stream(data, payload, engine, scad_path, actual_format),
        mimetype='text/event-stream',
    )


# Upper bound on a single cancel request. A stream issues one job per part and
# real modes render a handful; anything larger is a caller pushing work onto the
# queue sweep rather than cancelling its own render.
MAX_CANCEL_JOB_IDS = 64


@require_role("admin")
def _cancel_every_render():
    """`{"all": true}` — the operator escape hatch, behind the admin role.

    Renders carry no owner, and the backend runs a single replica, so cancelling
    "all" is cancelling every user's work. It was previously reachable by any
    anonymous caller with no body at all.
    """
    cancelled = cancel_all_renders()
    return jsonify({
        "status": "cancelled" if cancelled else "no_active_render",
        "cancelled": cancelled,
        "scope": "all",
    })


def _cancel_body() -> dict:
    """The cancel target, parsed from a normal request OR from a page-unload beacon.

    A browser abandoning a render — tab closed, back button, the Studio hook
    unmounting — has one reliable way to tell the server: `navigator.sendBeacon`,
    which the page does not stay alive to await. The Studio sends a JSON body
    that way (apps/studio/src/services/engine/renderService.ts::cancelRenderOnUnload)
    and falls back to `fetch(..., {keepalive: true})`.

    `request.get_json()` alone is not enough for that. A beacon's content type is
    whatever the Blob carries, and the fallback shape browsers accept without a
    CORS preflight is `text/plain` — so a body that is perfectly good JSON
    arrives under a content type Flask will not parse, `get_json(silent=True)`
    returns None, and the cancel becomes a 400 `cancel_target_required` for a
    render nobody is watching any more.

    Being tolerant here costs nothing: the body is still parsed as JSON and every
    field is still validated below. It only stops the content-type header from
    deciding whether a cancel counts.

    Nightly run #171 is why this matters: ~95 navigations in 40 minutes produced
    ZERO `render-cancel` calls, so every abandoned render ran to completion
    against a single worker while a live user waited behind it.
    """
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data

    raw = request.get_data(as_text=True) or ""
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@render_bp.route('/api/render-cancel', methods=['POST'])
@optional_auth
@require_render_scope
def cancel_render_endpoint():
    """Cancel the caller's own render, identified by `request_id` or `job_ids`.

    Both identifiers reach the client on its own `/api/render-stream` `job`
    event, so possessing one stands in for the render ownership the pipeline does
    not record. `job_id`s are server-minted UUID4s and unguessable; `request_id`
    is caller-suppliable, so a caller that sets a predictable one is choosing a
    predictable cancel handle (see docs/AUTH.md).
    """
    data = _cancel_body()

    # Cancellation is a write against a project's in-flight work, so it is
    # gated like the renders it stops (#78). The slug is optional here; an
    # absent one leaves the scoped behaviour untouched.
    denied = check_project_access(data.get("project"))
    if denied is not None:
        return denied

    if data.get("all") is True:
        return _cancel_every_render()

    request_id = data.get("request_id")
    raw_job_ids = data.get("job_ids")

    if raw_job_ids is not None:
        if not isinstance(raw_job_ids, list):
            return error_response(
                "'job_ids' must be a list of job id strings.",
                400,
                error_code="cancel_target_invalid",
            )
        if len(raw_job_ids) > MAX_CANCEL_JOB_IDS:
            return error_response(
                f"'job_ids' accepts at most {MAX_CANCEL_JOB_IDS} ids per request.",
                400,
                error_code="cancel_target_invalid",
            )
        if any(not isinstance(job_id, str) or not job_id.strip() for job_id in raw_job_ids):
            return error_response(
                "'job_ids' must contain non-empty strings.",
                400,
                error_code="cancel_target_invalid",
            )

    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip()):
        return error_response(
            "'request_id' must be a non-empty string.",
            400,
            error_code="cancel_target_invalid",
        )

    job_ids = [job_id.strip() for job_id in (raw_job_ids or [])]
    request_id = request_id.strip() if isinstance(request_id, str) else None

    if not request_id and not job_ids:
        return error_response(
            "Cancelling requires a target: send {\"request_id\": \"...\"} or "
            "{\"job_ids\": [...]} from the render's `job` stream event. "
            "Admins may send {\"all\": true} to cancel every render.",
            400,
            error_code="cancel_target_required",
        )

    cancelled_jobs: list[str] = []
    if request_id:
        cancelled_jobs.extend(cancel_request(request_id))
    if job_ids:
        already = set(cancelled_jobs)
        cancelled_jobs.extend(
            job_id for job_id in cancel_render_jobs(job_ids) if job_id not in already
        )

    # A `request_id` cancel with nothing queued yet is still a real cancel: the
    # flag stops the parts the render loop has not reached. Saying
    # "no_active_render" there would invite the client to retry a cancel that
    # already took.
    cancelled = bool(cancelled_jobs) or bool(request_id)
    return jsonify({
        "status": "cancelled" if cancelled else "no_active_render",
        "cancelled": cancelled,
        "cancelled_jobs": cancelled_jobs,
        "request_id": request_id,
    })
