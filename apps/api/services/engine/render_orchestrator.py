"""
Render Orchestrator Service
Centralizes engine selection, format validation, render execution, caching,
and post-render conversions. Eliminates duplication between sync/stream paths.
"""
import json
import logging
import os
import time
import uuid

import redis

from config import Config
from manifest import get_manifest
from services.engine.format_converter import convert_mesh, stl_to_glb
from services.engine.openscad import compute_scad_hash, validate_params
from services.engine.render_cache import render_cache
from services.engine.render_contract import (
    RENDER_EVENT_CANCELLED,
    RENDER_EVENT_COMPLETE,
    RENDER_EVENT_ERROR,
    RENDER_EVENT_JOB,
    RENDER_EVENT_PART_DONE,
    RENDER_STREAM_SCHEMA_VERSION,
    build_render_event,
    is_terminal_render_event,
    render_channel_for_job,
    render_final_channel_for_job,
)

r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

ALLOWED_EXPORT_FORMATS = {'stl', '3mf', 'off', 'step', 'gltf', 'glb', 'obj'}
TRIMESH_CONVERTIBLE = {'obj', 'ply', 'glb', 'gltf', '3mf', 'off'}
PROGRESS_TOTAL = 100
RENDER_QUEUE = "yantra_render_queue"
ACTIVE_RENDER_JOBS_KEY = "yantra_render_active_jobs"
ACTIVE_RENDER_META_PREFIX = "yantra_render_job_meta:"
CANCEL_ALL_KEY = "yantra_render_cancel_all"
CANCEL_JOB_PREFIX = "yantra_render_cancel_job:"
# Request-scoped cancel flag. A multi-part render enqueues one job per part
# *sequentially* — part i+1 is not queued until part i finishes — so marking the
# job_ids issued so far cannot stop the parts that have not been queued yet.
# This flag is what closes that gap: the render loop checks it before enqueuing
# each part and stops the whole request. It is also what `cancel_all_renders()`
# used CANCEL_ALL_KEY for, minus the blast radius.
CANCEL_REQUEST_PREFIX = "yantra_render_cancel_request:"
CANCEL_TTL_SECONDS = 120
ACTIVE_JOB_META_TTL = 300
CANCEL_EVENT_TTL_SECONDS = 30
RENDER_WORKER_HEARTBEAT_KEY = os.environ.get(
    "RENDER_WORKER_HEARTBEAT_KEY",
    "yantra_render_worker_heartbeat",
)
RENDER_WORKER_HEARTBEAT_TTL_SECONDS = int(os.environ.get(
    "RENDER_WORKER_HEARTBEAT_TTL_SECONDS",
    "60",
))

logger = logging.getLogger(__name__)

STATIC_FOLDER = str(Config.STATIC_DIR)

# Per-part SSE deadline. Env-tunable, default raised 120 -> 180: cold
# made-to-measure body lofts legitimately run 30-90s per part, and shared-runner
# contention pushes multi-part cold renders uncomfortably close to the old 120s
# figure. The subprocess ceiling RENDER_TIMEOUT_S (services/engine/render_engine.py,
# default 300) still bounds the actual render, so this only widens the window in
# which the stream is willing to wait for a legitimately slow part.
RENDER_STREAM_PART_TIMEOUT_SECONDS = int(os.getenv('RENDER_STREAM_PART_TIMEOUT_SECONDS', '180'))
RENDER_PART_WAIT_TIMEOUT_SECONDS = 120

# When truthy, payload shapes that deviate from the documented contract
# ({mode, parameters, parts, export_format?, project?}) are rejected with a 400
# instead of being silently tolerated. Default off so legacy callers keep
# working; flip on after fleet observation of the deprecation warnings below.
def _strict_payload_enabled() -> bool:
    """Read RENDER_STRICT_PAYLOAD at call time so tests/env changes take effect."""
    return os.getenv('RENDER_STRICT_PAYLOAD', '').strip().lower() in ('1', 'true', 'yes', 'on')


# ──────────────────────────────────────────────
# Payload Resolution
# ──────────────────────────────────────────────

class RenderPayloadError:
    """Structured error from payload resolution."""

    def __init__(self, message: str, bad_name: str | None = None):
        self.message = message
        self.bad_name = bad_name


def _request_origin() -> str:
    """Best-effort description of the caller (route + remote addr) for deprecation logs.

    Safe to call outside a Flask request context (unit tests, worker paths).
    """
    try:
        from flask import has_request_context, request
        if not has_request_context():
            return "no-request-context"
        return f"{request.method} {request.path} from {request.remote_addr}"
    except Exception:
        return "unknown"


