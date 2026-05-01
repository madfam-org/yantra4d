"""
Yantra4D Render Worker.

Consumes CAD rendering tasks from Redis queue and executes them via OpenSCAD or CadQuery.
Publishes progress and completion events via Redis Pub/Sub back to the API.
"""
import json
import logging
import os
import time
import redis

# Use the same imports as the orchestrator to run the actual engines
from config import Config
from manifest import get_manifest
from services.engine.openscad import build_openscad_command, run_render as run_openscad_render, stream_render as stream_openscad_render
from services.engine.cadquery_engine import build_cadquery_command, run_render as run_cadquery_render, stream_render as stream_cadquery_render
from services.core.implicit_engine import run_render as run_implicit_render, stream_render as stream_implicit_render
from services.engine.render_cache import render_cache
from services.engine.format_converter import convert_mesh, stl_to_glb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

STATIC_FOLDER = str(Config.STATIC_DIR)

def _post_render_convert(output_path, output_filename, part, stl_prefix, actual_format, export_format):
    serve_path, serve_filename = output_path, output_filename
    viewer_filename = None

    if actual_format != export_format:
        final_filename = f"{stl_prefix}{part}.{export_format}"
        final_path = os.path.join(STATIC_FOLDER, final_filename)
        if convert_mesh(output_path, final_path):
            serve_path, serve_filename = final_path, final_filename

    if export_format == "stl":
        glb_filename = f"{stl_prefix}{part}.glb"
        glb_path = os.path.join(STATIC_FOLDER, glb_filename)
        threemf_path = output_path.rsplit('.stl', 1)[0] + '.3mf' if output_path.endswith('.stl') else None
        if threemf_path and os.path.isfile(threemf_path):
            if convert_mesh(threemf_path, glb_path):
                viewer_filename = glb_filename
            elif stl_to_glb(output_path, glb_path):
                viewer_filename = glb_filename
        elif stl_to_glb(output_path, glb_path):
            viewer_filename = glb_filename

    return serve_path, serve_filename, viewer_filename

def process_sync_task(task):
    """Processes a synchronous render task and publishes the final result."""
    job_id = task['job_id']
    engine = task['engine']
    part = task['part']
    payload = task['payload']
    scad_path = task['scad_path']
    output_path = task['output_path']
    export_format = task['export_format']
    project_slug = payload['project_slug']
    params = payload['params']
    mode_map = payload['mode_map']

    manifest = get_manifest(project_slug)
    
    logger.info(f"Worker processing sync render for part {part} using {engine}")
    
    # Simple execution (no telemetry routing for worker sync simplicity)
    if engine == "cadquery":
        cp_copy = params.copy()
        cp_copy["target_part"] = part
        cmd = build_cadquery_command(output_path, scad_path, cp_copy, export_format)
        success, stderr = run_cadquery_render(cmd, scad_path=scad_path)
    elif engine == "implicit":
        config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
        success, stderr = run_implicit_render(output_path, config, params)
    else:
        render_mode = mode_map.get(part, 0)
        cmd = build_openscad_command(output_path, scad_path, params, render_mode)
        success, stderr = run_openscad_render(cmd, scad_path=scad_path)

    if not success:
        r.publish(f"render:{job_id}", json.dumps({"event": "error", "part": part, "error": stderr}))
        return

    # Post-render
    output_filename = os.path.basename(output_path)
    actual_format = output_filename.rsplit('.', 1)[-1]
    serve_path, serve_filename, viewer_filename = _post_render_convert(
        output_path, output_filename, part, payload['stl_prefix'], actual_format, export_format
    )

    try:
        size_bytes = os.path.getsize(serve_path)
    except OSError:
        size_bytes = None

    render_cache.put(
        project_slug, payload['scad_filename'], params, part, export_format,
        serve_path, size_bytes, scad_content_hash=payload.get('scad_content_hash')
    )

    part_entry = {
        "type": part,
        "url": f"/static/{serve_filename}",
        "size_bytes": size_bytes,
        "log": f"[{part}] {stderr}\n"
    }
    if viewer_filename:
        part_entry["viewer_url"] = f"/static/{viewer_filename}"

    r.publish(f"render:{job_id}", json.dumps({"event": "part_done", "part_entry": part_entry}))

def process_stream_task(task):
    """Processes a streaming render task and publishes SSE progress events."""
    job_id = task['job_id']
    engine = task['engine']
    part = task['part']
    payload = task['payload']
    scad_path = task['scad_path']
    output_path = task['output_path']
    export_format = task['export_format']
    i = task['part_index']
    num_parts = task['num_parts']
    part_base = task['part_base']
    part_weight = task['part_weight']

    project_slug = payload['project_slug']
    params = payload['params']
    mode_map = payload['mode_map']
    manifest = get_manifest(project_slug)

    logger.info(f"Worker streaming render for part {part} using {engine}")

    if engine == "cadquery":
        cp_copy = params.copy()
        cp_copy["target_part"] = part
        cmd = build_cadquery_command(output_path, scad_path, cp_copy, export_format)
        stream_gen = stream_cadquery_render(cmd, part, part_base, part_weight, i, num_parts, scad_path=scad_path)
    elif engine == "implicit":
        config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
        stream_gen = stream_implicit_render(output_path, config, params, part, part_base, part_weight, i, num_parts)
    else:
        render_mode = mode_map.get(part, 0)
        cmd = build_openscad_command(output_path, scad_path, params, render_mode)
        stream_gen = stream_openscad_render(cmd, part, part_base, part_weight, i, num_parts, scad_path=scad_path)

    for event_data in stream_gen:
        # Pass stream events directly to PubSub
        r.publish(f"render:{job_id}", event_data)
        try:
            event = json.loads(event_data)
            if event.get('event') == 'part_done':
                # Finalize conversion on part_done
                output_filename = os.path.basename(output_path)
                actual_format = output_filename.rsplit('.', 1)[-1]
                serve_path, serve_filename, viewer_filename = _post_render_convert(
                    output_path, output_filename, part, payload['stl_prefix'], actual_format, export_format
                )
                try:
                    size_bytes = os.path.getsize(serve_path)
                except OSError:
                    size_bytes = None
                render_cache.put(
                    project_slug, payload['scad_filename'], params, part, export_format,
                    serve_path, size_bytes, scad_content_hash=payload.get('scad_content_hash')
                )
                part_entry = {"type": part, "url": f"/static/{serve_filename}", "size_bytes": size_bytes}
                if viewer_filename:
                    part_entry["viewer_url"] = f"/static/{viewer_filename}"
                
                # Publish the fully baked part info
                r.publish(f"render:{job_id}:final", json.dumps(part_entry))
        except Exception as e:
            logger.error(f"Error parsing stream event: {e}")

def run_worker():
    logger.info("Render worker listening on queue 'yantra_render_queue'")
    while True:
        try:
            _, message = r.blpop("yantra_render_queue", timeout=5)
            if message:
                task = json.loads(message)
                if task.get('stream'):
                    process_stream_task(task)
                else:
                    process_sync_task(task)
        except TypeError:
            pass  # Timeout
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_worker()
