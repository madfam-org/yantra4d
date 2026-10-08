"""
Simulation Tasks
Background job execution for the PPF Contact Solver pipeline.

No physics solver ships with the API. A job can only be created once a solver
backend has been registered with ``configure_physics_solver``; until then
``queue_simulation`` raises ``PhysicsSolverUnavailable`` and the route answers
501. A job never reports frames that a solver did not return.
If migrating to a cloud cluster, decorate the worker with @celery.task(queue="gpu_tasks").
"""
import hashlib
import logging
import threading
import time
import uuid
from collections.abc import Callable

logger = logging.getLogger(__name__)

# A solver backend runs the generated PPF script for ``part_count`` parts and
# returns the frame sequence it computed (for example, URLs of exported frames).
PhysicsSolver = Callable[[str, int], list]

_SOLVER: PhysicsSolver | None = None

# In-memory job store (single process; jobs do not survive a restart).
_JOB_STORE: dict[str, dict] = {}
_JOB_LOCK = threading.Lock()


class PhysicsSolverUnavailable(RuntimeError):
    """No physics solver backend is configured on this server."""


def configure_physics_solver(solver: PhysicsSolver | None) -> None:
    """Register the backend that executes PPF scripts; ``None`` removes it."""
    global _SOLVER
    _SOLVER = solver


def physics_solver_available() -> bool:
    return _SOLVER is not None


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
    solver = _SOLVER
    if solver is None:
        raise PhysicsSolverUnavailable("No physics solver is configured on this server.")

    from services.simulation.script_generator import generate_ppf_script

    # The generated script is the solver's input.
    script = generate_ppf_script(slug, parts, kinematics)

    job_id = str(uuid.uuid4())
    with _JOB_LOCK:
        _JOB_STORE[job_id] = _new_job_record(slug)
    logger.info("Queued physics simulation %s for project %s.", job_id, slug)

    thread = threading.Thread(
        target=_run_worker_simulation, args=(job_id, slug, script, len(parts), solver)
    )
    thread.daemon = True
    thread.start()

    return job_id


def get_job_status(job_id: str) -> dict | None:
    with _JOB_LOCK:
        state = _JOB_STORE.get(job_id)
        if state is None:
            return None
        return state.copy()


def _run_worker_simulation(
    job_id: str, slug: str, built_script: str, part_count: int, solver: PhysicsSolver
):
    script_signature = hashlib.sha1(built_script.encode("utf-8")).hexdigest()[:12]
    with _JOB_LOCK:
        state = _JOB_STORE.setdefault(job_id, _new_job_record(slug))
        state["status"] = "running"
        state["started_at"] = time.time()
        state["metadata"] = {"parts": part_count, "script_signature": script_signature}
    logger.info("Physics simulation %s running, script_signature=%s", job_id, script_signature)

    try:
        frames = list(solver(built_script, part_count))
    except Exception as e:
        logger.exception("Physics solver failed for simulation %s.", job_id)
        with _JOB_LOCK:
            state = _JOB_STORE.get(job_id)
            if state is None:
                return
            state["status"] = "failed"
            state["error"] = str(e)
            state["finished_at"] = time.time()
            state["duration_ms"] = int((state["finished_at"] - state["started_at"]) * 1000)
        return

    with _JOB_LOCK:
        state = _JOB_STORE.get(job_id)
        if state is None:
            return
        state["status"] = "success"
        state["progress"] = 100.0
        state["frames"] = frames
        state["frames_generated"] = len(frames)
        state["finished_at"] = time.time()
        state["duration_ms"] = int((state["finished_at"] - state["started_at"]) * 1000)
    logger.info("Physics simulation %s finished with %d solver frames.", job_id, len(frames))
