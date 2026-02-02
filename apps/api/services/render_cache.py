"""
Render Result Cache
In-memory LRU cache for OpenSCAD render results, keyed by parameter hash.
Avoids redundant compilations when the same parameters are requested again.
"""
import hashlib
import json
import os
import threading
import time
from collections import OrderedDict

DEFAULT_TTL = 3600  # 1 hour
DEFAULT_MAX_ENTRIES = 200


class RenderCache:
    """Thread-safe LRU cache for render output file paths."""

    def __init__(self, ttl: int = DEFAULT_TTL, max_entries: int = DEFAULT_MAX_ENTRIES):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max_entries = max_entries

    @staticmethod
    def _make_key(project: str, scad_file: str, params: dict, part: str, export_format: str) -> str:
        raw = json.dumps({
            "project": project,
            "scad_file": scad_file,
            "params": params,
            "part": part,
            "format": export_format,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, project: str, scad_file: str, params: dict, part: str, export_format: str) -> dict | None:
        """Return cached entry if valid, else None."""
        key = self._make_key(project, scad_file, params, part, export_format)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.time() - entry["ts"] > self._ttl:
                self._cache.pop(key, None)
                return None
            if not os.path.isfile(entry["path"]):
                self._cache.pop(key, None)
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry

    def put(self, project: str, scad_file: str, params: dict, part: str, export_format: str, path: str, size_bytes: int | None):
        key = self._make_key(project, scad_file, params, part, export_format)
        with self._lock:
            self._cache[key] = {"path": path, "size_bytes": size_bytes, "ts": time.time()}
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)


# Module-level singleton
render_cache = RenderCache()
