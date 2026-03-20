"""
Render Orchestrator Service
Centralizes engine selection, format validation, render execution, caching,
and post-render conversions. Eliminates duplication between sync/stream paths.
"""
import json
import logging
import os
import queue

from config import Config
from manifest import get_manifest
from services.engine.openscad import (
    build_openscad_command,
    compute_scad_hash,
    run_render as run_openscad_render,
    stream_render as stream_openscad_render,
    cancel_render as cancel_openscad_render,
    validate_params,
)
from services.engine.cadquery_engine import (
    build_cadquery_command,
    run_render as run_cadquery_render,
    stream_render as stream_cadquery_render,
    cancel_render as cancel_cadquery_render,
)
from services.core.implicit_engine import (
    run_render as run_implicit_render,
    stream_render as stream_implicit_render,
)
from services.engine.render_cache import render_cache
from services.engine.format_converter import stl_to_glb, convert_mesh
from services.core.mqtt_telemetry import telemetry_service, telemetry_queue
from utils.route_helpers import cleanup_old_stl_files
from utils.metrics import RENDERS_TOTAL, RENDER_DURATION

ALLOWED_EXPORT_FORMATS = {'stl', '3mf', 'off', 'step', 'gltf', 'glb', 'obj'}
TRIMESH_CONVERTIBLE = {'obj', 'ply', 'glb', 'gltf', '3mf', 'off'}
PROGRESS_TOTAL = 100

logger = logging.getLogger(__name__)

STATIC_FOLDER = str(Config.STATIC_DIR)


# ──────────────────────────────────────────────
# Payload Resolution
# ──────────────────────────────────────────────

class RenderPayloadError:
    """Structured error from payload resolution."""

    def __init__(self, message: str, bad_name: str | None = None):
        self.message = message
        self.bad_name = bad_name


def resolve_render_context(data: dict):
    """Resolve scad_file, parts, and mode_map from request payload.

    Returns (scad_filename, scad_path, parts, mode_map, static_stl_map)
    or RenderPayloadError on failure.
    """
    project_slug = data.get('project')
    manifest = get_manifest(project_slug)
    mode_id = data.get('mode')
    scad_filename = data.get('scad_file')

    if mode_id:
        scad_filename = manifest.get_scad_file_for_mode(mode_id)
        parts = manifest.get_parts_for_mode(mode_id)
    else:
        if scad_filename:
            logger.warning("Deprecated: 'scad_file' parameter used instead of 'mode'. Update client to use 'mode'.")
        else:
            scad_filename = manifest.modes[0]["scad_file"]
        parts_map = manifest.get_parts_map()
        parts = parts_map.get(scad_filename, manifest.modes[0]["parts"])

    allowed = manifest.get_allowed_files()
    if scad_filename not in allowed:
        return RenderPayloadError(f"Invalid SCAD file: {scad_filename}", bad_name=scad_filename)

    scad_path = str(allowed[scad_filename])
    mode_map = manifest.get_mode_map()
    static_stl_map = manifest.get_static_stl_map()
    return scad_filename, scad_path, parts, mode_map, static_stl_map