def resolve_render_context(data: dict):
    """Resolve scad_file, parts, and mode_map from request payload.

    Returns (scad_filename, scad_path, parts, mode_map, static_stl_map, mode_id)
    or RenderPayloadError on failure.
    """
    project_slug = data.get('project')
    manifest = get_manifest(project_slug)
    mode_id = data.get('mode')
    scad_filename = data.get('scad_file')

    if mode_id:
        scad_filename = manifest.get_scad_file_for_mode(mode_id)
        if scad_filename is None:
            return RenderPayloadError(f"Invalid mode id: {mode_id}", bad_name=mode_id)
        parts = manifest.get_parts_for_mode(mode_id)
    else:
        if scad_filename:
            logger.warning("Deprecated: 'scad_file' parameter used instead of 'mode'. Update client to use 'mode'.")
            mode_id = "legacy"
        else:
            # No 'mode' in the payload. The documented contract requires one; we
            # silently fall through to modes[0] and return HTTP 200, which has
            # masked client bugs (wrong geometry rendered, never surfaced).
            fallback_mode = manifest.modes[0]["id"]
            if _strict_payload_enabled():
                return RenderPayloadError(
                    "Missing required 'mode' in render payload. The documented "
                    "contract is {mode, parameters, parts, export_format?, project?}. "
                    f"Refusing to silently render the first manifest mode "
                    f"('{fallback_mode}') under RENDER_STRICT_PAYLOAD."
                )
            logger.warning(
                "Deprecated render payload: no 'mode' supplied; silently rendering "
                "first manifest mode '%s'. project=%s origin=%s. "
                "Send an explicit 'mode' — this will 400 once RENDER_STRICT_PAYLOAD is on.",
                fallback_mode,
                project_slug or "<default>",
                _request_origin(),
            )
            mode_id = fallback_mode
            scad_filename = manifest.modes[0]["scad_file"]
        parts_map = manifest.get_parts_map()
        parts = parts_map.get(scad_filename, manifest.modes[0]["parts"])

    allowed = manifest.get_allowed_files()
    if scad_filename not in allowed:
        return RenderPayloadError(f"Invalid SCAD file: {scad_filename}", bad_name=scad_filename)

    scad_path = str(allowed[scad_filename])
    mode_map = manifest.get_mode_map()
    static_stl_map = manifest.get_static_stl_map()
    return scad_filename, scad_path, parts, mode_map, static_stl_map, mode_id


def extract_render_payload(data: dict) -> dict | RenderPayloadError:
    """Extract and validate all render payload fields from request data.

    Returns a dict of render parameters on success, or RenderPayloadError on failure.
    """
    import hashlib

    result = resolve_render_context(data)
    if isinstance(result, RenderPayloadError):
        return result

    scad_filename, scad_path, parts_to_render, mode_map, static_stl_map, mode_id = result

    project_slug = data.get('project', '')
    export_format = data.get('export_format', 'stl')
    if export_format not in ALLOWED_EXPORT_FORMATS:
        export_format = 'stl'

    # Documented contract nests render parameters under 'parameters'. A flattened
    # payload (params spread at the top level) silently "works" but produces a
    # different param_hash — and therefore a different cache key — than the same
    # parameters sent nested, and loses fields only read from the nested form
    # (e.g. target_material below). That divergence cost an 8-layer cross-service
    # debug chain on 2026-08-22.
    raw_params = data.get('parameters')
    if raw_params is None:
        if _strict_payload_enabled():
            return RenderPayloadError(
                "Missing required 'parameters' object in render payload. The "
                "documented contract is {mode, parameters, parts, export_format?, "
                "project?} with render parameters NESTED under 'parameters'. "
                "Refusing the flattened top-level form under RENDER_STRICT_PAYLOAD."
            )
        logger.warning(
            "Deprecated render payload: no 'parameters' key; treating the whole "
            "request body as the parameter map. project=%s mode=%s origin=%s. "
            "This yields a different param_hash (cache key) than the nested form "
            "and drops 'target_material'. Nest parameters under 'parameters' — "
            "this will 400 once RENDER_STRICT_PAYLOAD is on.",
            project_slug or "<default>",
            mode_id,
            _request_origin(),
        )
        raw_params = data

    params = validate_params(raw_params, project_slug or None)

    raw_hash = json.dumps({"s": scad_filename, "p": params}, sort_keys=True)
    param_hash = hashlib.sha256(raw_hash.encode()).hexdigest()[:10]

    base_prefix = f"{project_slug}_{Config.STL_PREFIX}" if project_slug else Config.STL_PREFIX
    stl_prefix = f"{base_prefix}{param_hash}_"

    # Inject Material Hyperobject Compensations. Read from the resolved parameter
    # container so a flattened legacy payload no longer silently loses this field.
    target_mat = raw_params.get('target_material') if isinstance(raw_params, dict) else None
    if target_mat:
        _inject_material_compensations(params, target_mat)

    scad_content_hash = compute_scad_hash(scad_path)

    return {
        'scad_filename': scad_filename,
        'scad_path': scad_path,
        'parts': parts_to_render,
        'mode_map': mode_map,
        'stl_prefix': stl_prefix,
        'mode': mode_id,
        'request_id': data.get("request_id") or str(uuid.uuid4()),
        'export_format': export_format,
        'params': params,
        'static_stl_map': static_stl_map,
        'project_slug': project_slug,
        'ignore_cache': data.get('ignore_cache', False),
        'scad_content_hash': scad_content_hash,
    }


