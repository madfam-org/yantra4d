"""Tests for render cache service.

Entries record an artifact **store key**, not an absolute path, and validity is
"still in the store" rather than "still on this filesystem". Each cache here is
therefore built against a filesystem store rooted at the test's tmp_path, and
artifacts are addressed by file name.
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.engine.render_cache import RenderCache, entry_key
from services.storage import FilesystemArtifactStore


@pytest.fixture
def store(tmp_path):
    """A filesystem artifact store rooted at the test's own directory."""
    return FilesystemArtifactStore(tmp_path)


class TestRenderCache:
    def test_put_and_get(self, tmp_path, store):
        cache = RenderCache(store=store)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00" * 10)
        cache.put("proj", "main.scad", {"w": 10}, "main", "stl", f.name, 10)
        result = cache.get("proj", "main.scad", {"w": 10}, "main", "stl")
        assert result is not None
        assert result["size_bytes"] == 10

    def test_miss(self, store):
        cache = RenderCache(store=store)
        assert cache.get("proj", "main.scad", {}, "main", "stl") is None

    def test_different_params_miss(self, tmp_path, store):
        cache = RenderCache(store=store)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00")
        cache.put("proj", "main.scad", {"w": 10}, "main", "stl", f.name, 1)
        assert cache.get("proj", "main.scad", {"w": 20}, "main", "stl") is None

    def test_expired_entry(self, tmp_path, store):
        cache = RenderCache(ttl=0, store=store)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00")
        cache.put("proj", "main.scad", {}, "main", "stl", f.name, 1)
        time.sleep(0.01)
        assert cache.get("proj", "main.scad", {}, "main", "stl") is None

    def test_missing_artifact_evicted(self, tmp_path, store):
        """An entry whose artifact left the store is a miss, not a broken hit."""
        cache = RenderCache(store=store)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00")
        cache.put("proj", "main.scad", {}, "main", "stl", f.name, 1)
        f.unlink()
        assert cache.get("proj", "main.scad", {}, "main", "stl") is None

    def test_max_entries_eviction(self, tmp_path, store):
        cache = RenderCache(max_entries=2, store=store)
        for i in range(3):
            f = tmp_path / f"test{i}.stl"
            f.write_bytes(b"\x00")
            cache.put("proj", "main.scad", {"i": i}, "main", "stl", f.name, 1)
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

    def test_put_and_get_glb(self, tmp_path, store):
        cache = RenderCache(store=store)
        f = tmp_path / "test.glb"
        f.write_bytes(b"\x00" * 20)
        cache.put("proj", "main.scad", {"w": 10}, "main", "glb", f.name, 20)
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

    def test_content_hash_in_get_put(self, tmp_path, store):
        cache = RenderCache(store=store)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00" * 10)
        cache.put("proj", "main.scad", {"w": 10}, "main", "stl", f.name, 10, scad_content_hash="abc")
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
        with patch("services.engine.render_cache._redis_available", return_value=False):
            assert cache._redis_get("any_key") is None

    def test_redis_put_noop_when_no_client(self):
        cache = RenderCache()
        with patch("services.engine.render_cache._redis_available", return_value=False):
            # Should not raise
            cache._redis_put("any_key", {"key": "f.stl", "size_bytes": 1, "ts": 0})

    def test_redis_get_returns_entry_on_hit(self):
        cache = RenderCache()
        entry = {"key": "test.stl", "size_bytes": 42, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(entry).encode()
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache._redis_get("test_key")
        assert result is not None
        assert result["size_bytes"] == 42

    def test_redis_get_returns_none_on_miss(self):
        cache = RenderCache()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            assert cache._redis_get("missing_key") is None

    def test_redis_get_returns_none_on_exception(self):
        cache = RenderCache()
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("connection lost")
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            assert cache._redis_get("any_key") is None

    def test_redis_put_calls_setex(self):
        cache = RenderCache()
        entry = {"key": "test.stl", "size_bytes": 10, "ts": time.time()}
        mock_redis = MagicMock()
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            cache._redis_put("test_key", entry)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "render:test_key"

    def test_l2_promotes_to_l1_on_hit(self, tmp_path, store):
        """When L1 misses but L2 hits, entry should be promoted to L1."""
        cache = RenderCache(store=store)
        f = tmp_path / "test.stl"
        f.write_bytes(b"\x00" * 10)
        entry = {"key": f.name, "size_bytes": 10, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(entry).encode()
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache.get("proj", "main.scad", {"w": 10}, "main", "stl")
        assert result is not None
        assert result["size_bytes"] == 10
        # Verify it's now in L1 (no Redis needed for second get)
        with patch("services.engine.render_cache._redis_available", return_value=False):
            result2 = cache.get("proj", "main.scad", {"w": 10}, "main", "stl")
        assert result2 is not None

    def test_l2_skipped_when_artifact_missing(self, tmp_path, store):
        """L2 hit should be discarded if the artifact is no longer in the store."""
        cache = RenderCache(store=store)
        entry = {"key": "nonexistent_file.stl", "size_bytes": 10, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(entry).encode()
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache.get("proj", "main.scad", {}, "main", "stl")
        assert result is None

    def test_circuit_breaker_opens_after_failures(self):
        """After repeated Redis failures, circuit breaker should prevent further attempts."""
        import services.engine.render_cache as cache_mod
        # Reset circuit breaker state
        cache_mod._redis_failure_count = 0
        cache_mod._redis_circuit_open_until = 0.0

        # Simulate 3 failures
        for i in range(3):
            cache_mod._redis_fail("test_op", Exception(f"fail {i}"))

        # Circuit should now be open
        assert cache_mod._redis_circuit_open_until > time.time()
        assert not cache_mod._redis_available()

        # Reset for other tests
        cache_mod._redis_failure_count = 0
        cache_mod._redis_circuit_open_until = 0.0


class TestLegacyPathEntries:
    """Entries written before artifacts had keys must survive a rollout.

    Redis L2 outlives a deploy by up to RENDER_CACHE_REDIS_TTL (24h), so the
    first day after this change meets entries whose only locator is the old
    absolute `path`. Their basename is exactly the key the flat static
    directory used, so they keep hitting instead of turning the rollout into a
    cold cache.
    """

    def test_entry_key_prefers_the_key_field(self):
        assert entry_key({"key": "a.stl", "path": "/elsewhere/b.stl"}) == "a.stl"

    def test_entry_key_falls_back_to_a_legacy_path_basename(self):
        assert entry_key({"path": "/app/backend/static/proj_preview_body.stl"}) == (
            "proj_preview_body.stl"
        )

    def test_entry_key_is_none_for_nothing_usable(self):
        assert entry_key({}) is None
        assert entry_key(None) is None

    def test_a_legacy_l2_entry_still_hits(self, tmp_path, store):
        cache = RenderCache(store=store)
        artifact = tmp_path / "proj_preview_body.stl"
        artifact.write_bytes(b"solid\n")
        legacy = {"path": f"/app/backend/static/{artifact.name}", "size_bytes": 6, "ts": time.time()}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(legacy).encode()
        with patch("services.engine.render_cache._redis_available", return_value=True), \
             patch("services.engine.render_cache._redis_client", mock_redis):
            result = cache.get("proj", "main.scad", {}, "main", "stl")
        assert result is not None
        assert result["size_bytes"] == 6
