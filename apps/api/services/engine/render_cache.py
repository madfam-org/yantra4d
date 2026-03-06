"""
Render Result Cache
Two-level LRU cache for render results, keyed by parameter hash.
L1: In-memory OrderedDict (per-process, instant)
L2: Redis (shared across workers, survives restarts)
Avoids redundant compilations when the same parameters are requested again.
"""
import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict

import redis as redis_lib

logger = logging.getLogger(__name__)

DEFAULT_TTL = int(os.getenv("RENDER_CACHE_TTL", "3600"))
DEFAULT_MAX_ENTRIES = int(os.getenv("RENDER_CACHE_MAX_ENTRIES", "200"))
REDIS_TTL = int(os.getenv("RENDER_CACHE_REDIS_TTL", "86400"))
REDIS_URL = os.getenv("REDIS_URL")

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


class RenderCache:
    """Thread-safe two-level LRU cache for render output file paths."""

    def __init__(self, ttl: int = DEFAULT_TTL, max_entries: int = DEFAULT_MAX_ENTRIES):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max_entries = max_entries

    @staticmethod
    def _make_key(project: str, scad_file: str, params: dict, part: str, export_format: str, scad_content_hash: str | None = None) -> str:
        raw = json.dumps({
            "project": project,
            "scad_file": scad_file,
            "params": params,
            "part": part,
            "format": export_format,
            **({"scad_hash": scad_content_hash} if scad_content_hash else {}),
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _redis_get(self, key: str) -> dict | None:
        """Try fetching from Redis L2. Returns entry dict or None."""
        if not _redis_client:
            return None
        try:
            data = _redis_client.get(f"render:{key}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def _redis_put(self, key: str, entry: dict):
        """Write to Redis L2 (best-effort, non-blocking)."""
        if not _redis_client:
            return
        try:
            _redis_client.setex(
                f"render:{key}",
                REDIS_TTL,
                json.dumps({"path": entry["path"], "size_bytes": entry["size_bytes"], "ts": entry["ts"]})
            )
        except Exception:
            pass

    def get(self, project: str, scad_file: str, params: dict, part: str, export_format: str, scad_content_hash: str | None = None) -> dict | None:
        """Return cached entry if valid, else None. Checks L1 then L2."""
        key = self._make_key(project, scad_file, params, part, export_format, scad_content_hash)

        # L1: in-memory
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                if time.time() - entry["ts"] > self._ttl:
                    self._cache.pop(key, None)
                elif not os.path.isfile(entry["path"]):
                    self._cache.pop(key, None)
                else:
                    self._cache.move_to_end(key)
                    return entry

        # L2: Redis
        redis_entry = self._redis_get(key)
        if redis_entry and os.path.isfile(redis_entry.get("path", "")):
            # Promote to L1
            with self._lock:
                self._cache[key] = redis_entry
                self._cache.move_to_end(key)
                while len(self._cache) > self._max_entries:
                    self._cache.popitem(last=False)
            return redis_entry

        return None

    def put(self, project: str, scad_file: str, params: dict, part: str, export_format: str, path: str, size_bytes: int | None, scad_content_hash: str | None = None):
        key = self._make_key(project, scad_file, params, part, export_format, scad_content_hash)
        entry = {"path": path, "size_bytes": size_bytes, "ts": time.time()}

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