def _inject_material_compensations(params: dict, target_mat: str) -> None:
    """Inject material hyperobject compensations into render params."""
    from services.core.material_service import get_material
    try:
        mat_manifest = get_material(target_mat)
        comps = mat_manifest.get("am_compensations", {})
        shrink = comps.get("shrinkage", {})
        clear = comps.get("clearances", {})

        params["mat_shrinkage_x"] = float(shrink.get("x", 1.0))
        params["mat_shrinkage_y"] = float(shrink.get("y", 1.0))
        params["mat_shrinkage_z"] = float(shrink.get("z", 1.0))
        params["mat_clear_press"] = float(clear.get("press_fit", 0.0))
        params["mat_clear_slide"] = float(clear.get("sliding_fit", 0.0))
        params["mat_clear_loose"] = float(clear.get("loose_fit", 0.0))

        thermo = mat_manifest.get("thermodynamics", {})
        params["thermo_glass_transition_temp"] = float(thermo.get("glass_transition_temp", 999.0))
        params["thermo_melting_temp"] = float(thermo.get("melting_temp", 999.0))
        params["thermo_yield_strength"] = float(thermo.get("yield_strength", 999.0))

        logger.info(f"Injected Material Hyperobject parameters for: {target_mat}")
    except Exception as e:
        logger.warning(f"Failed to inject material compensations for {target_mat}: {e}")


# ──────────────────────────────────────────────
# Engine Configuration
# ──────────────────────────────────────────────

def resolve_engine_config(data: dict, payload: dict, tier: str):
    """Determine the engine, validate export format, and resolve the actual render format.

    Returns (engine, scad_path, actual_format, error_tuple_or_none).
    If error_tuple_or_none is not None, it is (message, status_code).
    """
    from services.core.tier_service import check_feature

    project_slug = payload['project_slug']
    export_format = payload['export_format']
    scad_path = payload['scad_path']

    manifest = get_manifest(project_slug)
    # Per-mode engine resolution enables dual-engine cartridges (e.g. legacy
    # OpenSCAD modes alongside CadQuery modes). `scad_path` already points at the
    # active mode's primary file, so a per-mode engine routes each mode correctly.
    mode_id = data.get('mode')
    engine = manifest.mode_engine(mode_id)

    # Dual-engine fallback: CadQuery for formats the primary engine can't produce
    if mode_id and engine in ("openscad", "implicit") and export_format in ('step', 'glb', 'gltf'):
        mode_config = next((m for m in manifest.modes if m['id'] == mode_id), None)
        if mode_config and mode_config.get('cq_file'):
            engine = "cadquery"
            scad_path = os.path.join(os.path.dirname(scad_path), mode_config['cq_file'])

    # Validate engine+format compatibility
    if engine == "cadquery":
        if not check_feature(tier, "cadquery_engine"):
            return engine, scad_path, None, ("CadQuery engine is not available for your tier.", 403)
        if export_format not in Config.CADQUERY_ALLOWED_EXPORT_FORMATS:
            return engine, scad_path, None, (f"Export format '{export_format}' is not supported by CadQuery engine.", 400)
    elif engine == "graph":
        # Graph documents transpile to CadQuery scripts (services/engine/graph_engine.py),
        # so they gate and format-check like a paid backend kernel of their own.
        if not check_feature(tier, "graph_engine"):
            return engine, scad_path, None, ("Graph engine is not available for your tier.", 403)
        if export_format not in Config.GRAPH_ALLOWED_EXPORT_FORMATS:
            return engine, scad_path, None, (f"Export format '{export_format}' is not supported by graph engine.", 400)
    elif engine == "implicit":
        if export_format not in Config.IMPLICIT_ALLOWED_EXPORT_FORMATS:
            return engine, scad_path, None, (f"Export format '{export_format}' is not supported by implicit engine.", 400)
    elif engine == "openscad":
        if export_format not in Config.OPENSCAD_ALLOWED_EXPORT_FORMATS and export_format not in TRIMESH_CONVERTIBLE:
            return engine, scad_path, None, (f"Export format '{export_format}' is not supported by OpenSCAD engine.", 400)

    # Determine actual render format
    if engine in ("cadquery", "graph"):
        actual_format = export_format
    elif engine == "implicit":
        actual_format = 'stl'
    else:
        actual_format = export_format if export_format in Config.OPENSCAD_ALLOWED_EXPORT_FORMATS else 'stl'

    return engine, scad_path, actual_format, None


# ──────────────────────────────────────────────
# Part Rendering (shared between sync and stream)
# ──────────────────────────────────────────────

