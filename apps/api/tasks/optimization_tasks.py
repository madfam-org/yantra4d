"""
Optimization Task Queue
Background thread system for running long multi-generation topological evolution.
"""
import logging
import threading
import uuid
from services.simulation.optimizer import TopologyOptimizer

logger = logging.getLogger(__name__)

_OPT_JOB_STORE = {}

def queue_optimization(slug: str, original_params: dict) -> str:
    job_id = str(uuid.uuid4())
    _OPT_JOB_STORE[job_id] = {
        "status": "queued",
        "slug": slug,
        "progress": 0.0,
        "best_params": None,
        "logs": [],
        "error": None
    }
    
    # Spawn background thread mimicking Celery
    thread = threading.Thread(target=_run_optimizer_loop, args=(job_id, slug, original_params))
    thread.daemon = True
    thread.start()
    
    return job_id

def get_opt_status(job_id: str) -> dict | None:
    return _OPT_JOB_STORE.get(job_id)

def _run_optimizer_loop(job_id: str, slug: str, original_params: dict):
    _OPT_JOB_STORE[job_id]["status"] = "running"
    
    # Initialize the optimizer module
    opt = TopologyOptimizer(slug, original_params)
    
    # We will simulate 15 generations 
    TOTAL_GENS = 15
    
    try:
        for gen in range(1, TOTAL_GENS + 1):
            # Process one optimization step (generates mesh, tests physics, returns metrics)
            result = opt.step(gen)
            
            _OPT_JOB_STORE[job_id]["progress"] = (gen / float(TOTAL_GENS)) * 100.0
            
            log_msg = f"Gen {gen:02d} | Sigma: {result['current_sigma']:.1f} | Best: {result['best_sigma']:.1f}"
            _OPT_JOB_STORE[job_id]["logs"].append(log_msg)
            logger.info(f"[Task {job_id[:8]}] {log_msg}")

        _OPT_JOB_STORE[job_id]["status"] = "success"
        _OPT_JOB_STORE[job_id]["best_params"] = opt.best_params
        
    except Exception as e:
        logger.exception(f"Optimization task failed for {job_id}")
        _OPT_JOB_STORE[job_id]["status"] = "failed"
        _OPT_JOB_STORE[job_id]["error"] = str(e)
