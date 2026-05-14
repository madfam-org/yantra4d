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
from services.engine import render_orchestrator
from services.engine.openscad import build_openscad_command, run_render as run_openscad_render, stream_render as stream_openscad_render
from services.engine.cadquery_engine import build_cadquery_command, run_render as run_cadquery_render, stream_render as stream_cadquery_render
from services.core.implicit_engine import run_render as run_implicit_render, stream_render as stream_implicit_render
from services.engine.render_cache import render_cache
from services.engine.format_converter import convert_mesh, stl_to_glb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

RENDER_QUEUE = getattr(render_orchestrator, "RENDER_QUEUE", "yantra_render_queue")
ACTIVE_RENDER_JOBS_KEY = getattr(render_orchestrator, "ACTIVE_RENDER_JOBS_KEY", "yantra_render_active_jobs")
ACTIVE_RENDER_META_PREFIX = getattr(render_orchestrator, "ACTIVE_RENDER_META_PREFIX", "yantra_render_job_meta:")
CANCEL_ALL_KEY = getattr(render_orchestrator, "CANCEL_ALL_KEY", "yantra_render_cancel_all")
CANCEL_JOB_PREFIX = getattr(render_orchestrator, "CANCEL_JOB_PREFIX", "yantra_render_cancel_job:")
ACTIVE_JOB_META_TTL = getattr(render_orchestrator, "ACTIVE_JOB_META_TTL", 300)
CANCEL_TTL_SECONDS = getattr(render_orchestrator, "CANCEL_TTL_SECONDS", 120)

STATIC_FOLDER = str(Config.STATIC_DIR)


def _is_cancelled(job_id: str) -> bool:
    try:
        if r.get(CANCEL_ALL_KEY):
            return True
        return bool(r.get(f"{CANCEL_JOB_PREFIX}{job_id}"))
    except Exception:
        logger.debug("Failed to read cancel flag for job %s", job_id, exc_info=True)
        return False


def _set_active_job(job_id: str, part: str, engine: str) -> None:
    """Track an active job for cancellation and observability."""
    meta = {
        "job_id": job_id,
        "part": part,
        "engine": engine,
        "started_at": int(time.time()),
    }
    r.sadd(ACTIVE_RENDER_JOBS_KEY, job_id)
    r.set(
        f"{ACTIVE_RENDER_META_PREFIX}{job_id}",
        json.dumps(meta),
        ex=ACTIVE_JOB_META_TTL,
    )


def _clear_active_job(job_id: str) -> None:
    """Remove active job tracking."""
    r.srem(ACTIVE_RENDER_JOBS_KEY, job_id)
    r.delete(f"{ACTIVE_RENDER_META_PREFIX}{job_id}")
    r.delete(f"{CANCEL_JOB_PREFIX}{job_id}")


def _publish_job_event(job_id: str, payload: dict, emit_final: bool = False) -> None:
    """Publish job progress/final events to both normal and final channels."""
    message = json.dumps(payload)
    r.publish(f"render:{job_id}", message)
    if emit_final:
        r.publish(f"render:{job_id}:final", message)


def _notify_cancelled(job_id: str, part: str) -> None:
    _publish_job_event(
        job_id,
        {
            "event": "error",
            "part": part or "",
            "error": "Render cancelled by user request",
        },
        emit_final=True,
    )


def _notify_error(job_id: str, part: str, error: str) -> None:
    _publish_job_event(
        job_id,
        {
            "event": "error",
            "part": part,
            "error": error,
        },
        emit_final=True,
    )


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

    if _is_cancelled(job_id):
        _notify_cancelled(job_id, part)
        return

    _set_active_job(job_id, part, engine)
    try:
    # Simple execution (no telemetry routing for worker sync simplicity)
        if engine == "cadquery":
            cp_copy = params.copy()
            cp_copy["target_part"] = part
            cmd = build_cadquery_command(output_path, scad_path, cp_copy, export_format)
            success, stderr = run_cadquery_render(
                cmd, scad_path=scad_path, is_cancelled=lambda: _is_cancelled(job_id)
            )
        elif engine == "implicit":
            config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
            success, stderr = run_implicit_render(output_path, config, params)
        else:
            render_mode = mode_map.get(part, 0)
            cmd = build_openscad_command(output_path, scad_path, params, render_mode)
            success, stderr = run_openscad_render(
                cmd, scad_path=scad_path, is_cancelled=lambda: _is_cancelled(job_id)
            )

        if _is_cancelled(job_id):
            _notify_cancelled(job_id, part)
            return

        if not success:
            _notify_error(job_id, part, stderr)
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
    except Exception as exc:
        logger.exception("Sync render failed for job %s part %s: %s", job_id, part, exc)
        if _is_cancelled(job_id):
            _notify_cancelled(job_id, part)
        else:
            _notify_error(job_id, part, str(exc))
    finally:
        _clear_active_job(job_id)

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
    if _is_cancelled(job_id):
        _notify_cancelled(job_id, part)
        return

    _set_active_job(job_id, part, engine)
    emitted_final = False
    try:
        if engine == "cadquery":
            cp_copy = params.copy()
            cp_copy["target_part"] = part
            cmd = build_cadquery_command(output_path, scad_path, cp_copy, export_format)
            stream_gen = stream_cadquery_render(
                cmd, part, part_base, part_weight, i, num_parts,
                scad_path=scad_path, is_cancelled=lambda: _is_cancelled(job_id)
            )
        elif engine == "implicit":
            config = manifest.project.get("hyperobject", {}).get("implicit_field", {})
            stream_gen = stream_implicit_render(output_path, config, params, part, part_base, part_weight, i, num_parts)
        else:
            render_mode = mode_map.get(part, 0)
            cmd = build_openscad_command(output_path, scad_path, params, render_mode)
            stream_gen = stream_openscad_render(
                cmd, part, part_base, part_weight, i, num_parts,
                scad_path=scad_path, is_cancelled=lambda: _is_cancelled(job_id)
            )

        for event_data in stream_gen:
            if _is_cancelled(job_id):
                _notify_cancelled(job_id, part)
                emitted_final = True
                break

            # Pass stream events directly to PubSub
            r.publish(f"render:{job_id}", event_data)
            try:
                event = json.loads(event_data)
                if event.get('event') == 'error':
                    error_message = event.get('error') or 'Render failed'
                    if error_message == 'Render cancelled by user request':
                        _notify_cancelled(job_id, part)
                    else:
                        _notify_error(job_id, part, error_message)
                    emitted_final = True
                    break

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
                    emitted_final = True
                    break
            except Exception as e:
                logger.error(f"Error parsing stream event: {e}")

        if not emitted_final:
            if _is_cancelled(job_id):
                _notify_cancelled(job_id, part)
            else:
                _notify_error(job_id, part, "Render stream ended without completion")
    except Exception as exc:
        logger.exception("Stream render failed for job %s part %s: %s", job_id, part, exc)
        if _is_cancelled(job_id):
            _notify_cancelled(job_id, part)
        else:
            _notify_error(job_id, part, str(exc))
    finally:
        _clear_active_job(job_id)

def run_worker():
    logger.info("Render worker listening on queue '%s'", RENDER_QUEUE)
    while True:
        try:
            _, message = r.blpop(RENDER_QUEUE, timeout=5)
            if message:
                try:
                    task = json.loads(message)
                    if task.get('stream'):
                        process_stream_task(task)
                    else:
                        process_sync_task(task)
                except json.JSONDecodeError:
                    logger.warning("Malformed task in render queue: %s", message)
        except TypeError:
            pass  # Timeout
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_worker()