def _render_static_part(part, static_stl_map, stl_prefix, export_format, project_slug):
    """Handle a pre-existing static STL part. Returns (part_info, log_line) or None."""
    if part not in static_stl_map:
        return None
    static_path = static_stl_map[part]
    if not static_path.is_file():
        return None

    serve_url = f"/api/projects/{project_slug}/parts/{static_path.name}"
    if export_format != 'stl' and export_format in TRIMESH_CONVERTIBLE:
        conv_filename = f"{stl_prefix}{part}_static.{export_format}"
        conv_path = os.path.join(STATIC_FOLDER, conv_filename)
        if convert_mesh(str(static_path), conv_path):
            serve_url = f"/static/{conv_filename}"

    try:
        size_bytes = os.path.getsize(static_path)
    except OSError:
        size_bytes = None

    return {
        "type": part,
        "url": serve_url,
        "size_bytes": size_bytes,
    }, f"[{part}] static STL: {static_path.name}\n"


def _check_cache(payload, part, export_format):
    """Check render cache for a part. Returns cached entry dict or None."""
    if payload.get('ignore_cache', False):
        return None
    return render_cache.get(
        payload['project_slug'], payload['scad_filename'],
        payload['params'], part, export_format,
        scad_content_hash=payload.get('scad_content_hash'),
    )


def _post_render_convert(output_path, output_filename, part, stl_prefix,
                          actual_format, export_format):
    """Handle post-render format conversion and STL→GLB delivery conversion.

    Returns (final_path, final_filename, viewer_filename).

    - final_filename: the file in the requested export_format (used for download).
    - viewer_filename: a GLB version for the 3D viewer (only populated when
      export_format == 'stl' and conversion succeeds; None otherwise).

    The two are kept separate so that a download request for 'stl' delivers a
    real STL file while the viewer can still consume the GLB.
    """
    serve_path, serve_filename = output_path, output_filename
    viewer_filename = None

    if actual_format != export_format:
        final_filename = f"{stl_prefix}{part}.{export_format}"
        final_path = os.path.join(STATIC_FOLDER, final_filename)
        if convert_mesh(output_path, final_path):
            serve_path, serve_filename = final_path, final_filename
        else:
            logger.warning("Format conversion to %s failed for part %s", export_format, part)

    if export_format == "stl":
        glb_filename = f"{stl_prefix}{part}.glb"
        glb_path = os.path.join(STATIC_FOLDER, glb_filename)

        # Prefer 3MF → GLB conversion (preserves per-face colors from OpenSCAD)
        threemf_path = output_path.rsplit('.stl', 1)[0] + '.3mf' if output_path.endswith('.stl') else None
        if threemf_path and os.path.isfile(threemf_path):
            if convert_mesh(threemf_path, glb_path):
                viewer_filename = glb_filename
                logger.info("Color-preserving 3MF→GLB conversion for part %s", part)
            elif stl_to_glb(output_path, glb_path):
                viewer_filename = glb_filename
        elif stl_to_glb(output_path, glb_path):
            # Fallback: STL → GLB (no colors, but still works)
            viewer_filename = glb_filename

    return serve_path, serve_filename, viewer_filename