def extract_render_payload(data: dict) -> dict | RenderPayloadError:
    """Extract and validate all render payload fields from request data.

    Returns a dict of render parameters on success, or RenderPayloadError on failure.
    """
    import hashlib

    result = resolve_render_context(data)
    if isinstance(result, RenderPayloadError):
        return result

    scad_filename, scad_path, parts_to_render, mode_map, static_stl_map = result

    project_slug = data.get('project', '')
    export_format = data.get('export_format', 'stl')
    if export_format not in ALLOWED_EXPORT_FORMATS:
        export_format = 'stl'

    params = validate_params(data.get('parameters', data), project_slug or None)

    raw_hash = json.dumps({"s": scad_filename, "p": params}, sort_keys=True)
    param_hash = hashlib.sha256(raw_hash.encode()).hexdigest()[:10]

    base_prefix = f"{project_slug}_{Config.STL_PREFIX}" if project_slug else Config.STL_PREFIX
    stl_prefix = f"{base_prefix}{param_hash}_"

    # Inject Material Hyperobject Compensations
    target_mat = data.get('parameters', {}).get('target_material')
    if target_mat:
        _inject_material_compensations(params, target_mat)

    scad_content_hash = compute_scad_hash(scad_path)

    return {
        'scad_filename': scad_filename,
        'scad_path': scad_path,
        'parts': parts_to_render,
        'mode_map': mode_map,
        'stl_prefix': stl_prefix,
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
    engine = manifest.engine

    # Dual-engine fallback: CadQuery for formats the primary engine can't produce
    if engine in ("openscad", "implicit") and export_format in ('step', 'glb', 'gltf'):
        mode_id = data.get('mode')
        if mode_id:
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
    elif engine == "implicit":
        if export_format not in Config.IMPLICIT_ALLOWED_EXPORT_FORMATS:
            return engine, scad_path, None, (f"Export format '{export_format}' is not supported by implicit engine.", 400)
    elif engine == "openscad":
        if export_format not in Config.OPENSCAD_ALLOWED_EXPORT_FORMATS and export_format not in TRIMESH_CONVERTIBLE:
            return engine, scad_path, None, (f"Export format '{export_format}' is not supported by OpenSCAD engine.", 400)

    # Determine actual render format
    if engine == "cadquery":
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
        if stl_to_glb(output_path, glb_path):
            # Keep serve_filename as the .stl for download; GLB is viewer-only.
            viewer_filename = glb_filename

    return serve_path, serve_filename, viewer_filename


def _run_engine_render(engine, part, payload, scad_path, output_path, export_format, manifest):
    """Execute a single-part render for the given engine. Returns (success, stderr)."""
    project_slug = payload['project_slug']
    params = payload['params']
    mode_map = payload['mode_map']

    project_topic = f"yantra4d/telemetry/projects/{project_slug}"
    computed_params = telemetry_service.inject_telemetry_to_params(params, project_topic)

    if engine == "cadquery":
        cmd = build_cadquery_command(output_path, scad_path, computed_params, export_format)
        return run_cadquery_render(cmd, scad_path=scad_path)
    elif engine == "implicit":
        config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
        return run_implicit_render(output_path, config, computed_params)
    else:
        render_mode = mode_map.get(part, 0)
        cmd = build_openscad_command(output_path, scad_path, params, render_mode)
        return run_openscad_render(cmd, scad_path=scad_path)


# ──────────────────────────────────────────────
# Sync Render Orchestration
# ──────────────────────────────────────────────

def render_parts_sync(data: dict, payload: dict, engine: str, scad_path: str,
                      actual_format: str, tier: str):
    """Execute a synchronous render for all parts. Returns (parts_list, log_str, cache_stats)."""
    import time as _time

    parts_to_render = payload['parts']
    stl_prefix = payload['stl_prefix']
    export_format = payload['export_format']
    params = payload['params']
    static_stl_map = payload.get('static_stl_map', {})
    project_slug = payload['project_slug']

    manifest = get_manifest(project_slug)
    generated_parts = []
    combined_log = ""
    cache_hits = 0
    cache_total = 0

    for part in parts_to_render:
        # Static parts
        static_result = _render_static_part(part, static_stl_map, stl_prefix, export_format, project_slug)
        if static_result:
            part_info, log_line = static_result
            generated_parts.append(part_info)
            combined_log += log_line
            continue

        output_filename = f"{stl_prefix}{part}.{actual_format}"
        output_path = os.path.join(STATIC_FOLDER, output_filename)
        cache_total += 1

        # Cache check
        cached = _check_cache(payload, part, export_format)
        if cached:
            cache_hits += 1
            combined_log += f"[{part}] cache HIT\n"
            cached_filename = os.path.basename(cached["path"])
            generated_parts.append({
                "type": part,
                "url": f"/static/{cached_filename}",
                "size_bytes": cached["size_bytes"],
            })
            continue

        # Cache miss — clean up old files before re-rendering
        cleanup_old_stl_files([part], STATIC_FOLDER, stl_prefix, export_format)

        t0 = _time.monotonic()
        success, stderr = _run_engine_render(engine, part, payload, scad_path, output_path, export_format, manifest)
        duration = _time.monotonic() - t0
        RENDER_DURATION.labels(engine=engine).observe(duration)
        RENDERS_TOTAL.labels(engine=engine, format=export_format, tier=tier).inc()
        if not success:
            return None, stderr, (cache_hits, cache_total)

        combined_log += f"[{part}] {stderr}\n"

        # Post-render conversions
        serve_path, serve_filename, viewer_filename = _post_render_convert(
            output_path, output_filename, part, stl_prefix, actual_format, export_format,
        )

        try:
            size_bytes = os.path.getsize(serve_path)
        except OSError:
            size_bytes = None

        render_cache.put(
            project_slug, payload['scad_filename'], params, part, export_format,
            serve_path, size_bytes, scad_content_hash=payload.get('scad_content_hash'),
        )

        part_entry = {
            "type": part,
            "url": f"/static/{serve_filename}",
            "size_bytes": size_bytes,
        }
        if viewer_filename:
            part_entry["viewer_url"] = f"/static/{viewer_filename}"
        generated_parts.append(part_entry)

    return generated_parts, combined_log, (cache_hits, cache_total)


# ──────────────────────────────────────────────
# Streaming Render Orchestration
# ──────────────────────────────────────────────

def render_parts_stream(data: dict, payload: dict, engine: str, scad_path: str,
                        actual_format: str):
    """Generator that streams render progress as SSE event strings.

    Yields `data: {...}\n\n` formatted strings.
    """
    parts_to_render = payload['parts']
    stl_prefix = payload['stl_prefix']
    export_format = payload['export_format']
    params = payload['params']
    static_stl_map = payload.get('static_stl_map', {})
    project_slug = payload['project_slug']

    manifest = get_manifest(project_slug)
    num_parts = len(parts_to_render)
    generated_parts = []

    for i, part in enumerate(parts_to_render):
        # Static parts
        static_result = _render_static_part(part, static_stl_map, stl_prefix, export_format, project_slug)
        if static_result:
            part_info, _ = static_result
            generated_parts.append(part_info)
            progress = ((i + 1) / num_parts) * 100
            yield f"data: {json.dumps({'event': 'part_done', 'part': part, 'progress': progress, 'part_index': i, 'total_parts': num_parts})}\n\n"
            continue

        output_filename = f"{stl_prefix}{part}.{actual_format}"
        output_path = os.path.join(STATIC_FOLDER, output_filename)

        # Cache check
        cached = _check_cache(payload, part, export_format)
        if cached:
            cached_filename = os.path.basename(cached["path"])
            generated_parts.append({
                "type": part,
                "url": f"/static/{cached_filename}",
                "size_bytes": cached["size_bytes"],
            })
            progress = ((i + 1) / num_parts) * 100
            yield f"data: {json.dumps({'event': 'part_done', 'part': part, 'progress': progress, 'part_index': i, 'total_parts': num_parts, 'cached': True})}\n\n"
            continue

        cleanup_old_stl_files([part], STATIC_FOLDER, stl_prefix, export_format)

        part_base = (i / num_parts) * PROGRESS_TOTAL
        part_weight = PROGRESS_TOTAL / num_parts

        project_topic = f"yantra4d/telemetry/projects/{project_slug}"
        computed_params = telemetry_service.inject_telemetry_to_params(params, project_topic)
        mode_map = payload['mode_map']

        if engine == "cadquery":
            cmd = build_cadquery_command(output_path, scad_path, computed_params, export_format)
            stream_gen = stream_cadquery_render(cmd, part, part_base, part_weight, i, num_parts, scad_path=scad_path)
        elif engine == "implicit":
            config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
            stream_gen = stream_implicit_render(output_path, config, computed_params, part, part_base, part_weight, i, num_parts)
        else:
            render_mode = mode_map.get(part, 0)
            cmd = build_openscad_command(output_path, scad_path, params, render_mode)
            stream_gen = stream_openscad_render(cmd, part, part_base, part_weight, i, num_parts, scad_path=scad_path)

        for event_data in stream_gen:
            yield f"data: {event_data}\n\n"
            try:
                event = json.loads(event_data)
            except json.JSONDecodeError:
                logger.warning(f"Malformed SSE event data: {event_data!r}")
                continue
            if event.get('event') == 'part_done':
                serve_path, serve_filename, viewer_filename = _post_render_convert(
                    output_path, output_filename, part, stl_prefix, actual_format, export_format,
                )
                try:
                    size_bytes = os.path.getsize(serve_path)
                except OSError:
                    size_bytes = None
                render_cache.put(
                    project_slug, payload['scad_filename'], params, part, export_format,
                    serve_path, size_bytes, scad_content_hash=payload.get('scad_content_hash'),
                )
                part_entry = {
                    "type": part,
                    "url": f"/static/{serve_filename}",
                    "size_bytes": size_bytes,
                }
                if viewer_filename:
                    part_entry["viewer_url"] = f"/static/{viewer_filename}"
                generated_parts.append(part_entry)

        # Drain telemetry events
        while not telemetry_queue.empty():
            try:
                telemetry_event = telemetry_queue.get_nowait()
                if telemetry_event['topic'] == project_topic:
                    yield f"data: {json.dumps({'event': 'telemetry_update', 'payload': telemetry_event['payload']})}\n\n"
            except queue.Empty:
                break

    yield f"data: {json.dumps({'event': 'complete', 'parts': generated_parts, 'progress': 100})}\n\n"


# ──────────────────────────────────────────────
# Cancellation
# ──────────────────────────────────────────────

def cancel_all_renders() -> bool:
    """Cancel any active render processes across all engines."""
    cancelled_scad = cancel_openscad_render()
    cancelled_cq = cancel_cadquery_render()
    return cancelled_scad or cancelled_cq
