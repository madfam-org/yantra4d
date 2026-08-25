"""
apps/api/routes/projects/animations.py

Animations Blueprint — parametric assembly animation rendering.

POST /api/projects/<slug>/animations/<animation_id>/render
  Renders N interpolated GLB frames between from_state and to_state.
  Streams Server-Sent Events (SSE) with per-frame progress.
"""

import json
import logging
import os

from flask import Blueprint, Response, jsonify, request

import rate_limits
from config import Config
from extensions import limiter
from manifest import get_manifest
from middleware.auth import optional_auth
from services.core.implicit_engine import run_render as run_implicit_render
from services.core.tier_service import check_feature, resolve_tier
from services.engine.cadquery_engine import (
    build_cadquery_command,
)
from services.engine.cadquery_engine import (
    run_render as run_cadquery_render,
)
from services.engine.format_converter import stl_to_glb
from services.engine.openscad import (
    build_openscad_command,
)
from services.engine.openscad import (
    run_render as run_openscad_render,
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


def _render_frame(engine: str, manifest, output_path: str, params: dict,
                  part: str, mode_map: dict, scad_path: str) -> tuple[bool, str]:
    """Dispatch a single-frame render to the correct engine."""
    if engine == "cadquery":
        cmd = build_cadquery_command(output_path, scad_path, params, "glb")
        return run_cadquery_render(cmd, scad_path=scad_path)
    elif engine == "implicit":
        config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
        return run_implicit_render(output_path, config, params)
    else:
        render_mode = mode_map.get(part, 0)
        cmd = build_openscad_command(output_path, scad_path, params, render_mode)
        return run_openscad_render(cmd, scad_path=scad_path)


@animations_bp.route("/api/projects/<slug>/animations/<animation_id>/render", methods=["POST"])
@require_valid_slug
@optional_auth
@limiter.limit(rate_limits.ANIMATION_RENDER)
def render_animation(slug: str, animation_id: str):
    """
    Render all frames of a parametric animation defined in project.json.
    Returns an SSE stream of per-frame progress events, followed by a
    completion event with the full frames[] array of GLB URLs.

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

    # Resolve render context
    scad_filename = manifest.get_scad_file_for_mode(mode_id)
    parts = manifest.get_parts_for_mode(mode_id)
    allowed = manifest.get_allowed_files()
    if scad_filename not in allowed:
        return error_response(f"Mode '{mode_id}' references an invalid SCAD file.", 400)

    scad_path = str(allowed[scad_filename])
    mode_map = manifest.get_mode_map()
    engine = manifest.mode_engine(mode_id)

    # Merge request-time base params (e.g., user's current slider state)
    data = request.get_json(silent=True) or {}
    base_params = data.get("parameters", {})

    def generate():
        frames = []

        for frame_idx in range(n_frames):
            # t ∈ [0, 1] — linear position across frames
            t_linear = frame_idx / (n_frames - 1) if n_frames > 1 else 0.0
            t_eased = _ease(t_linear, easing)

            # Interpolate over animation states, then apply base_params as defaults
            anim_params = _interpolate_params(from_state, to_state, t_eased)
            frame_params = {**base_params, **anim_params}

            frame_glbs = []
            frame_ok = True
            frame_stderr = ""

            for part in parts:
                output_filename = f"anim_{slug}_{animation_id}_f{frame_idx:03d}_{part}.stl"
                output_path = os.path.join(STATIC_FOLDER, output_filename)

                success, stderr = _render_frame(
                    engine, manifest, output_path, frame_params, part, mode_map, scad_path
                )
                frame_stderr += stderr

                if not success:
                    frame_ok = False
                    break

                # Convert STL → GLB
                glb_filename = output_filename.replace(".stl", ".glb")
                glb_path = os.path.join(STATIC_FOLDER, glb_filename)
                if stl_to_glb(output_path, glb_path):
                    serve_filename = glb_filename
                else:
                    serve_filename = output_filename

                frame_glbs.append({
                    "part": part,
                    "url": f"/static/{serve_filename}",
                })

            progress = round(((frame_idx + 1) / n_frames) * 100, 1)

            if not frame_ok:
                yield f"data: {json.dumps({'event': 'error', 'frame': frame_idx, 'error': frame_stderr})}\n\n"
                return

            frame_entry = {
                "frame_index": frame_idx,
                "t_linear": round(t_linear, 4),
                "t_eased": round(t_eased, 4),
                "params": frame_params,
                "parts": frame_glbs,
            }
            frames.append(frame_entry)

            yield f"data: {json.dumps({'event': 'frame_done', 'frame': frame_idx, 'progress': progress, 'total_frames': n_frames})}\n\n"

        yield f"data: {json.dumps({'event': 'complete', 'frames': frames, 'progress': 100})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@animations_bp.route("/api/projects/<slug>/animations", methods=["GET"])
@require_valid_slug
@optional_auth
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