def _coerce_channel(value) -> str:
    """Decode Redis pubsub channel names consistently across client versions."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _read_render_worker_last_seen() -> int | None:
    """Return the last worker heartbeat timestamp from Redis."""
    try:
        raw = r.get(RENDER_WORKER_HEARTBEAT_KEY)
        if not raw:
            return None

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return int(float(raw.strip()))
    except Exception:
        return None


def is_render_worker_available() -> bool:
    """Return True when the dedicated render worker has published heartbeat."""
    last_seen = _read_render_worker_last_seen()
    if last_seen is None:
        return False
    return (int(time.time()) - last_seen) <= RENDER_WORKER_HEARTBEAT_TTL_SECONDS * 2


def get_render_worker_status() -> dict:
    """Return render worker and queue status for readiness/operations surfaces."""
    last_seen = _read_render_worker_last_seen()
    now = int(time.time())
    age_seconds = None if last_seen is None else max(0, now - last_seen)
    available = (
        age_seconds is not None
        and age_seconds <= RENDER_WORKER_HEARTBEAT_TTL_SECONDS * 2
    )

    try:
        queue_depth = r.llen(RENDER_QUEUE)
    except Exception:
        queue_depth = None

    try:
        active_jobs = r.scard(ACTIVE_RENDER_JOBS_KEY)
    except Exception:
        active_jobs = None

    return {
        "available": available,
        "heartbeat_key": RENDER_WORKER_HEARTBEAT_KEY,
        "heartbeat_ttl_seconds": RENDER_WORKER_HEARTBEAT_TTL_SECONDS,
        "last_seen": last_seen,
        "age_seconds": age_seconds,
        "queue_depth": queue_depth,
        "active_jobs": active_jobs,
    }


def _parse_stream_payload(message_data) -> dict | None:
    """Parse JSON from Redis payload and normalize missing protocol metadata."""
    if message_data is None:
        return None
    try:
        payload = json.loads(message_data)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    payload.setdefault("stream_protocol", RENDER_STREAM_SCHEMA_VERSION)
    return payload


def _sse_event(payload: dict) -> str:
    """Serialize one render event as an SSE data frame."""
    return f"data: {json.dumps(payload)}\n\n"


def _sanitize_terminal_payload(payload: dict | None) -> dict:
    """Strip protocol metadata and event envelope for client-facing artifacts."""
    payload = payload or {}
    clean = payload.copy()
    if isinstance(clean.get("part_entry"), dict) and "type" in clean["part_entry"]:
        nested = clean.pop("part_entry")
        if isinstance(nested, dict):
            merged = nested.copy()
            for key, value in clean.items():
                if key in {"event", "stream_protocol", "part_entry"}:
                    continue
                if key not in merged:
                    merged[key] = value
            clean = merged
    clean.pop("event", None)
    clean.pop("stream_protocol", None)
    return clean


def render_parts_sync(data: dict, payload: dict, engine: str, scad_path: str, actual_format: str, tier: str):
    parts_to_render = payload['parts']
    stl_prefix = payload['stl_prefix']
    export_format = payload['export_format']
    project_slug = payload['project_slug']
    static_stl_map = payload.get('static_stl_map', {})
    
    request_id = payload.get("request_id")

    generated_parts = []
    combined_log = ""
    cache_hits, cache_total = 0, 0

    clear_request_cancel(request_id)

    for part in parts_to_render:
        # /api/render answers only when every part is done, so a caller can
        # cancel it only by supplying its own `request_id` up front — which is
        # exactly what the field is for on this path.
        if is_request_cancelled(request_id):
            combined_log += f"[{part}] INFO: Render cancelled by user request\n"
            break

        static_result = _render_static_part(part, static_stl_map, stl_prefix, export_format, project_slug)
        if static_result:
            generated_parts.append(static_result[0])
            combined_log += static_result[1]
            continue
            
        output_filename = f"{stl_prefix}{part}.{actual_format}"
        output_path = os.path.join(STATIC_FOLDER, output_filename)
        cache_total += 1
        
        cached = _check_cache(payload, part, export_format)
        if cached:
            cache_hits += 1
            combined_log += f"[{part}] cache HIT\n"
            generated_parts.append({"type": part, "url": f"/static/{os.path.basename(cached['path'])}", "size_bytes": cached["size_bytes"]})
            continue

        if not is_render_worker_available():
            return None, "Render worker unavailable or not healthy", (cache_hits, cache_total)

        job_id = str(uuid.uuid4())
        render_channel = render_channel_for_job(job_id)
        final_channel = render_final_channel_for_job(job_id)
        part_sub = r.pubsub(ignore_subscribe_messages=True)
        part_sub.subscribe(render_channel)
        part_sub.subscribe(final_channel)

        task = {
            "request_id": payload.get("request_id"),
            "mode": payload.get("mode"),
            "scad_filename": payload.get("scad_filename"),
            "job_id": job_id, "stream": False, "engine": engine, "part": part, 
            "payload": payload, "scad_path": scad_path, "output_path": output_path, 
            "export_format": export_format
        }
        r.rpush(RENDER_QUEUE, json.dumps(task))

        part_deadline = time.time() + RENDER_PART_WAIT_TIMEOUT_SECONDS
        part_complete = False
        while not part_complete:
            if time.time() > part_deadline:
                combined_log += f"[{part}] ERROR: Render timed out while waiting for completion\n"
                _notify_error(job_id, part, "Render job timed out")
                break

            message = part_sub.get_message(timeout=1.0)
            if not message:
                continue

            channel = _coerce_channel(message.get("channel", ""))
            event_payload = _parse_stream_payload(message.get("data"))
            if not event_payload:
                logger.debug("Skipping non-JSON render payload for job %s", job_id)
                continue

            event_type = event_payload.get("event")
            if channel == final_channel and is_terminal_render_event(event_payload):
                if event_type == RENDER_EVENT_PART_DONE:
                    part_entry = _sanitize_terminal_payload(event_payload)
                    combined_log += part_entry.pop("log", "")
                    generated_parts.append(part_entry)
                elif event_type == RENDER_EVENT_ERROR:
                    combined_log += f"[{event_payload.get('part', 'unknown')}] ERROR: {event_payload.get('error', event_payload.get('message'))}\n"
                elif event_type == RENDER_EVENT_CANCELLED:
                    combined_log += f"[{event_payload.get('part', 'unknown')}] INFO: {event_payload.get('message')}\n"
                else:
                    combined_log += f"[{event_payload.get('part', 'unknown')}] INFO: {event_type}\n"
                part_complete = True
            elif channel == render_channel and event_type in {
                RENDER_EVENT_PART_DONE,
                RENDER_EVENT_ERROR,
                RENDER_EVENT_CANCELLED,
            }:
                # Legacy/compat fallback: handle terminal payloads on primary channel.
                if event_type == RENDER_EVENT_PART_DONE:
                    part_entry = _sanitize_terminal_payload(event_payload)
                    combined_log += part_entry.pop("log", "")
                    generated_parts.append(part_entry)
                elif event_type == RENDER_EVENT_ERROR:
                    combined_log += f"[{event_payload.get('part', 'unknown')}] ERROR: {event_payload.get('error', event_payload.get('message'))}\n"
                else:
                    combined_log += f"[{event_payload.get('part', 'unknown')}] INFO: {event_payload.get('message')}\n"
                part_complete = True

        part_sub.close()

    return generated_parts, combined_log, (cache_hits, cache_total)

def render_parts_stream(data: dict, payload: dict, engine: str, scad_path: str, actual_format: str):
    parts_to_render = payload["parts"]
    stl_prefix = payload["stl_prefix"]
    export_format = payload["export_format"]
    project_slug = payload["project_slug"]
    static_stl_map = payload.get("static_stl_map", {})

    num_parts = len(parts_to_render)
    generated_parts = []
    request_id = payload.get("request_id")
    job_ids: list[str] = []

    # A fresh render supersedes any cancel still flagged against a reused
    # request_id, so a client that supplies a fixed one is not stuck cancelled
    # for the rest of CANCEL_TTL_SECONDS.
    clear_request_cancel(request_id)

    # Hand the client its cancellation identity before any work starts. The
    # request_id is usable immediately and covers the parts that do not exist
    # yet; job_ids fill in below as each part is queued.
    yield _sse_event(build_render_event(
        RENDER_EVENT_JOB,
        request_id=request_id,
        job_ids=list(job_ids),
    ))

    for i, part in enumerate(parts_to_render):
        # Parts are queued one at a time, so this is the only place a cancel can
        # stop the parts that have not been queued yet.
        if is_request_cancelled(request_id):
            yield _sse_event(build_render_event(
                RENDER_EVENT_CANCELLED,
                part=part,
                message="Render cancelled by user request",
                reason="user_request",
            ))
            break

        static_result = _render_static_part(part, static_stl_map, stl_prefix, export_format, project_slug)
        if static_result:
            generated_parts.append(static_result[0])
            progress = ((i + 1) / num_parts) * 100
            yield _sse_event(build_render_event(
                    RENDER_EVENT_PART_DONE,
                    part=part,
                    progress=progress,
                    part_index=i,
                    total_parts=num_parts,
                )
            )
            continue

        output_filename = f"{stl_prefix}{part}.{actual_format}"
        output_path = os.path.join(STATIC_FOLDER, output_filename)

        cached = _check_cache(payload, part, export_format)
        if cached:
            generated_parts.append(
                {
                    "type": part,
                    "url": f"/static/{os.path.basename(cached['path'])}",
                    "size_bytes": cached["size_bytes"],
                }
            )
            progress = ((i + 1) / num_parts) * 100
            yield _sse_event(build_render_event(
                    RENDER_EVENT_PART_DONE,
                    part=part,
                    progress=progress,
                    part_index=i,
                    total_parts=num_parts,
                    cached=True,
                )
            )
            continue

        if not is_render_worker_available():
            unavailable_error = build_render_event(
                RENDER_EVENT_ERROR,
                part=part,
                error="Render worker unavailable or not healthy",
                message="Render worker unavailable or not healthy",
            )
            unavailable_complete = build_render_event(
                RENDER_EVENT_COMPLETE,
                parts=generated_parts,
                progress=100,
                error="Render worker unavailable or not healthy",
                part=part,
            )
            yield _sse_event(unavailable_error)
            yield _sse_event(unavailable_complete)
            return

        part_base = (i / num_parts) * PROGRESS_TOTAL
        part_weight = PROGRESS_TOTAL / num_parts

        job_id = str(uuid.uuid4())
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        render_channel = render_channel_for_job(job_id)
        final_channel = render_final_channel_for_job(job_id)
        pubsub.subscribe(render_channel)
        pubsub.subscribe(final_channel)

        task = {
            "request_id": payload.get("request_id"),
            "mode": payload.get("mode"),
            "scad_filename": payload.get("scad_filename"),
            "job_id": job_id,
            "stream": True,
            "engine": engine,
            "part": part,
            "payload": payload,
            "scad_path": scad_path,
            "output_path": output_path,
            "export_format": export_format,
            "part_index": i,
            "num_parts": num_parts,
            "part_base": part_base,
            "part_weight": part_weight,
        }
        r.rpush(RENDER_QUEUE, json.dumps(task))
        job_ids.append(job_id)
        yield _sse_event(build_render_event(
            RENDER_EVENT_JOB,
            request_id=request_id,
            job_ids=list(job_ids),
        ))

        done = False
        part_deadline = time.time() + RENDER_STREAM_PART_TIMEOUT_SECONDS

        while not done:
            if time.time() > part_deadline:
                timeout_event = build_render_event(
                    RENDER_EVENT_ERROR,
                    part=part,
                    error="Render stream timed out waiting for completion",
                    message="Render stream timed out waiting for completion",
                )
                yield f"data: {json.dumps(timeout_event)}\n\n"
                _notify_error(job_id, part, "Render stream timed out waiting for completion")
                break

            message = pubsub.get_message(timeout=0.2)
            if not message:
                continue

            channel = _coerce_channel(message.get("channel", ""))
            event_data = _parse_stream_payload(message.get("data"))
            if event_data is None:
                logger.debug("Skipping malformed render payload for part %s", part)
                continue

            if channel == render_channel:
                yield f"data: {json.dumps(event_data)}\n\n"
                if event_data.get("event") == RENDER_EVENT_PART_DONE and event_data.get("type"):
                    generated_parts.append(_sanitize_terminal_payload(event_data))
                    done = True
                continue

            if channel != final_channel:
                continue

            event_type = event_data.get("event")
            if event_type == RENDER_EVENT_PART_DONE:
                generated_parts.append(_sanitize_terminal_payload(event_data))
                done = True
            elif event_type == RENDER_EVENT_ERROR:
                logger.error(
                    "Render stream error for part %s: %s",
                    event_data.get("part"),
                    event_data.get("error"),
                )
                yield f"data: {json.dumps(event_data)}\n\n"
                done = True
            elif event_type == RENDER_EVENT_CANCELLED:
                logger.info(
                    "Render stream cancelled for part %s (reason=%s)",
                    event_data.get("part"),
                    event_data.get("reason"),
                )
                yield f"data: {json.dumps(event_data)}\n\n"
                done = True
            elif event_type:
                logger.info("Render stream event for part %s: %s", part, event_type)
                yield f"data: {json.dumps(event_data)}\n\n"
                done = True
            else:
                generated_parts.append(event_data)
                done = True

        pubsub.close()

    yield _sse_event(build_render_event(
            RENDER_EVENT_COMPLETE,
            parts=generated_parts,
            progress=100,
        )
    )


# ──────────────────────────────────────────────
# Cancellation
#
# Three scopes, one mechanism. The worker (apps/worker/render_worker.py::
# _is_cancelled) polls two Redis keys for every job it runs: the global
# CANCEL_ALL_KEY and the per-job CANCEL_JOB_PREFIX + job_id. Scoped cancellation
# therefore needs no worker change — it sets the per-job key the worker already
# honours, for the jobs it is allowed to touch, instead of the global one.
#
# The third key, CANCEL_REQUEST_PREFIX + request_id, is read here rather than by
# the worker: a multi-part render enqueues its parts one at a time, so stopping
# a request means stopping the render loop from queueing the parts that do not
# exist yet.
# ──────────────────────────────────────────────


def _request_cancel_key(request_id: str) -> str:
    return f"{CANCEL_REQUEST_PREFIX}{request_id}"


def is_request_cancelled(request_id: str | None) -> bool:
    """True while a scoped cancel is outstanding for this render request."""
    if not request_id:
        return False
    try:
        return bool(r.get(_request_cancel_key(request_id)))
    except Exception:
        # Fail open: an unreachable Redis must not silently abort live renders.
        logger.debug("Failed to read cancel flag for request %s", request_id, exc_info=True)
        return False


def clear_request_cancel(request_id: str | None) -> None:
    """Drop any stale cancel flag before a request's first part is queued.

    `request_id` is caller-suppliable, so a client that reuses a fixed one would
    otherwise inherit its own previous cancellation for CANCEL_TTL_SECONDS and
    watch every later render die instantly. A new render supersedes an old
    cancel.
    """
    if not request_id:
        return
    try:
        r.delete(_request_cancel_key(request_id))
    except Exception:
        logger.debug("Failed to clear cancel flag for request %s", request_id, exc_info=True)


def _iter_queued_tasks():
    """Yield (raw_entry, parsed_task) for each readable entry in the render queue."""
    try:
        raw_tasks = r.lrange(RENDER_QUEUE, 0, -1)
    except Exception as e:
        logger.warning("Failed to read pending render queue items: %s", e)
        return
    for raw_task in raw_tasks:
        if not raw_task:
            continue
        try:
            task = json.loads(raw_task)
        except json.JSONDecodeError:
            continue
        if isinstance(task, dict):
            yield raw_task, task


def _active_job_meta(job_id: str) -> dict:
    """Return the worker's metadata for an active job, or {} when unreadable."""
    try:
        meta = r.get(f"{ACTIVE_RENDER_META_PREFIX}{job_id}")
    except Exception:
        logger.debug("Failed to read meta for active render %s", job_id, exc_info=True)
        return {}
    if not meta:
        return {}
    try:
        parsed = json.loads(meta)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _cancel_matching(matches) -> list[str]:
    """Cancel every queued and active job the `matches(task)` predicate accepts.

    Queued entries are pruned from RENDER_QUEUE so they never start; active jobs
    get the per-job cancel key the worker polls. Both are told on their render
    channel. `matches` receives the queue task dict, or for an active job its
    worker metadata with `job_id` merged in — a job whose metadata has expired
    matches nothing but a job_id, which is the conservative direction: we cancel
    only what we can still attribute.

    Returns the job_ids actually marked.
    """
    cancelled: list[str] = []

    for raw_task, task in _iter_queued_tasks():
        job_id = task.get("job_id")
        if not job_id or not matches(task):
            continue
        try:
            r.lrem(RENDER_QUEUE, 0, raw_task)
        except Exception as e:
            logger.warning("Failed to prune queued render %s: %s", job_id, e)
            continue
        _notify_cancelled(job_id, task.get("part"), emit_final=True)
        cancelled.append(job_id)

    try:
        active_jobs = [jid for jid in r.smembers(ACTIVE_RENDER_JOBS_KEY) if jid]
    except Exception as e:
        logger.warning("Failed to read active render jobs for cancellation: %s", e)
        active_jobs = []

    for job_id in active_jobs:
        if job_id in cancelled:
            continue
        meta = _active_job_meta(job_id)
        if not matches({**meta, "job_id": job_id}):
            continue
        try:
            _set_job_cancel(job_id)
        except Exception as e:
            logger.warning("Failed to mark active render %s for cancellation: %s", job_id, e)
            continue
        _notify_cancelled(job_id, meta.get("part", ""), emit_final=True)
        cancelled.append(job_id)

    return cancelled


