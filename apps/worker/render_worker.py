"""
Yantra4D Render Worker.

Consumes CAD rendering tasks from Redis queue and executes them via OpenSCAD or CadQuery.
Publishes progress and completion events via Redis Pub/Sub back to the API.
"""
import json
import logging
import os
import signal
import socket
import sys
import threading
import time

import redis

BACKEND_PATH = os.environ.get("YANTRA4D_BACKEND_PATH", "/app/backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

# Use the same imports as the orchestrator to run the actual engines
from config import Config
from manifest import get_manifest
from services.core.implicit_engine import run_render as run_implicit_render
from services.core.implicit_engine import stream_render as stream_implicit_render
from services.engine import render_orchestrator
from services.engine.cadquery_engine import build_cadquery_command
from services.engine.cadquery_engine import run_render as run_cadquery_render
from services.engine.cadquery_engine import stream_render as stream_cadquery_render
from services.engine.format_converter import convert_mesh, stl_to_glb
from services.engine.graph_engine import prepare_graph_script
from services.engine.openscad import build_openscad_command
from services.engine.openscad import run_render as run_openscad_render
from services.engine.openscad import stream_render as stream_openscad_render
from services.engine.render_cache import render_cache
from services.engine.render_contract import (
    RENDER_EVENT_CANCELLED,
    RENDER_EVENT_ERROR,
    RENDER_EVENT_PART_DONE,
    build_render_event,
    render_channel_for_job,
    render_final_channel_for_job,
)

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
# Legacy single global heartbeat key. One key for the whole fleet, so it can
# only ever answer "is at least one worker alive", never "how many". Kept as a
# dual-write purely so an API still running pre-split code (a rollback) keeps
# seeing a live worker. Remove once every reader is on the per-worker keys.
RENDER_WORKER_HEARTBEAT_KEY = getattr(
    render_orchestrator,
    "RENDER_WORKER_HEARTBEAT_KEY",
    "yantra_render_worker_heartbeat",
)
# Per-worker heartbeat keys: `render_worker:heartbeat:<pod-name>`. One key per
# pod is what makes N replicas observable — the API counts live keys, and a
# wedged pod fails its own probe instead of hiding behind a healthy sibling
# that happens to be refreshing a shared key.
RENDER_WORKER_HEARTBEAT_PREFIX = getattr(
    render_orchestrator,
    "RENDER_WORKER_HEARTBEAT_PREFIX",
    "render_worker:heartbeat:",
)
RENDER_WORKER_HEARTBEAT_TTL_SECONDS = getattr(
    render_orchestrator,
    "RENDER_WORKER_HEARTBEAT_TTL_SECONDS",
    60,
)

STATIC_FOLDER = str(Config.STATIC_DIR)


def _resolve_worker_id() -> str:
    """Identify this worker pod.

    Kubernetes sets HOSTNAME to the pod name; RENDER_WORKER_ID is wired
    explicitly from the downward API so the identity does not depend on that
    implicit container behaviour. Both are absent outside a cluster.
    """
    for candidate in (os.environ.get("RENDER_WORKER_ID"), os.environ.get("HOSTNAME")):
        if candidate and candidate.strip():
            return candidate.strip()
    try:
        return socket.gethostname()
    except OSError:
        return f"worker-{os.getpid()}"


WORKER_ID = _resolve_worker_id()
WORKER_HEARTBEAT_KEY = f"{RENDER_WORKER_HEARTBEAT_PREFIX}{WORKER_ID}"

# Beat well inside the TTL so a single missed tick (a Redis blip, a slow
# scheduler) does not expire the key and fail an otherwise healthy probe.
HEARTBEAT_INTERVAL_SECONDS = max(5, RENDER_WORKER_HEARTBEAT_TTL_SECONDS // 3)

# Two separate events on purpose. _shutdown means "take no new work"; the
# heartbeat must keep beating right through the drain, because a draining
# worker is still alive and still finishing a render. Letting the heartbeat
# stop at SIGTERM would make the pod vanish from the fleet for up to the whole
# grace period — and if it were the last worker, the API would see zero
# workers, fail readiness under RENDER_WORKER_REQUIRED and restart itself while
# that render was still being written.
_shutdown = threading.Event()
_stop_beating = threading.Event()
_state_lock = threading.Lock()
_worker_state = {"state": "starting", "job_id": None}


def _set_worker_state(state: str, job_id: str | None = None) -> None:
    with _state_lock:
        _worker_state["state"] = state
        _worker_state["job_id"] = job_id


def _publish_heartbeat() -> None:
    """Publish this worker's heartbeat for the API and for its own probes.

    Writes two keys:
      * the per-worker key, carrying JSON state so the API can report a fleet;
      * the legacy global key, as a bare timestamp, for pre-split readers.
    """
    now = int(time.time())
    with _state_lock:
        payload = json.dumps({
            "ts": now,
            "worker_id": WORKER_ID,
            "state": _worker_state["state"],
            "job_id": _worker_state["job_id"],
        })
    try:
        pipe = r.pipeline()
        pipe.set(WORKER_HEARTBEAT_KEY, payload, ex=RENDER_WORKER_HEARTBEAT_TTL_SECONDS)
        pipe.set(
            RENDER_WORKER_HEARTBEAT_KEY,
            str(now),
            ex=RENDER_WORKER_HEARTBEAT_TTL_SECONDS,
        )
        pipe.execute()
    except Exception:
        logger.debug("Failed to publish render worker heartbeat", exc_info=True)


def _heartbeat_loop() -> None:
    """Beat on a timer, independent of the job loop.

    The heartbeat used to be published only at the top of the blpop loop, so a
    render longer than the TTL stopped the beat while the worker was doing
    exactly what it is for. The API reads that same beat with a TTL*2 staleness
    window and RENDER_WORKER_REQUIRED=true, so a long render could drive
    /api/health/ready to 503 and get the API pod restarted mid-render. Beating
    from a daemon thread decouples liveness from job duration and is what makes
    a liveness probe on this key safe to add.
    """
    while not _stop_beating.wait(HEARTBEAT_INTERVAL_SECONDS):
        _publish_heartbeat()


def _clear_heartbeat() -> None:
    """Drop this worker's key on a clean exit so the fleet count falls now."""
    try:
        r.delete(WORKER_HEARTBEAT_KEY)
    except Exception:
        logger.debug("Failed to clear render worker heartbeat", exc_info=True)


def _handle_shutdown(signum, _frame) -> None:
    """Stop taking new work; let the job in hand finish.

    The HPA deletes pods to scale down and does not consult the
    PodDisruptionBudget, so a worker can be told to stop at any moment. A job
    already popped off the Redis list exists nowhere else — killing the process
    mid-render loses it outright. Draining bounds that to the grace period.
    """
    logger.info("Received signal %s — draining after the current job", signum)
    _shutdown.set()
    with _state_lock:
        if _worker_state["state"] != "busy":
            _worker_state["state"] = "draining"


def _is_cancelled(job_id: str) -> bool:
    try:
        if r.get(CANCEL_ALL_KEY):
            return True
        return bool(r.get(f"{CANCEL_JOB_PREFIX}{job_id}"))
    except Exception:
        logger.debug("Failed to read cancel flag for job %s", job_id, exc_info=True)
        return False


def _set_active_job(job_id: str, part: str, engine: str, payload: dict) -> None:
    """Track an active job for cancellation and observability."""
    meta = {
        "job_id": job_id,
        "part": part,
        "engine": engine,
        "project_slug": payload.get("project_slug", ""),
        "mode": payload.get("mode", ""),
        "scad_filename": payload.get("scad_filename", ""),
        "request_id": payload.get("request_id", ""),
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
    r.publish(render_channel_for_job(job_id), message)
    if emit_final:
        r.publish(render_final_channel_for_job(job_id), message)


def _notify_cancelled(job_id: str, part: str) -> None:
    _publish_job_event(
        job_id,
        build_render_event(
            RENDER_EVENT_CANCELLED,
            part=part or "",
            message="Render cancelled by user request",
            reason="user_request",
        ),
        emit_final=True,
    )


def _notify_error(job_id: str, part: str, error: str) -> None:
    _publish_job_event(
        job_id,
        build_render_event(
            RENDER_EVENT_ERROR,
            part=part,
            error=error,
            message=error,
        ),
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
            if convert_mesh(threemf_path, glb_path) or stl_to_glb(output_path, glb_path):
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

    _set_active_job(job_id, part, engine, payload)
    try:
    # Simple execution (no telemetry routing for worker sync simplicity)
        if engine == "cadquery":
            cp_copy = params.copy()
            cp_copy["target_part"] = part
            cmd = build_cadquery_command(output_path, scad_path, cp_copy, export_format)
            success, stderr = run_cadquery_render(
                cmd, scad_path=scad_path, is_cancelled=lambda: _is_cancelled(job_id)
            )
        elif engine == "graph":
            # Transpile the graph document to a CadQuery script, then ride the
            # proven CadQuery sandbox path (part selection via target_part).
            script_path = prepare_graph_script(scad_path, manifest)
            cp_copy = params.copy()
            cp_copy["target_part"] = part
            cmd = build_cadquery_command(output_path, script_path, cp_copy, export_format)
            success, stderr = run_cadquery_render(
                cmd, scad_path=script_path, is_cancelled=lambda: _is_cancelled(job_id)
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

        final_payload = build_render_event(
            RENDER_EVENT_PART_DONE,
            part=part,
            type=part,
            url=f"/static/{serve_filename}",
            size_bytes=size_bytes,
            log=f"[{part}] {stderr}\n",
        )
        if viewer_filename:
            final_payload["viewer_url"] = f"/static/{viewer_filename}"

        _publish_job_event(job_id, final_payload, emit_final=True)
    except Exception as exc:
        logger.exception("Sync render failed for job %s part %s", job_id, part)
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

    _set_active_job(job_id, part, engine, payload)
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
        elif engine == "graph":
            script_path = prepare_graph_script(scad_path, manifest)
            cp_copy = params.copy()
            cp_copy["target_part"] = part
            cmd = build_cadquery_command(output_path, script_path, cp_copy, export_format)
            stream_gen = stream_cadquery_render(
                cmd, part, part_base, part_weight, i, num_parts,
                scad_path=script_path, is_cancelled=lambda: _is_cancelled(job_id)
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

            try:
                event = json.loads(event_data)
                _publish_job_event(job_id, event)
                if event.get("event") == RENDER_EVENT_ERROR or (
                    event.get("event") == "progress" and event.get("error")
                ):
                    error_message = event.get("error") or event.get("message") or "Render failed"
                    if "cancel" in str(error_message).lower():
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
                    part_entry = {
                        "type": part,
                        "url": f"/static/{serve_filename}",
                        "size_bytes": size_bytes,
                    }
                    if viewer_filename:
                        part_entry["viewer_url"] = f"/static/{viewer_filename}"

                    # Publish the fully baked part info
                    _publish_job_event(
                        job_id,
                        build_render_event(
                            RENDER_EVENT_PART_DONE,
                            part=part,
                            **part_entry,
                        ),
                        emit_final=True,
                    )
                    emitted_final = True
                    break
            except Exception as e:  # noqa: BLE001 — one bad event must not kill the stream
                logger.error(f"Error parsing stream event: {e}")

        if not emitted_final:
            if _is_cancelled(job_id):
                _notify_cancelled(job_id, part)
            else:
                _notify_error(job_id, part, "Render stream ended without completion")
    except Exception as exc:
        logger.exception("Stream render failed for job %s part %s", job_id, part)
        if _is_cancelled(job_id):
            _notify_cancelled(job_id, part)
        else:
            _notify_error(job_id, part, str(exc))
    finally:
        _clear_active_job(job_id)

def run_worker():
    logger.info(
        "Render worker %s listening on queue '%s' (heartbeat %s)",
        WORKER_ID,
        RENDER_QUEUE,
        WORKER_HEARTBEAT_KEY,
    )
    _set_worker_state("idle")
    _publish_heartbeat()

    heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        name="render-worker-heartbeat",
        daemon=True,
    )
    heartbeat_thread.start()

    try:
        while not _shutdown.is_set():
            try:
                _, message = r.blpop(RENDER_QUEUE, timeout=5)
                if message:
                    try:
                        task = json.loads(message)
                        _set_worker_state("busy", task.get("job_id"))
                        try:
                            if task.get('stream'):
                                process_stream_task(task)
                            else:
                                process_sync_task(task)
                        finally:
                            _set_worker_state("idle")
                    except json.JSONDecodeError:
                        logger.warning("Malformed task in render queue: %s", message)
            except TypeError:
                pass  # Timeout
            except Exception as e:  # noqa: BLE001 — the worker loop must survive anything
                logger.error(f"Worker loop error: {e}")
                _set_worker_state("idle")
                time.sleep(1)
    finally:
        # Only now stop beating: the job in hand is done and this worker is
        # genuinely leaving.
        _set_worker_state("stopping")
        _stop_beating.set()
        _clear_heartbeat()
        logger.info("Render worker %s stopped", WORKER_ID)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    run_worker()
