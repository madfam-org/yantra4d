"""
Render Orchestrator Service
Centralizes engine selection, format validation, render execution, caching,
and post-render conversions. Eliminates duplication between sync/stream paths.
"""
import json
import logging
import os
import uuid

import redis

from config import Config
from manifest import get_manifest
from services.engine.openscad import compute_scad_hash, validate_params
from services.engine.render_cache import render_cache
from services.engine.format_converter import stl_to_glb, convert_mesh

r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

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


def render_parts_sync(data: dict, payload: dict, engine: str, scad_path: str, actual_format: str, tier: str):
    parts_to_render = payload['parts']
    stl_prefix = payload['stl_prefix']
    export_format = payload['export_format']
    project_slug = payload['project_slug']
    static_stl_map = payload.get('static_stl_map', {})
    
    generated_parts = []
    combined_log = ""
    cache_hits, cache_total = 0, 0
    job_ids = []
    
    pubsub = r.pubsub(ignore_subscribe_messages=True)

    for part in parts_to_render:
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

        job_id = str(uuid.uuid4())
        job_ids.append((job_id, part))
        pubsub.subscribe(f"render:{job_id}")

        task = {
            "job_id": job_id, "stream": False, "engine": engine, "part": part, 
            "payload": payload, "scad_path": scad_path, "output_path": output_path, 
            "export_format": export_format
        }
        r.rpush("yantra_render_queue", json.dumps(task))

    completed_jobs = 0
    while completed_jobs < len(job_ids):
        message = pubsub.get_message(timeout=1.0)
        if message:
            data = json.loads(message['data'])
            if data.get('event') == 'part_done':
                pe = data['part_entry']
                combined_log += pe.pop('log', '')
                generated_parts.append(pe)
                completed_jobs += 1
            elif data.get('event') == 'error':
                combined_log += f"[{data['part']}] ERROR: {data['error']}\n"
                completed_jobs += 1
    
    pubsub.close()
    return generated_parts, combined_log, (cache_hits, cache_total)

def render_parts_stream(data: dict, payload: dict, engine: str, scad_path: str, actual_format: str):
    parts_to_render = payload['parts']
    stl_prefix = payload['stl_prefix']
    export_format = payload['export_format']
    project_slug = payload['project_slug']
    static_stl_map = payload.get('static_stl_map', {})
    
    num_parts = len(parts_to_render)
    generated_parts = []
    
    for i, part in enumerate(parts_to_render):
        static_result = _render_static_part(part, static_stl_map, stl_prefix, export_format, project_slug)
        if static_result:
            generated_parts.append(static_result[0])
            progress = ((i + 1) / num_parts) * 100
            yield f"data: {json.dumps({'event': 'part_done', 'part': part, 'progress': progress, 'part_index': i, 'total_parts': num_parts})}\n\n"
            continue
            
        output_filename = f"{stl_prefix}{part}.{actual_format}"
        output_path = os.path.join(STATIC_FOLDER, output_filename)
        
        cached = _check_cache(payload, part, export_format)
        if cached:
            generated_parts.append({"type": part, "url": f"/static/{os.path.basename(cached['path'])}", "size_bytes": cached["size_bytes"]})
            progress = ((i + 1) / num_parts) * 100
            yield f"data: {json.dumps({'event': 'part_done', 'part': part, 'progress': progress, 'part_index': i, 'total_parts': num_parts, 'cached': True})}\n\n"
            continue

        part_base = (i / num_parts) * PROGRESS_TOTAL
        part_weight = PROGRESS_TOTAL / num_parts

        job_id = str(uuid.uuid4())
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(f"render:{job_id}")
        pubsub.subscribe(f"render:{job_id}:final")

        task = {
            "job_id": job_id, "stream": True, "engine": engine, "part": part, "payload": payload,
            "scad_path": scad_path, "output_path": output_path, "export_format": export_format,
            "part_index": i, "num_parts": num_parts, "part_base": part_base, "part_weight": part_weight
        }
        r.rpush("yantra_render_queue", json.dumps(task))

        done = False
        while not done:
            message = pubsub.get_message(timeout=0.1)
            if message:
                if message['channel'] == f"render:{job_id}":
                    # Directly yield the raw SSE event
                    yield f"data: {message['data']}\n\n"
                elif message['channel'] == f"render:{job_id}:final":
                    generated_parts.append(json.loads(message['data']))
                    done = True
        
        pubsub.close()

    yield f"data: {json.dumps({'event': 'complete', 'parts': generated_parts, 'progress': 100})}\n\n"


# ──────────────────────────────────────────────
# Cancellation
# ──────────────────────────────────────────────

def cancel_all_renders() -> bool:
    """Cancel any active render processes across all engines."""
    # TODO: Implement queue-based cancellation
    return True
