"""
apps/api/routes/projects/animations.py

Animations Blueprint — parametric assembly animation rendering.

POST /api/projects/<slug>/animations/<animation_id>/render
  Renders N interpolated frames between from_state and to_state on the
  render worker and streams Server-Sent Events (SSE) with per-frame progress.
"""

import hashlib
import json
import logging
import os
import uuid

from flask import Blueprint, Response, jsonify, request

import rate_limits
from config import Config
from extensions import limiter
from manifest import get_manifest
from middleware.auth import optional_auth
from services.core.project_access import require_project_access
from services.core.tier_service import check_feature, resolve_tier
from services.engine.openscad import validate_params
from services.engine.render_contract import (
    RENDER_EVENT_JOB,
    RENDER_EVENT_PART_DONE,
    build_render_event,
)
from services.engine.render_orchestrator import (
    cancel_request,
    clear_request_cancel,
    is_render_worker_available,
    resolve_engine_config,
)
from services.engine.render_revision import cache_revision, render_revision
from services.engine.render_source import RenderSourceError, render_source_for_mode, source_content_hash
from services.engine.worker_dispatch import (
    WORKER_UNAVAILABLE,
    queue_worker_part,
    wait_worker_part,
)
from utils.route_helpers import error_response
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)
animations_bp = Blueprint("animations", __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)


def _ease(t: float, easing: str) -> float:
    """Apply easing function to a linear progress value t ∈ [0, 1]."""
    if easing == "ease-in":
        return t * t
    if easing == "ease-out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if easing == "ease-in-out":
        return t * t * (3.0 - 2.0 * t)  # smoothstep
    return t  # linear


def _interpolate_params(from_state: dict, to_state: dict, t: float) -> dict:
    """
    Interpolate between from_state and to_state at progress t ∈ [0, 1].

    - Numeric params: linearly interpolated
    - Boolean/string params: snap to to_state at t >= 0.5
    """
    result = {}
    all_keys = set(from_state) | set(to_state)
    for key in all_keys:
        from_val = from_state.get(key)
        to_val = to_state.get(key)

        if from_val is None:
            result[key] = to_val
        elif to_val is None:
            result[key] = from_val
        elif isinstance(from_val, (int, float)) and isinstance(to_val, (int, float)):
            result[key] = from_val + (to_val - from_val) * t
            # Preserve int type if both sides were ints
            if isinstance(from_val, int) and isinstance(to_val, int):
                result[key] = round(result[key])
        else:
            # Non-numeric: snap halfway
            result[key] = to_val if t >= 0.5 else from_val

    return result


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _frame_prefix(slug: str, animation_id: str, frame_idx: int, frame_params: dict,
                  scad_hash: str | None) -> str:
    """Artifact name prefix for one frame.

    Carries a digest of what the frame depends on (its parameters, the source
    and the renderer release), so two requests with different base parameters
    never write — or hand out a URL to — the same file.
    """
    identity = json.dumps({"p": frame_params, "source": scad_hash, "revision": cache_revision()},
                          sort_keys=True, default=str)
    digest = hashlib.sha256(identity.encode()).hexdigest()[:10]
    return f"anim_{slug}_{animation_id}_f{frame_idx:03d}_{digest}_"


