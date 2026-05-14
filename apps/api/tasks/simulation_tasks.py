"""
Simulation Tasks
Background job execution for the PPF Contact Solver pipeline.
If migrating to full cloud cluster, decorate these with @celery.task(queue="gpu_tasks").
"""
import hashlib
import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)

# In-memory distributed task mimic
_JOB_STORE: dict[str, dict] = {}
_JOB_LOCK = threading.Lock()
_TOTAL_FRAMES = 100
_FRAME_DELAY = 0.03


def _new_job_record(slug: str) -> dict:
    now = time.time()
    return {
        "status": "queued",
        "slug": slug,
        "frames": [],
        "progress": 0.0,
        "error": None,
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "duration_ms": None,
        "metadata": None,
        "frames_generated": 0,
    }


def queue_simulation(slug: str, parts: list, kinematics: dict) -> str:
    from services.simulation.script_generator import generate_ppf_script

    job_id = str(uuid.uuid4())
    with _JOB_LOCK:
        _JOB_STORE[job_id] = _new_job_record(slug)

    # Pre-compile the GPU instruction script
    script = generate_ppf_script(slug, parts, kinematics)
    logger.info(f"Queued physics simulation {job_id} for project {slug}.")

    thread = threading.Thread(target=_run_worker_simulation, args=(job_id, slug, script, len(parts)))
    thread.daemon = True
    thread.start()

    return job_id


def get_job_status(job_id: str) -> dict | None:
    with _JOB_LOCK:
        state = _JOB_STORE.get(job_id)
        if state is None:
            return None
        return state.copy()


def _run_worker_simulation(job_id: str, slug: str, built_script: str, part_count: int = 0):
    logger.info(f"Worker claimed physics simulation {job_id}")

    with _JOB_LOCK:
        state = _JOB_STORE.setdefault(job_id, _new_job_record(slug))
        state["status"] = "running"
        state["started_at"] = time.time()
        state["metadata"] = {
            "parts": part_count,
            "frame_count": _TOTAL_FRAMES,
            "frame_delay_s": _FRAME_DELAY,
        }

    script_signature = hashlib.sha1(built_script.encode("utf-8")).hexdigest()[:12]
    logger.info("Physics simulation %s script_signature=%s", job_id, script_signature)

    try:
        frames = []
        # Simulate ~3 seconds of GPU compute generating 100 frames
        for i in range(1, _TOTAL_FRAMES + 1):
            time.sleep(_FRAME_DELAY)
            with _JOB_LOCK:
                state = _JOB_STORE.get(job_id)
                if state is None:
                    return
                state["progress"] = (i / float(_TOTAL_FRAMES)) * 100.0

            frames.append(True)

        with _JOB_LOCK:
            state = _JOB_STORE.get(job_id)
            if state is None:
                return
            state["status"] = "success"
            state["frames"] = frames
            state["frames_generated"] = len(frames)
            state["finished_at"] = time.time()
            state["duration_ms"] = int((state["finished_at"] - state["started_at"]) * 1000)
            metadata = state.get("metadata") or {}
            metadata["script_signature"] = script_signature
            state["metadata"] = metadata
        logger.info(f"Simulation Job {job_id} successfully baked 100 physics frames.")

    except Exception as e:
        logger.exception("Simulation crashed at solver level.")
        with _JOB_LOCK:
            state = _JOB_STORE.get(job_id)
            if state is None:
                return
            state["status"] = "failed"
            state["error"] = str(e)
            if state.get("started_at"):
                state["duration_ms"] = int((time.time() - state["started_at"]) * 1000)
            else:
                state["duration_ms"] = 0
            state["finished_at"] = time.time()
