"""Cache-integrity tests for backend-aware render cache keys.

Manifold and CGAL are different geometry kernels; identical parameters can yield
different tessellations. If the cache key ignored which one produced an artifact,
a cache filled under CGAL would be served to a Manifold process and vice versa —
silently interleaving two kernels' output. These tests pin that separation.
"""
from unittest.mock import patch

from services.engine.render_cache import RenderCache

ARGS = ("proj", "f.scad", {"size": 10}, "main", "stl")


def _key_with_signature(signature: str) -> str:
    with patch.object(RenderCache, "_engine_signature", return_value=signature):
        return RenderCache._make_key(*ARGS)


class TestBackendPartitionsTheCache:
    def test_manifold_and_cgal_keys_differ(self):
        assert _key_with_signature("Manifold|v2026.02.13") != _key_with_signature(
            "CGAL|v2026.02.13"
        )

    def test_openscad_version_bump_partitions_the_cache(self):
        # A kernel upgrade can change tessellation too; age the old entries out
        # rather than serve them as if nothing changed.
        assert _key_with_signature("Manifold|v2026.02.13") != _key_with_signature(
            "Manifold|v2027.01.01"
        )

    def test_same_backend_same_params_is_stable(self):
        assert _key_with_signature("Manifold|v1") == _key_with_signature("Manifold|v1")

    def test_params_still_discriminate_within_one_backend(self):
        with patch.object(RenderCache, "_engine_signature", return_value="Manifold|v1"):
            k1 = RenderCache._make_key("proj", "f.scad", {"size": 10}, "main", "stl")
            k2 = RenderCache._make_key("proj", "f.scad", {"size": 20}, "main", "stl")
        assert k1 != k2


class TestSignatureDegradesSafely:
    def test_probe_failure_yields_a_shared_namespace_not_an_error(self):
        # Keying must never be the thing that breaks a render.
        with patch(
            "services.engine.openscad.backend_cache_signature",
            side_effect=RuntimeError("probe exploded"),
        ):
            assert RenderCache._engine_signature() == "unknown"

    def test_signature_is_folded_into_the_key(self):
        with patch.object(RenderCache, "_engine_signature", return_value="unknown"):
            unknown = RenderCache._make_key(*ARGS)
        assert unknown != _key_with_signature("Manifold|v1")


class TestEndToEndCacheBehaviour:
    def test_entry_stored_under_one_backend_is_not_served_to_another(self, tmp_path):
        artifact = tmp_path / "part.stl"
        artifact.write_bytes(b"solid\n")
        cache = RenderCache()

        with patch.object(RenderCache, "_engine_signature", return_value="CGAL|v1"):
            cache.put(*ARGS, str(artifact), 6)
            assert cache.get(*ARGS) is not None  # same backend: hit

        with patch.object(RenderCache, "_engine_signature", return_value="Manifold|v1"):
            assert cache.get(*ARGS) is None  # other backend: miss, not a wrong hit
