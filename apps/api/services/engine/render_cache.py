"""
Render Result Cache
Two-level LRU cache for render results, keyed by parameter hash.
L1: In-memory OrderedDict (per-process, instant)
L2: Redis (shared across workers, survives restarts)
Avoids redundant compilations when the same parameters are requested again.

An entry records the artifact's **store key** — the artifact-relative name that
appears in `/static/<key>` — not an absolute path. The two are the same string
under the filesystem store, but a path is only meaningful to a process that can
see that filesystem, and the whole point of the artifact store is that the API
and the render worker eventually will not. A key is meaningful to both.

Validation follows from that: an entry is a hit only if the artifact is still
*in the store*, which is `ArtifactStore.exists`, not `os.path.isfile`. An entry
whose key has since been collected — swept by the GC, expired by a bucket
lifecycle rule, or written before a store switch — is treated as a miss and the
part is rendered again. Nothing is ever served on the strength of a cache entry
alone.
"""
import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict

import redis as redis_lib

from utils.metrics import CACHE_HITS, CACHE_MISSES

logger = logging.getLogger(__name__)

DEFAULT_TTL = int(os.getenv("RENDER_CACHE_TTL", "3600"))
DEFAULT_MAX_ENTRIES = int(os.getenv("RENDER_CACHE_MAX_ENTRIES", "200"))
REDIS_TTL = int(os.getenv("RENDER_CACHE_REDIS_TTL", "86400"))
REDIS_URL = os.getenv("REDIS_URL")

# Redis circuit breaker state
_redis_failure_count = 0
_redis_circuit_open_until = 0.0
_CIRCUIT_THRESHOLD = 3
_CIRCUIT_COOLDOWN = 60.0

