"""
Render Artifact Garbage Collector
Periodically removes stale render output files from the static directory.

Runs as a daemon thread, started from the Flask app factory.

The static directory is backed by an emptyDir volume with a hard `sizeLimit`
(see k8s/production/yantra4d-backend-deployment.yaml). When that limit is
exceeded the kubelet evicts the whole pod, so age-based expiry alone is not
enough: a burst of renders can fill the volume long before anything is old
enough to expire. The sweep therefore runs two passes — age first, then a
size pass that reclaims oldest-first down to a low-water mark.
"""
import logging
import os
import threading
import time

from config import Config

logger = logging.getLogger(__name__)

# Configuration via environment
GC_INTERVAL_S = int(os.getenv("RENDER_GC_INTERVAL", "300"))      # 5 minutes
GC_MAX_AGE_S = int(os.getenv("RENDER_GC_TTL", "86400"))          # 24 hours
GC_EXTENSIONS = {".stl", ".glb", ".gltf", ".3mf", ".off", ".obj", ".step"}

# Must match the emptyDir sizeLimit for the render-output volume. Wired through
# the deployment env so the two cannot drift apart silently.
VOLUME_LIMIT_BYTES = int(os.getenv("RENDER_VOLUME_LIMIT_BYTES", str(512 * 1024 * 1024)))
# Reclaim once usage crosses HIGH_WATER, down to LOW_WATER.
HIGH_WATER = float(os.getenv("RENDER_GC_HIGH_WATER", "0.75"))
LOW_WATER = float(os.getenv("RENDER_GC_LOW_WATER", "0.60"))


def volume_usage(static_dir: str | None = None) -> tuple[int, int]:
    """Return (bytes_used, bytes_limit) for the render output volume.

    Counts every file in the directory, not just collectable artifacts, because
    the kubelet's sizeLimit accounting counts everything too.
    """
    static_dir = static_dir or str(Config.STATIC_DIR)
    used = 0
    try:
        for entry in os.scandir(static_dir):
            try:
                if entry.is_file(follow_symlinks=False):
                    used += entry.stat(follow_symlinks=False).st_size
            except OSError:
                pass
    except OSError as e:
        logger.error("Render GC usage scan failed: %s", e)
    return used, VOLUME_LIMIT_BYTES


def _collectable(static_dir: str) -> list[tuple[float, int, str]]:
    """Return (mtime, size, path) for every artifact eligible for collection."""
    out = []
    try:
        for entry in os.scandir(static_dir):
            if not entry.is_file(follow_symlinks=False):
                continue
            if os.path.splitext(entry.name)[1].lower() not in GC_EXTENSIONS:
                continue
            try:
                st = entry.stat(follow_symlinks=False)
                out.append((st.st_mtime, st.st_size, entry.path))
            except OSError:
                pass
    except OSError as e:
        logger.error("Render GC scan failed: %s", e)
    return out


def _gc_sweep(static_dir: str, max_age: int) -> int:
    """Expire artifacts older than max_age, then reclaim by size if still over
    the high-water mark.

    Returns number of files removed.
    """
    removed = 0
    now = time.time()

    # Pass 1 — age expiry.
    survivors: list[tuple[float, int, str]] = []
    for mtime, size, path in _collectable(static_dir):
        if now - mtime > max_age:
            try:
                os.unlink(path)
                removed += 1
                continue
            except OSError:
                pass
        survivors.append((mtime, size, path))

    # Pass 2 — size reclamation. The age pass can leave the volume full of
    # artifacts that are new but numerous; without this the kubelet evicts us.
    used, limit = volume_usage(static_dir)
    if limit <= 0 or used <= limit * HIGH_WATER:
        return removed

    target = limit * LOW_WATER
    logger.warning(
        "Render GC: volume at %.1f%% of %dMiB limit, reclaiming to %.0f%%",
        (used / limit) * 100, limit // (1024 * 1024), LOW_WATER * 100,
    )
    for _mtime, size, path in sorted(survivors):  # oldest first
        if used <= target:
            break
        try:
            os.unlink(path)
            used -= size
            removed += 1
        except OSError:
            pass

    if used > target:
        logger.error(
            "Render GC: could not reclaim below target; %dMiB still in use and "
            "no further collectable artifacts remain",
            used // (1024 * 1024),
        )
    return removed


def _gc_loop(static_dir: str, interval: int, max_age: int):
    """Background loop that runs GC sweeps at the configured interval."""
    while True:
        time.sleep(interval)
        try:
            count = _gc_sweep(static_dir, max_age)
            if count > 0:
                logger.info("Render GC: removed %d artifacts from %s", count, static_dir)
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
    logger.info(
        "Render GC started: interval=%ds, max_age=%ds, limit=%dMiB, "
        "high_water=%.0f%%, low_water=%.0f%%, dir=%s",
        GC_INTERVAL_S, GC_MAX_AGE_S, VOLUME_LIMIT_BYTES // (1024 * 1024),
        HIGH_WATER * 100, LOW_WATER * 100, static_dir,
    )