def cancel_render_jobs(job_ids) -> list[str]:
    """Cancel exactly the named jobs, and nothing else.

    `job_id`s are server-generated UUID4s published only on the requesting
    client's own SSE stream (the `job` event), so knowing one is the proof of
    entitlement that lets this endpoint stay open to anonymous callers.
    """
    wanted = {job_id for job_id in job_ids if job_id}
    if not wanted:
        return []
    cancelled = _cancel_matching(lambda task: task.get("job_id") in wanted)
    logger.info(
        "Render cancel by job_id: %d requested, %d marked", len(wanted), len(cancelled)
    )
    return cancelled


def cancel_request(request_id: str) -> list[str]:
    """Cancel one render request: its queued and active parts, and its future ones.

    The flag is set first so the render loop stops queueing further parts even if
    the sweep below races the part currently in flight.
    """
    if not request_id:
        return []
    try:
        r.set(_request_cancel_key(request_id), "1", ex=CANCEL_TTL_SECONDS)
    except Exception as e:
        logger.warning("Render cancel requested but Redis is unavailable: %s", e)
        return []

    cancelled = _cancel_matching(lambda task: task.get("request_id") == request_id)
    logger.info("Render cancel by request_id: %d jobs marked", len(cancelled))
    return cancelled


def cancel_all_renders() -> bool:
    """Cancel every render on the box, queued and active, for every caller.

    Reachable over HTTP only via `POST /api/render-cancel {"all": true}`, which
    requires the `admin` role — the single backend replica means "every render"
    is literal, so this is an operator tool, not a client one.
    """
    try:
        r.set(CANCEL_ALL_KEY, str(int(time.time())), ex=CANCEL_EVENT_TTL_SECONDS)
    except Exception as e:
        logger.warning("Render cancel requested but Redis is unavailable: %s", e)
        return False

    cancelled = _cancel_matching(lambda _task: True)
    if cancelled:
        logger.info("Render cancel-all requested; marked %d jobs", len(cancelled))
    return bool(cancelled)


