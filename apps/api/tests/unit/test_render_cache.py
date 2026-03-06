"""Tests for render cache service."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


sys.path.insert(0, str(Path(__file__).parent.parent))

from services.engine.render_cache import RenderCache


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

    def test_glb_format_different_from_stl(self):
        key_stl = RenderCache._make_key("p", "f.scad", {}, "main", "stl")
        key_glb = RenderCache._make_key("p", "f.scad", {}, "main", "glb")
        assert key_stl != key_glb

    def test_put_and_get_glb(self, tmp_path):
        cache = RenderCache()
        f = tmp_path / "test.glb"
        f.write_bytes(b"\x00" * 20)
        cache.put("proj", "main.scad", {"w": 10}, "main", "glb", str(f), 20)
        result = cache.get("proj", "main.scad", {"w": 10}, "main", "glb")
        assert result is not None
        assert result["size_bytes"] == 20

    def test_different_content_hash_different_key(self):
        key1 = RenderCache._make_key("p", "f.scad", {}, "main", "stl", "abc123")
        key2 = RenderCache._make_key("p", "f.scad", {}, "main", "stl", "def456")
        assert key1 != key2

    def test_none_hash_backward_compat(self):
        key_no_hash = RenderCache._make_key("p", "f.scad", {}, "main", "stl", None)
        key_old = RenderCache._make_key("p", "f.scad", {}, "main", "stl")
        assert key_no_hash == key_old

    def test_content_hash_in_get_put(self, tmp_path):
        cache = RenderCache()
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00" * 10)
        cache.put("proj", "main.scad", {"w": 10}, "main", "stl", str(f), 10, scad_content_hash="abc")
        # Same hash -> hit
        result = cache.get("proj", "main.scad", {"w": 10}, "main", "stl", scad_content_hash="abc")
        assert result is not None
        # Different hash -> miss
        result = cache.get("proj", "main.scad", {"w": 10}, "main", "stl", scad_content_hash="def")
        assert result is None


class TestRenderCacheRedisL2:
    """Tests for Redis L2 cache layer (mocked — no live Redis required)."""

    def test_redis_get_returns_none_when_no_client(self):
        cache = RenderCache()
        with patch("services.engine.render_cache._redis_client", None):
            assert cache._redis_get("any_key") is None

    def test_redis_put_noop_when_no_client(self):
        cache = RenderCache()
        with patch("services.engine.render_cache._redis_client", None):
            # Should not raise
            cache._redis_put("any_key", {"path": "/f", "size_bytes": 1, "ts": 0})

    def test_redis_get_returns_entry_on_hit(self):
        cache = RenderCache()
        entry = {"path": "/tmp/test.stl", "size_bytes": 42, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(entry).encode()
        with patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache._redis_get("test_key")
        assert result is not None
        assert result["size_bytes"] == 42

    def test_redis_get_returns_none_on_miss(self):
        cache = RenderCache()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        with patch("services.engine.render_cache._redis_client", mock_redis):
            assert cache._redis_get("missing_key") is None

    def test_redis_get_returns_none_on_exception(self):
        cache = RenderCache()
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("connection lost")
        with patch("services.engine.render_cache._redis_client", mock_redis):
            assert cache._redis_get("any_key") is None

    def test_redis_put_calls_setex(self):
        cache = RenderCache()
        entry = {"path": "/tmp/test.stl", "size_bytes": 10, "ts": time.time()}
        mock_redis = MagicMock()
        with patch("services.engine.render_cache._redis_client", mock_redis):
            cache._redis_put("test_key", entry)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "render:test_key"

    def test_l2_promotes_to_l1_on_hit(self, tmp_path):
        """When L1 misses but L2 hits, entry should be promoted to L1."""
        cache = RenderCache()
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00" * 10)
        entry = {"path": str(f), "size_bytes": 10, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(entry).encode()
        with patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache.get("proj", "main.scad", {"w": 10}, "main", "stl")
        assert result is not None
        assert result["size_bytes"] == 10
        # Verify it's now in L1 (no Redis needed for second get)
        with patch("services.engine.render_cache._redis_client", None):
            result2 = cache.get("proj", "main.scad", {"w": 10}, "main", "stl")
        assert result2 is not None

    def test_l2_skipped_when_file_missing(self, tmp_path):
        """L2 hit should be discarded if the file no longer exists on disk."""
        cache = RenderCache()
        entry = {"path": "/tmp/nonexistent_file.stl", "size_bytes": 10, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(entry).encode()
        with patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache.get("proj", "main.scad", {}, "main", "stl")
        assert result is None
