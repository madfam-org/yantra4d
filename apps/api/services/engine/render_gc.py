"""
Render Artifact Garbage Collector
Periodically removes stale render output files from the static directory.

Runs as a daemon thread, started from the Flask app factory.
"""
import logging
import os
import threading
import time

from config import Config

logger = logging.getLogger(__name__)

# Configuration via environment
GC_INTERVAL_S = int(os.getenv("RENDER_GC_INTERVAL", "1800"))     # 30 minutes
GC_MAX_AGE_S = int(os.getenv("RENDER_GC_TTL", "86400"))          # 24 hours
GC_EXTENSIONS = {".stl", ".glb", ".gltf", ".3mf", ".off", ".obj", ".step"}


def _gc_sweep(static_dir: str, max_age: int) -> int:
    """Remove render artifacts older than max_age seconds.

    Returns number of files removed.
    """
    removed = 0
    now = time.time()
    try:
        for entry in os.scandir(static_dir):
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1].lower()
            if ext not in GC_EXTENSIONS:
                continue
            try:
                age = now - entry.stat().st_mtime
                if age > max_age:
                    os.unlink(entry.path)
                    removed += 1
            except OSError:
                pass
    except OSError as e:
        logger.error("Render GC scan failed: %s", e)
    return removed


def _gc_loop(static_dir: str, interval: int, max_age: int):
    """Background loop that runs GC sweeps at the configured interval."""
    while True:
        time.sleep(interval)
        try:
            count = _gc_sweep(static_dir, max_age)
            if count > 0:
                logger.info("Render GC: removed %d stale artifacts from %s", count, static_dir)
        except Exception:
            logger.exception("Render GC sweep error")


def start_gc():
    """Start the background GC thread. Safe to call multiple times (idempotent)."""
    static_dir = str(Config.STATIC_DIR)
    if not os.path.isdir(static_dir):
        logger.warning("Render GC: static directory %s does not exist, skipping", static_dir)
        return

    thread = threading.Thread(
        target=_gc_loop,
        args=(static_dir, GC_INTERVAL_S, GC_MAX_AGE_S),
        daemon=True,
        name="render-gc",
    )
    thread.start()
    logger.info("Render GC started: interval=%ds, max_age=%ds, dir=%s",
                GC_INTERVAL_S, GC_MAX_AGE_S, static_dir)