@animations_bp.route("/api/projects/<slug>/animations/<animation_id>/render", methods=["POST"])
@require_valid_slug
@optional_auth
@limiter.limit(rate_limits.ANIMATION_RENDER)
@require_project_access
def render_animation(slug: str, animation_id: str):
    """
    Render all frames of a parametric animation defined in project.json.
    Returns an SSE stream of per-frame progress events, followed by a
    completion event with the full frames[] array of GLB URLs.

    Every frame part is a job on the render worker, the same queue and event
    channels `/api/render` uses; this handler interpolates the keyframes,
    queues the parts and relays progress. The stream opens with a `job` event
    carrying the `request_id` `POST /api/render-cancel` accepts.

    Requires 'pro' tier or above.
    """
    tier = resolve_tier(getattr(request, "auth_claims", None))
    if not check_feature(tier, "animation"):
        return error_response("Animation rendering requires Pro tier or above.", 403)

    try:
        manifest = get_manifest(slug)
    except RuntimeError as e:
        return error_response(str(e), 404)

    # Look up the animation definition in the manifest
    animations = manifest._data.get("animations", [])
    anim = next((a for a in animations if a["id"] == animation_id), None)
    if anim is None:
        return error_response(
            f"Animation '{animation_id}' not found in project '{slug}'.", 404
        )

    from_state = anim["from_state"]
    to_state = anim["to_state"]
    n_frames = anim.get("frames", 5)
    easing = anim.get("easing", "ease-in-out")
    mode_id = anim.get("mode") or manifest.modes[0]["id"]

    # Resolve render context: the mode's render source, as every render path
    # resolves it (services/engine/render_source.py).
    try:
        source = render_source_for_mode(manifest, mode_id)
    except RenderSourceError as exc:
        return error_response(str(exc), 400)
    parts = manifest.get_parts_for_mode(mode_id)
    if source is None:
        return error_response(f"Mode '{mode_id}' references an invalid SCAD file.", 400)
    scad_filename = source.filename
    if source.is_graph:
        scad_path = str(source.path)
    else:
        allowed = manifest.get_allowed_files()
        if scad_filename not in allowed:
            return error_response(f"Mode '{mode_id}' references an invalid SCAD file.", 400)
        scad_path = str(allowed[scad_filename])
    mode_map = manifest.get_mode_map()

    # Frames are served as GLB from an STL render, whatever the engine; the
    # engine and its tier gate resolve exactly as they do for /api/render.
    export_format = "stl"
    engine, scad_path, actual_format, engine_error = resolve_engine_config(
        {"mode": mode_id},
        {"project_slug": slug, "export_format": export_format, "scad_path": scad_path},
        tier,
    )
    if engine_error:
        return error_response(engine_error[0], engine_error[1])

    if not is_render_worker_available():
        return error_response(WORKER_UNAVAILABLE, 503, error_code="render_worker_unavailable")

    # Merge request-time base params (e.g., user's current slider state). They
    # are request input, so they pass the same validation /api/render applies;
    # the keyframes themselves come from the manifest.
    data = request.get_json(silent=True) or {}
    raw_base = data.get("parameters", {}) if isinstance(data, dict) else {}
    base_params = validate_params(raw_base, slug) if isinstance(raw_base, dict) and raw_base else {}

    request_id = data.get("request_id") if isinstance(data, dict) and isinstance(data.get("request_id"), str) else None
    request_id = request_id or str(uuid.uuid4())
    scad_hash = source_content_hash(scad_path, manifest)
    revision = render_revision()

    def generate():
        frames = []
        job_ids: list[str] = []
        finished = False
        clear_request_cancel(request_id)
        try:
            yield _sse(build_render_event(RENDER_EVENT_JOB, request_id=request_id, job_ids=[]))

            for frame_idx in range(n_frames):
                # t ∈ [0, 1] — linear position across frames
                t_linear = frame_idx / (n_frames - 1) if n_frames > 1 else 0.0
                t_eased = _ease(t_linear, easing)

                # Interpolate over animation states, then apply base_params as defaults
                anim_params = _interpolate_params(from_state, to_state, t_eased)
                frame_params = {**base_params, **anim_params}
                stl_prefix = _frame_prefix(slug, animation_id, frame_idx, frame_params, scad_hash)
                payload = {
                    "project_slug": slug,
                    "scad_filename": scad_filename,
                    "mode": mode_id,
                    "mode_map": mode_map,
                    "params": frame_params,
                    "stl_prefix": stl_prefix,
                    "export_format": export_format,
                    "request_id": request_id,
                    "render_revision": revision,
                    # A frame is not the render /api/render caches for its key.
                    "cache_write": False,
                }

                frame_glbs = []
                failure = None
                for part in parts:
                    if not is_render_worker_available():
                        failure = WORKER_UNAVAILABLE
                        break
                    queued = queue_worker_part(
                        payload, engine=engine, part=part, scad_path=scad_path,
                        output_path=os.path.join(STATIC_FOLDER, f"{stl_prefix}{part}.{actual_format}"),
                        export_format=export_format,
                    )
                    job_ids.append(queued.job_id)
                    yield _sse(build_render_event(RENDER_EVENT_JOB, request_id=request_id, job_ids=list(job_ids)))

                    result = wait_worker_part(queued)
                    if result.get("event") != RENDER_EVENT_PART_DONE:
                        failure = result.get("error") or result.get("message") or "Render failed"
                        break
                    # The viewer plays GLB: prefer the worker's GLB companion.
                    frame_glbs.append({
                        "part": part,
                        "url": result.get("viewer_url") or result.get("url"),
                    })

                if failure is not None:
                    yield _sse({"event": "error", "frame": frame_idx, "error": failure})
                    finished = True
                    return

                progress = round(((frame_idx + 1) / n_frames) * 100, 1)
                frames.append({
                    "frame_index": frame_idx,
                    "t_linear": round(t_linear, 4),
                    "t_eased": round(t_eased, 4),
                    "params": frame_params,
                    "parts": frame_glbs,
                })

                yield _sse({'event': 'frame_done', 'frame': frame_idx, 'progress': progress, 'total_frames': n_frames})

            yield _sse({'event': 'complete', 'frames': frames, 'progress': 100})
            finished = True
        finally:
            # A client that goes away mid-flipbook (the Studio's Cancel aborts
            # the fetch) must not leave its remaining frame parts on the queue.
            if not finished:
                cancel_request(request_id)

    return Response(generate(), mimetype="text/event-stream")


@animations_bp.route("/api/projects/<slug>/animations", methods=["GET"])
@require_valid_slug
@optional_auth
@require_project_access
def list_animations(slug: str):
    """Return the animations[] array from the project manifest."""
    tier = resolve_tier(getattr(request, "auth_claims", None))
    if not check_feature(tier, "animation"):
        return error_response("Animation features require Pro tier or above.", 403)

    try:
        manifest = get_manifest(slug)
    except RuntimeError as e:
        return error_response(str(e), 404)

    animations = manifest._data.get("animations", [])
    return jsonify({"animations": animations, "count": len(animations)})
