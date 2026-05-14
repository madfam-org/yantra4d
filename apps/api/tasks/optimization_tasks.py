"""
Optimization Task Queue
Background thread system for running long multi-generation topological evolution.
"""
import logging
import threading
import time
import uuid

from services.simulation.optimizer import TopologyOptimizer

logger = logging.getLogger(__name__)

_OPT_JOB_STORE: dict[str, dict] = {}
_OPT_JOB_LOCK = threading.Lock()
_TOTAL_GENERATIONS = 15


def _new_job_record(slug: str, original_params: dict) -> dict:
    now = time.time()
    return {
        "status": "queued",
        "slug": slug,
        "progress": 0.0,
        "best_params": None,
        "current_params": original_params.copy(),
        "logs": [],
        "error": None,
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "duration_ms": None,
        "current_sigma": None,
        "best_iteration": None,
        "cancel_requested": False,
    }


def queue_optimization(slug: str, original_params: dict) -> str:
    job_id = str(uuid.uuid4())
    with _OPT_JOB_LOCK:
        _OPT_JOB_STORE[job_id] = _new_job_record(slug, original_params)

    # Spawn background thread mimicking Celery
    thread = threading.Thread(target=_run_optimizer_loop, args=(job_id, slug, original_params))
    thread.daemon = True
    thread.start()

    return job_id


def get_opt_status(job_id: str) -> dict | None:
    with _OPT_JOB_LOCK:
        record = _OPT_JOB_STORE.get(job_id)
        if record is None:
            return None
        return record.copy()


def _run_optimizer_loop(job_id: str, slug: str, original_params: dict):
    start = time.time()
    with _OPT_JOB_LOCK:
        state = _OPT_JOB_STORE.setdefault(job_id, _new_job_record(slug, original_params))
        state["status"] = "running"
        state["started_at"] = start

    opt = TopologyOptimizer(slug, original_params)

    try:
        for gen in range(1, _TOTAL_GENERATIONS + 1):
            with _OPT_JOB_LOCK:
                state = _OPT_JOB_STORE.get(job_id)
                if state is None:
                    return
                if state.get("cancel_requested"):
                    state["status"] = "cancelled"
                    break

            result = opt.step(gen)

            with _OPT_JOB_LOCK:
                state = _OPT_JOB_STORE.get(job_id)
                if state is None:
                    return

                state["progress"] = (gen / float(_TOTAL_GENERATIONS)) * 100.0
                state["current_sigma"] = result["current_sigma"]
                state["best_iteration"] = opt.best_iteration
                log_msg = (
                    f"Gen {gen:02d} | "
                    f"{result['metadata']['parameter']}={result['testing_params'][result['metadata']['parameter']]} "
                    f"-> sigma {result['current_sigma']:.3f}, best {result['best_sigma']:.3f}"
                )
                state["logs"].append(log_msg)
                state["best_params"] = opt.best_params
                state["current_params"] = result["testing_params"]
                logger.info(f"[Task {job_id[:8]}] {log_msg}")

            # Deterministic cadence for observability; no-op in terms of real work.
            time.sleep(0.05)

        with _OPT_JOB_LOCK:
            state = _OPT_JOB_STORE.get(job_id)
            if state is None:
                return

            if state.get("status") == "cancelled":
                state["error"] = "Optimization cancelled by operator"
            else:
                state["status"] = "success"
            state["best_params"] = opt.best_params
            state["finished_at"] = time.time()
            state["duration_ms"] = int((state["finished_at"] - state.get("started_at", start)) * 1000)

    except Exception as e:
        logger.exception(f"Optimization task failed for {job_id}")
        with _OPT_JOB_LOCK:
            state = _OPT_JOB_STORE.get(job_id)
            if state is None:
                return
            state["status"] = "failed"
            state["error"] = str(e)
            state["finished_at"] = time.time()
            state["duration_ms"] = int((state["finished_at"] - state.get("started_at", start)) * 1000)