def _notify_cancelled(job_id: str, part: str, emit_final: bool = True) -> None:
    payload = build_render_event(
        RENDER_EVENT_CANCELLED,
        part=part or "",
        message="Render cancelled by user request",
        reason="user_request",
    )
    payload_json = json.dumps(payload)
    try:
        r.publish(render_channel_for_job(job_id), payload_json)
        if emit_final:
            r.publish(render_final_channel_for_job(job_id), payload_json)
    except Exception:
        logger.debug("Failed to notify cancellation for job %s", job_id, exc_info=True)


def _notify_error(job_id: str, part: str, message: str, emit_final: bool = True) -> None:
    payload = build_render_event(
        RENDER_EVENT_ERROR,
        part=part or "",
        error=message,
        message=message,
    )
    payload_json = json.dumps(payload)
    try:
        r.publish(render_channel_for_job(job_id), payload_json)
        if emit_final:
            r.publish(render_final_channel_for_job(job_id), payload_json)
    except Exception:
        logger.debug("Failed to notify render error for job %s", job_id, exc_info=True)


def _set_job_cancel(job_id: str) -> None:
    r.set(f"{CANCEL_JOB_PREFIX}{job_id}", "1", ex=CANCEL_TTL_SECONDS)


def cancel_openscad_render() -> bool:
    """Backward-compatible cancellation hook for OpenSCAD jobs."""
    return _cancel_by_engine("openscad")


def cancel_cadquery_render() -> bool:
    """Backward-compatible cancellation hook for CadQuery jobs."""
    return _cancel_by_engine("cadquery")


# `cancel_active_render()` used to live here as a "backward-compatible alias"
# for cancel_all_renders(). Its only caller was the unauthenticated WebSocket
# render channel, which gave any anonymous client a cancel-everything button.
# The alias is removed so that path cannot be reopened by accident; cancelling
# from a request goes through routes/engine/render.py::cancel_render_endpoint.


def _cancel_by_engine(engine: str) -> bool:
    """Cancel only jobs currently tracked for a specific engine."""
    return bool(_cancel_matching(lambda task: task.get("engine") == engine))
