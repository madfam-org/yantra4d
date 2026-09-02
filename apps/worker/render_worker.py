"""
Yantra4D Render Worker.

Consumes CAD rendering tasks from Redis queue and executes them via OpenSCAD or CadQuery.
Publishes progress and completion events via Redis Pub/Sub back to the API.
"""
import json
import logging
import os
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
from services.storage import check_artifact_store_ready, get_artifact_store, publish_artifact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

RENDER_QUEUE = getattr(render_orchestrator, "RENDER_QUEUE", "yantra_render_queue")
ACTIVE_RENDER_JOBS_KEY = getattr(render_orchestrator, "ACTIVE_RENDER_JOBS_KEY", "yantra_render_active_jobs")
ACTIVE_RENDER_META_PREFIX = getattr(render_orchestrator, "ACTIVE_RENDER_META_PREFIX", "yantra_render_job_meta:")
CANCEL_ALL_KEY = getattr(render_orchestrator, "CANCEL_ALL_KEY", "yantra_render_cancel_all")
CANCEL_JOB_PREFIX = getattr(render_orchestrator, "CANCEL_JOB_PREFIX", "yantra_render_cancel_job:")
# The active-job LEASE, not just metadata: `ACTIVE_RENDER_JOBS_KEY` is a plain
# set with no expiry, so this key's TTL is the only thing that can end a job's
# membership when this process dies without reaching its `finally`. It is
# refreshed on every heartbeat tick for as long as the job is held, so a
# legitimately long render never expires out from under itself.
ACTIVE_JOB_META_TTL = getattr(render_orchestrator, "ACTIVE_JOB_META_TTL", 420)
CANCEL_TTL_SECONDS = getattr(render_orchestrator, "CANCEL_TTL_SECONDS", 120)
RENDER_WORKER_HEARTBEAT_KEY = getattr(
    render_orchestrator,
    "RENDER_WORKER_HEARTBEAT_KEY",
    "yantra_render_worker_heartbeat",
)
RENDER_WORKER_HEARTBEAT_TTL_SECONDS = getattr(
    render_orchestrator,
    "RENDER_WORKER_HEARTBEAT_TTL_SECONDS",
    60,
)
# Beat well inside the TTL, so a single missed tick — a Redis blip, a slow
# scheduler — cannot expire the key on an otherwise healthy worker.
HEARTBEAT_INTERVAL_SECONDS = max(5, RENDER_WORKER_HEARTBEAT_TTL_SECONDS // 3)

_stop_beating = threading.Event()

# Job ids this worker is currently executing. The heartbeat thread renews their
# leases; nothing else may hold a lease open. Guarded because the heartbeat
# thread reads it while the job loop writes it.
_held_jobs: set[str] = set()
_held_jobs_lock = threading.Lock()

# Where the render engines write. Engines are subprocesses, so a real local
# path is not negotiable: OpenSCAD and CadQuery emit files, not object keys.
# Under the default `fs` store this directory *is* the artifact store and a
# render lands at its final location with nothing to copy. Under an object
# store it is scratch space, and `_publish_part_artifacts` uploads from it.
STATIC_FOLDER = str(Config.STATIC_DIR)


def _publish_part_artifacts(paths, discard=()) -> dict[str, str]:
    """Publish freshly rendered files to the artifact store, keyed by local path.

    *paths* are the files the studio will actually be handed a URL for.
    *discard* are intermediates nobody links to — the pre-conversion mesh, the
    3MF the GLB was made from — which are worth cleaning up but not storing.

    Under the filesystem store this is a no-op per file: the artifact is
    already at its final path, so the default deployment writes exactly what it
    wrote before, right down to the inode and mtime, and nothing is deleted.
    Under an object store the directory is scratch on a volume with a hard
    sizeLimit and no GC in this container, so once a file is safely stored the
    local copy goes.

    A publish failure propagates. The caller then reports the render as failed
    rather than handing back a URL to an artifact that was never stored — the
    quiet "render succeeded, download 404s" failure this whole seam exists to
    prevent.
    """
    store = get_artifact_store()
    published: dict[str, str] = {}
    for path in paths:
        if not path or path in published:
            continue
        published[path] = publish_artifact(path, store=store)

    if store.local_root() is None:
        for path in (*published, *discard):
            if not path:
                continue
            try:
                os.unlink(path)
            except OSError:
                logger.debug("Could not remove staged artifact %s", path, exc_info=True)

    return published


def _viewer_path(viewer_filename: str | None) -> str | None:
    """Local path of the GLB companion `_post_render_convert` may have written."""
    return os.path.join(STATIC_FOLDER, viewer_filename) if viewer_filename else None


def _intermediates(output_path: str, serve_path: str) -> list[str]:
    """Scratch files a render leaves behind that nothing is ever linked to."""
    leftovers = []
    if serve_path != output_path:
        leftovers.append(output_path)
    if output_path.endswith(".stl"):
        leftovers.append(output_path.rsplit(".stl", 1)[0] + ".3mf")
    return leftovers


def _publish_heartbeat() -> None:
    """Publish worker heartbeat metadata for API readiness probes."""
    try:
        r.set(
            RENDER_WORKER_HEARTBEAT_KEY,
            str(int(time.time())),
            ex=RENDER_WORKER_HEARTBEAT_TTL_SECONDS,
        )
    except Exception:
        logger.debug("Failed to publish render worker heartbeat", exc_info=True)


def _heartbeat_loop() -> None:
    """Beat on a timer, independent of the job loop.

    The heartbeat used to be published only at the top of the blpop loop, so it
    stopped for the whole duration of a render — while the worker was doing
    exactly what it exists to do. A render legitimately runs to RENDER_TIMEOUT_S
    (300s) against a 60s TTL, and the API treats a heartbeat older than TTL*2 as
    a dead worker: it starts refusing renders, and with
    RENDER_WORKER_REQUIRED=true /api/health/ready returns 503 and the kubelet
    restarts the API pod — mid-render, because of the render.

    Beating from a daemon thread decouples liveness from job duration.
    """
    while not _stop_beating.wait(HEARTBEAT_INTERVAL_SECONDS):
        _publish_heartbeat()
        _refresh_active_job_leases()


def _refresh_active_job_leases() -> None:
    """Renew the lease on every job this worker is still executing.

    The lease already outlasts RENDER_TIMEOUT_S plus the post-render conversion,
    so this is not what keeps a normal render alive — it is what makes the
    expiry MEAN something. Without it the ceiling would be a guess about the
    slowest possible job; with it, a lease survives exactly as long as a worker
    is alive and holding the job, and not one tick longer. That is the property
    `render_orchestrator.prune_active_jobs` relies on.

    Never raises: a failed renew is at worst one job pruned early from the
    *count*, and the worker keeps rendering it either way.
    """
    with _held_jobs_lock:
        held = list(_held_jobs)
    for job_id in held:
        try:
            r.expire(f"{ACTIVE_RENDER_META_PREFIX}{job_id}", ACTIVE_JOB_META_TTL)
        except Exception:
            logger.debug("Failed to renew lease for job %s", job_id, exc_info=True)


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
    with _held_jobs_lock:
        _held_jobs.add(job_id)
    r.sadd(ACTIVE_RENDER_JOBS_KEY, job_id)
    r.set(
        f"{ACTIVE_RENDER_META_PREFIX}{job_id}",
        json.dumps(meta),
        ex=ACTIVE_JOB_META_TTL,
    )


def _clear_active_job(job_id: str) -> None:
    """Remove active job tracking.

    Stop renewing the lease FIRST. If the Redis calls below fail, the entry then
    expires on its own instead of being pinned open by a heartbeat thread that
    still thinks the job is running — the failure mode this whole lease exists
    to end.
    """
    with _held_jobs_lock:
        _held_jobs.discard(job_id)
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
        serve_path, _serve_filename, viewer_filename = _post_render_convert(
            output_path, output_filename, part, payload['stl_prefix'], actual_format, export_format
        )

        # Size is read before publishing: under an object store the local copy
        # is scratch and is gone by the time the cache entry is written.
        try:
            size_bytes = os.path.getsize(serve_path)
        except OSError:
            size_bytes = None

        viewer_path = _viewer_path(viewer_filename)
        published = _publish_part_artifacts(
            (serve_path, viewer_path), discard=_intermediates(output_path, serve_path)
        )
        serve_key = published[serve_path]
        viewer_key = published.get(viewer_path) if viewer_path else None

        render_cache.put(
            project_slug, payload['scad_filename'], params, part, export_format,
            serve_key, size_bytes, scad_content_hash=payload.get('scad_content_hash')
        )

        part_entry = {
            "type": part,
            "url": f"/static/{serve_key}",
            "size_bytes": size_bytes,
            "log": f"[{part}] {stderr}\n"
        }
        if viewer_key:
            part_entry["viewer_url"] = f"/static/{viewer_key}"

        final_payload = build_render_event(
            RENDER_EVENT_PART_DONE,
            part=part,
            type=part,
            url=f"/static/{serve_key}",
            size_bytes=size_bytes,
            log=f"[{part}] {stderr}\n",
        )
        if viewer_key:
            final_payload["viewer_url"] = f"/static/{viewer_key}"

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
                    serve_path, _serve_filename, viewer_filename = _post_render_convert(
                        output_path, output_filename, part, payload['stl_prefix'], actual_format, export_format
                    )
                    try:
                        size_bytes = os.path.getsize(serve_path)
                    except OSError:
                        size_bytes = None

                    viewer_path = _viewer_path(viewer_filename)
                    published = _publish_part_artifacts(
                        (serve_path, viewer_path),
                        discard=_intermediates(output_path, serve_path),
                    )
                    serve_key = published[serve_path]
                    viewer_key = published.get(viewer_path) if viewer_path else None

                    render_cache.put(
                        project_slug, payload['scad_filename'], params, part, export_format,
                        serve_key, size_bytes, scad_content_hash=payload.get('scad_content_hash')
                    )
                    part_entry = {
                        "type": part,
                        "url": f"/static/{serve_key}",
                        "size_bytes": size_bytes,
                    }
                    if viewer_key:
                        part_entry["viewer_url"] = f"/static/{viewer_key}"

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
            except Exception as e:  # one bad event must not kill the stream
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

def _reconcile_active_jobs_on_start() -> list[str]:
    """Drop active-job entries orphaned by a previous worker instance.

    Delegates to `render_orchestrator.reconcile_active_jobs` so the API and the
    worker agree on what "active" means — a second implementation here is how
    the two answers drift. Never raises: a worker that cannot reach Redis at
    startup must still come up and start beating.
    """
    try:
        dropped = render_orchestrator.reconcile_active_jobs()
    except Exception:
        logger.warning("Active render job reconciliation failed", exc_info=True)
        return []
    if dropped:
        logger.warning(
            "Startup reconciliation dropped %d orphaned active render job(s)",
            len(dropped),
        )
    return dropped


def run_worker():
    # Fail closed before the first BLPOP. A worker that cannot reach its
    # artifact store would render happily and publish nowhere, and every
    # resulting URL would 404 — so it must not start at all.
    check_artifact_store_ready()
    logger.info("Render worker listening on queue '%s'", RENDER_QUEUE)

    # Anything still in the active-job set belongs to the instance this one
    # replaced: this process holds nothing yet, and there is one render worker
    # replica. Clearing it here is what makes /api/health truthful immediately
    # after a rollout rather than one lease later — the production symptom was
    # "active jobs 1, queue depth 0" persisting across two rollouts.
    _reconcile_active_jobs_on_start()

    # Publish once before consuming anything, so the API sees the worker as
    # soon as it is up rather than one interval later.
    _publish_heartbeat()
    threading.Thread(
        target=_heartbeat_loop,
        name="render-worker-heartbeat",
        daemon=True,
    ).start()

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
        except Exception as e:  # the worker loop must survive anything
            logger.error(f"Worker loop error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_worker()
