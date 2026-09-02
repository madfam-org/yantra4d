"""
Render Artifact Garbage Collector
Periodically removes stale render artifacts from the artifact store.

Runs as a daemon thread, started from the Flask app factory.

The GC used to walk ``Config.STATIC_DIR`` with ``os.scandir`` and unlink what
it found. That is only the same thing as "collect the render artifacts" while
the artifacts *are* files in that directory: point the deployment at an object
store and the same sweep sees an empty scratch directory, reports nothing to
do, and every render ever produced stays in the bucket forever. So the sweep
now lists and deletes through :class:`~services.storage.ArtifactStore`, and
both backends expire on exactly the same rule.

Two passes, and only the first is about the artifacts themselves:

**Age.** Anything older than ``RENDER_GC_TTL`` goes. Identical on both
backends.

**Size.** The static directory is an emptyDir with a hard `sizeLimit` (see
k8s/production/yantra4d-backend-deployment.yaml) and exceeding it gets the
whole pod evicted by the kubelet, so age expiry alone is not enough: a burst
of renders can fill the volume long before anything is old enough to expire.
This pass reclaims oldest-first down to a low-water mark. It is a property of
*that volume*, not of the store — with an object store there is no emptyDir
holding artifacts to protect, and `RENDER_VOLUME_LIMIT_BYTES` (512 MiB, the
volume's size) would be a nonsensical bucket quota to enforce. So the size
pass runs only for a filesystem-backed store; bucket capacity is the
operator's lifecycle policy, and the runbook says so.
"""
import logging
import os
import threading
import time

from config import Config
from services.storage import FilesystemArtifactStore, get_artifact_store

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


def gc_store(static_dir: str | None = None):
    """The store this sweep collects.

    With an object store there is one answer and it is the configured store.
    With a filesystem-backed one the GC collects *the directory it was started
    on*: that is what it has always done, it is what lets a caller (and the
    tests) sweep a directory that is not the process-wide static dir, and under
    the default deployment the two are the same directory anyway.
    """
    store = get_artifact_store()
    if store.local_root() is None:
        return store
    return FilesystemArtifactStore(static_dir or str(Config.STATIC_DIR))


def volume_usage(static_dir: str | None = None, store=None) -> tuple[int, int]:
    """Return (bytes_used, bytes_limit) for the render output volume.

    For a filesystem-backed store this counts every file in the directory, not
    just collectable artifacts, because the kubelet's sizeLimit accounting
    counts everything too — a stray `.3mf` intermediate or a core dump fills
    the volume just as well as a mesh does.

    For any other store there is no such volume; the reported usage is the size
    of what is actually stored, which is what the size pass is disabled on the
    strength of.
    """
    static_dir = static_dir or str(Config.STATIC_DIR)
    store = store or gc_store(static_dir)
    if store.local_root() is None:
        return sum(info.size for info in store.list()), VOLUME_LIMIT_BYTES

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


def _collectable(store) -> list[tuple[float, int, str]]:
    """Return (mtime, size, key) for every artifact eligible for collection."""
    out = []
    for info in store.list():
        name = info.key.rsplit("/", 1)[-1]
        if os.path.splitext(name)[1].lower() not in GC_EXTENSIONS:
            continue
        out.append((info.modified_at, info.size, info.key))
    return out


def _gc_sweep(static_dir: str, max_age: int, store=None) -> int:
    """Expire artifacts older than max_age, then reclaim by size if still over
    the high-water mark.

    Returns number of artifacts removed.
    """
    store = store or gc_store(static_dir)
    removed = 0
    now = time.time()

    # Pass 1 — age expiry. Store-driven, so it works identically whether the
    # artifact is a file on the volume or an object in a bucket.
    survivors: list[tuple[float, int, str]] = []
    for mtime, size, key in _collectable(store):
        if now - mtime > max_age and store.delete(key):
            removed += 1
            continue
        survivors.append((mtime, size, key))

    # Pass 2 — size reclamation, for the emptyDir only. The age pass can leave
    # the volume full of artifacts that are new but numerous; without this the
    # kubelet evicts us. A bucket has no such limit to defend (see the module
    # docstring), so this pass does not run there.
    if store.local_root() is None:
        return removed

    used, limit = volume_usage(static_dir, store=store)
    if limit <= 0 or used <= limit * HIGH_WATER:
        return removed

    target = limit * LOW_WATER
    logger.warning(
        "Render GC: volume at %.1f%% of %dMiB limit, reclaiming to %.0f%%",
        (used / limit) * 100, limit // (1024 * 1024), LOW_WATER * 100,
    )
    for _mtime, size, key in sorted(survivors):  # oldest first
        if used <= target:
            break
        if store.delete(key):
            used -= size
            removed += 1

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
            store = gc_store(static_dir)
            count = _gc_sweep(static_dir, max_age, store=store)
            if count > 0:
                logger.info("Render GC: removed %d artifacts from %s", count, store.describe())
        except Exception:
            logger.exception("Render GC sweep error")


def start_gc():
    """Start the background GC thread. Safe to call multiple times (idempotent)."""
    static_dir = str(Config.STATIC_DIR)
    store = gc_store(static_dir)
    if store.local_root() is not None and not os.path.isdir(static_dir):
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
        "high_water=%.0f%%, low_water=%.0f%%, store=%s",
        GC_INTERVAL_S, GC_MAX_AGE_S, VOLUME_LIMIT_BYTES // (1024 * 1024),
        HIGH_WATER * 100, LOW_WATER * 100, store.describe(),
    )