# Redis DB 2 (DB 0 = app default, DB 1 = rate limiter)
_redis_client = None
if REDIS_URL:
    try:
        _redis_client = redis_lib.from_url(REDIS_URL, db=2, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info("Render cache: Redis L2 connected (DB 2)")
    except Exception as e:
        logger.warning("Render cache: Redis L2 unavailable, falling back to L1-only: %s", e)
        _redis_client = None


def _redis_available() -> bool:
    """Check if Redis L2 should be attempted."""
    if not _redis_client:
        return False
    # Circuit is closed (Redis usable) once the cooldown window has elapsed.
    return time.time() >= _redis_circuit_open_until


def _redis_ok():
    """Reset circuit breaker on success."""
    global _redis_failure_count, _redis_circuit_open_until
    _redis_failure_count = 0
    _redis_circuit_open_until = 0.0


def _redis_fail(operation: str, error: Exception):
    """Record Redis failure, open circuit after threshold."""
    global _redis_failure_count, _redis_circuit_open_until
    _redis_failure_count += 1
    logger.warning("Render cache Redis %s failed (%d/%d): %s",
                   operation, _redis_failure_count, _CIRCUIT_THRESHOLD, error)
    if _redis_failure_count >= _CIRCUIT_THRESHOLD:
        _redis_circuit_open_until = time.time() + _CIRCUIT_COOLDOWN
        logger.error("Render cache Redis circuit breaker OPEN for %ds", int(_CIRCUIT_COOLDOWN))


def entry_key(entry: dict | None) -> str | None:
    """The store key an entry points at, tolerating pre-artifact-store entries.

    Redis L2 survives deploys, so the rollout of the artifact store meets
    entries whose only locator is the old absolute ``path``. Their basename is
    exactly the key the flat static directory used, so they keep working
    instead of turning the first minutes after a deploy into a cold cache.
    Removing this fallback is safe once RENDER_CACHE_REDIS_TTL (24h) has
    elapsed past the rollout.
    """
    if not isinstance(entry, dict):
        return None
    key = entry.get("key")
    if isinstance(key, str) and key:
        return key
    legacy_path = entry.get("path")
    if isinstance(legacy_path, str) and legacy_path:
        return os.path.basename(legacy_path)
    return None


class RenderCache:
    """Thread-safe two-level LRU cache for render artifact store keys."""

    def __init__(
        self,
        ttl: int = DEFAULT_TTL,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        store=None,
    ):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max_entries = max_entries
        self._store = store

    @property
    def store(self):
        """The artifact store entries are validated against.

        Resolved on every access rather than captured in ``__init__`` so the
        module-level singleton follows a store installed later in startup, and
        so a test can point one cache at a temporary directory.
        """
        if self._store is not None:
            return self._store
        from services.storage import get_artifact_store
        return get_artifact_store()

    def _stored(self, entry: dict | None) -> bool:
        """Whether the artifact an entry names is still in the store."""
        key = entry_key(entry)
        if not key:
            return False
        try:
            return self.store.exists(key)
        except Exception:
            # A store that cannot answer must not fail the render: degrade to a
            # miss and re-render, which is correct, just slower.
            logger.warning("Artifact store existence check failed for %r", key, exc_info=True)
            return False

    @staticmethod
    def _engine_signature() -> str:
        """Identity of the geometry evaluator that produces cached artifacts.

        CACHE INTEGRITY: OpenSCAD's Manifold and CGAL backends are different
        geometry kernels. For identical parameters they can emit different
        tessellations (differing vertex counts and ordering, and volumes that
        agree only to floating-point tolerance). If the key ignored which one
        ran, a cache populated under CGAL would be served to a process now
        running Manifold and vice versa — silently interleaving two kernels'
        output for what the user is told is one deterministic render. So the
        effective backend, plus the OpenSCAD version string, is folded into the
        key. Changing backend or upgrading OpenSCAD partitions the cache rather
        than corrupting it; stale entries simply age out on TTL.

        Imported lazily and defensively: the cache is also used by CadQuery,
        implicit and graph renders, and a probe failure must degrade to a
        single shared namespace, never break caching outright.
        """
        try:
            from services.engine.openscad import backend_cache_signature
            return backend_cache_signature()
        except Exception:
            logger.debug("Backend signature unavailable for cache key", exc_info=True)
            return "unknown"

    @classmethod
    def _make_key(cls, project: str, scad_file: str, params: dict, part: str, export_format: str, scad_content_hash: str | None = None) -> str:
        raw = json.dumps({
            "project": project,
            "scad_file": scad_file,
            "params": params,
            "part": part,
            "format": export_format,
            # See _engine_signature: keeps Manifold and CGAL outputs disjoint.
            "engine": cls._engine_signature(),
            **({"scad_hash": scad_content_hash} if scad_content_hash else {}),
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _redis_get(self, key: str) -> dict | None:
        """Try fetching from Redis L2. Returns entry dict or None."""
        if not _redis_available():
            return None
        try:
            data = _redis_client.get(f"render:{key}")
            if data:
                _redis_ok()
                return json.loads(data)
            _redis_ok()
        except Exception as e:
            _redis_fail("get", e)
        return None

    def _redis_put(self, key: str, entry: dict):
        """Write to Redis L2 (best-effort, non-blocking)."""
        if not _redis_available():
            return
        try:
            _redis_client.setex(
                f"render:{key}",
                REDIS_TTL,
                json.dumps({
                    "key": entry["key"],
                    "size_bytes": entry["size_bytes"],
                    "ts": entry["ts"],
                })
            )
            _redis_ok()
        except Exception as e:
            _redis_fail("put", e)

    def get(self, project: str, scad_file: str, params: dict, part: str, export_format: str, scad_content_hash: str | None = None) -> dict | None:
        """Return cached entry if valid, else None. Checks L1 then L2."""
        key = self._make_key(project, scad_file, params, part, export_format, scad_content_hash)

        # L1: in-memory
        with self._lock:
            entry = self._cache.get(key)
            expired = entry is not None and time.time() - entry["ts"] > self._ttl
        if entry is not None:
            # The store check is deliberately outside the lock: against an
            # object store it is a network round trip, and holding the cache
            # mutex across it would serialize every render in the process.
            if expired or not self._stored(entry):
                with self._lock:
                    self._cache.pop(key, None)
            else:
                with self._lock:
                    if key in self._cache:
                        self._cache.move_to_end(key)
                CACHE_HITS.inc()
                return entry

        # L2: Redis
        redis_entry = self._redis_get(key)
        if redis_entry and self._stored(redis_entry):
            # Promote to L1
            with self._lock:
                self._cache[key] = redis_entry
                self._cache.move_to_end(key)
                while len(self._cache) > self._max_entries:
                    self._cache.popitem(last=False)
            CACHE_HITS.inc()
            return redis_entry

        CACHE_MISSES.inc()
        return None

    def put(self, project: str, scad_file: str, params: dict, part: str, export_format: str, artifact_key: str, size_bytes: int | None, scad_content_hash: str | None = None):
        """Record that *artifact_key* satisfies this render.

        ``artifact_key`` is a store key (``ArtifactStore``), i.e. the same
        artifact-relative name that goes into the `/static/<key>` URL — never
        an absolute path, which would only mean something to a process sharing
        the producer's filesystem.
        """
        key = self._make_key(project, scad_file, params, part, export_format, scad_content_hash)
        entry = {"key": artifact_key, "size_bytes": size_bytes, "ts": time.time()}

        # L1
        with self._lock:
            self._cache[key] = entry
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)

        # L2
        self._redis_put(key, entry)


# Module-level singleton
render_cache = RenderCache()
