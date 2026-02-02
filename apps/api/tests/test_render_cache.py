"""Tests for render cache service."""
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from services.render_cache import RenderCache


class TestRenderCache:
    def test_put_and_get(self, tmp_path):
        cache = RenderCache()
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00" * 10)
        cache.put("proj", "main.scad", {"w": 10}, "main", "stl", str(f), 10)
        result = cache.get("proj", "main.scad", {"w": 10}, "main", "stl")
        assert result is not None
        assert result["size_bytes"] == 10

    def test_miss(self):
        cache = RenderCache()
        assert cache.get("proj", "main.scad", {}, "main", "stl") is None

    def test_different_params_miss(self, tmp_path):
        cache = RenderCache()
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00")
        cache.put("proj", "main.scad", {"w": 10}, "main", "stl", str(f), 1)
        assert cache.get("proj", "main.scad", {"w": 20}, "main", "stl") is None

    def test_expired_entry(self, tmp_path):
        cache = RenderCache(ttl=0)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00")
        cache.put("proj", "main.scad", {}, "main", "stl", str(f), 1)
        time.sleep(0.01)
        assert cache.get("proj", "main.scad", {}, "main", "stl") is None

    def test_missing_file_evicted(self, tmp_path):
        cache = RenderCache()
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00")
        cache.put("proj", "main.scad", {}, "main", "stl", str(f), 1)
        f.unlink()
        assert cache.get("proj", "main.scad", {}, "main", "stl") is None

    def test_max_entries_eviction(self, tmp_path):
        cache = RenderCache(max_entries=2)
        for i in range(3):
            f = tmp_path / f"test{i}.stl"
            f.write_bytes(b"\x00")
            cache.put("proj", "main.scad", {"i": i}, "main", "stl", str(f), 1)
        # First entry should be evicted
        assert cache.get("proj", "main.scad", {"i": 0}, "main", "stl") is None
        assert cache.get("proj", "main.scad", {"i": 2}, "main", "stl") is not None

    def test_key_deterministic(self):
        key1 = RenderCache._make_key("p", "f.scad", {"a": 1, "b": 2}, "main", "stl")
        key2 = RenderCache._make_key("p", "f.scad", {"b": 2, "a": 1}, "main", "stl")
        assert key1 == key2

    def test_different_format_different_key(self):
        key1 = RenderCache._make_key("p", "f.scad", {}, "main", "stl")
        key2 = RenderCache._make_key("p", "f.scad", {}, "main", "3mf")
        assert key1 != key2
