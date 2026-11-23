"""Tessellation profiles (owner rulings M1-M3, 2026-11-22): who may ask, and what changes.

Design: docs/architecture/tessellation-profiles-and-mesh-gate.md. Pinned here, without
a CAD kernel:

  - ``print`` is the default and the only profile a public caller gets; ``preview`` is
    the models pipeline's, honoured only with ALLOW_PREVIEW_TESSELLATION on AND
    AUTH_ENABLED off (M3);
  - every print cache key, artifact name and runner command is exactly what it was
    before profiles existed, so introducing them invalidates nothing (M1);
  - a preview render gets its own cache key and artifact name, so it can never answer a
    print request (M3).

The byte-for-byte proof on a real kernel is tests/integration/test_tessellation_kernel.py.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from services.engine import tessellation
from services.engine.cadquery_engine import _job_from_cmd, build_cadquery_command
from services.engine.render_cache import RenderCache
from services.engine.tessellation import (
    PREVIEW,
    PRINT,
    TessellationRequestError,
    key_fields,
    preview_allowed,
    requested_profile,
)


@pytest.fixture
def pipeline(monkeypatch):
    """The prerender workflow's local API: the opt-in on, auth off."""
    monkeypatch.setattr(Config, "ALLOW_PREVIEW_TESSELLATION", True)
    monkeypatch.setattr(Config, "AUTH_ENABLED", False)


class TestProfiles:
    def test_print_is_cadquerys_own_export_defaults(self):
        """M1: print keeps today's numbers (0.1 relative, 0.1 rad) under its new name."""
        p = tessellation.profile(PRINT)
        assert (p.linear, p.angular, p.relative) == (0.1, 0.1, True)

    def test_preview_is_the_ruled_absolute_bound(self):
        """M2: 0.02 mm absolute, 0.35 rad."""
        p = tessellation.profile(PREVIEW)
        assert (p.linear, p.angular, p.relative) == (0.02, 0.35, False)

    def test_none_is_the_default_and_unknown_raises(self):
        assert tessellation.profile(None).name == PRINT
        with pytest.raises(ValueError, match="unknown tessellation profile"):
            tessellation.profile("draft")

    def test_print_numbers_match_the_installed_cadquery(self):
        """The recorded print numbers are the exporter's defaults, not a copy that drifts."""
        import inspect

        cq = pytest.importorskip("cadquery", reason="CadQuery kernel not installed")
        export = inspect.signature(cq.exporters.export).parameters
        export_stl = inspect.signature(cq.Shape.exportStl).parameters
        p = tessellation.profile(PRINT)
        assert export["tolerance"].default == p.linear
        assert export["angularTolerance"].default == p.angular
        assert export_stl["relative"].default is p.relative


class TestWhoMayAskForPreview:
    """M3: only the models pipeline, never a public API caller."""

    @pytest.mark.parametrize("data", [{}, {"tessellation": None}, {"tessellation": "print"}])
    def test_absent_or_print_is_print(self, data):
        assert requested_profile(data, "stl") == PRINT

    def test_public_caller_is_refused_preview(self):
        assert Config.ALLOW_PREVIEW_TESSELLATION is False
        with pytest.raises(TessellationRequestError) as err:
            requested_profile({"tessellation": "preview"}, "stl")
        assert err.value.status_code == 403
        assert err.value.error_code == "tessellation_not_allowed"

    def test_opt_in_is_inert_while_auth_is_enabled(self, monkeypatch):
        """The variable leaking into a real deployment widens nothing."""
        monkeypatch.setattr(Config, "ALLOW_PREVIEW_TESSELLATION", True)
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        assert preview_allowed() is False
        with pytest.raises(TessellationRequestError) as err:
            requested_profile({"tessellation": "preview"}, "stl")
        assert err.value.status_code == 403

    def test_models_pipeline_gets_preview(self, pipeline):
        assert preview_allowed() is True
        assert requested_profile({"tessellation": "preview"}, "stl") == PREVIEW

    @pytest.mark.parametrize("fmt", ["3mf", "glb", "step", "obj"])
    def test_preview_is_stl_only(self, pipeline, fmt):
        with pytest.raises(TessellationRequestError) as err:
            requested_profile({"tessellation": "preview"}, fmt)
        assert err.value.status_code == 400

    @pytest.mark.parametrize("value", ["draft", "PREVIEW", 1, ["preview"], {"name": "preview"}])
    def test_unknown_values_are_refused_not_rendered_as_print(self, pipeline, value):
        with pytest.raises(TessellationRequestError) as err:
            requested_profile({"tessellation": value}, "stl")
        assert err.value.status_code == 400
        assert err.value.error_code == "invalid_tessellation"


class TestCacheKey:
    ARGS = ("proj", "main.py", {"size": 10}, "body", "stl", "deadbeef")

    def test_print_key_is_the_key_from_before_profiles(self):
        """The key a print render had yesterday, recomputed from its documented fields."""
        expected = hashlib.sha256(json.dumps({
            "project": "proj", "scad_file": "main.py", "params": {"size": 10}, "part": "body",
            "format": "stl", "engine": RenderCache._engine_signature(),
            "revision": __import__("services.engine.render_revision", fromlist=["x"]).cache_revision(),
            "scad_hash": "deadbeef",
        }, sort_keys=True).encode()).hexdigest()
        assert RenderCache._make_key(*self.ARGS) == expected
        assert RenderCache._make_key(*self.ARGS, tessellation=PRINT) == expected
        assert RenderCache._make_key(*self.ARGS, tessellation=None) == expected

    def test_preview_key_is_disjoint_from_print(self):
        assert RenderCache._make_key(*self.ARGS, tessellation=PREVIEW) != RenderCache._make_key(*self.ARGS)

    def test_preview_entry_never_answers_a_print_lookup(self, tmp_path):
        from services.storage import FilesystemArtifactStore

        store = FilesystemArtifactStore(tmp_path)
        (tmp_path / "preview.stl").write_bytes(b"solid preview")
        cache = RenderCache(store=store)
        cache.put("proj", "main.py", {}, "body", "stl", "preview.stl", 13, tessellation=PREVIEW)
        assert cache.get("proj", "main.py", {}, "body", "stl", tessellation=PREVIEW)["key"] == "preview.stl"
        assert cache.get("proj", "main.py", {}, "body", "stl") is None
        assert cache.get("proj", "main.py", {}, "body", "stl", tessellation=PRINT) is None

    def test_key_fields(self):
        assert key_fields(None) == {}
        assert key_fields(PRINT) == {}
        assert key_fields(PREVIEW) == {"tessellation": PREVIEW}


class TestRunnerCommand:
    def test_print_command_is_the_six_element_command_from_before(self):
        before = build_cadquery_command("o.stl", "s.py", {"a": 1}, "stl")
        assert len(before) == 6
        assert build_cadquery_command("o.stl", "s.py", {"a": 1}, "stl", PRINT) == before
        assert _job_from_cmd(before) == {
            "script_path": "s.py", "output_path": "o.stl", "params_json": '{"a": 1}', "export_format": "stl",
        }

    def test_preview_rides_as_a_fifth_runner_argument_and_reaches_the_pool_job(self):
        cmd = build_cadquery_command("o.stl", "s.py", {}, "stl", PREVIEW)
        assert cmd[-1] == PREVIEW and len(cmd) == 7
        assert _job_from_cmd(cmd)["tessellation"] == PREVIEW

    def test_pool_request_carries_the_profile_only_when_it_is_not_print(self, monkeypatch):
        from services.engine.cq_pool import CadQueryPool

        seen = []

        class _Worker:
            def run(self, request, deadline, is_cancelled):
                seen.append(dict(request))
                return True, "ok"

        pool = CadQueryPool()
        monkeypatch.setattr(pool, "_acquire", lambda env: _Worker())
        monkeypatch.setattr(pool, "_release", lambda worker: None)
        assert pool.submit("s.py", "o.stl", "{}", "stl") == (True, "ok")
        assert pool.submit("s.py", "o.stl", "{}", "stl", tessellation=PREVIEW) == (True, "ok")
        assert "tessellation" not in seen[0]
        assert seen[1]["tessellation"] == PREVIEW


class TestRenderPayload:
    """The profile in the payload, the cache lookup and the artifact name."""

    @pytest.fixture
    def env(self, monkeypatch):
        class _Manifest:
            slug = "proj"

            def __init__(self):
                self.modes = [{"id": "solid", "parts": ["body"], "cq_file": "main.py"}]
                self.parameters = []

            def get_parts_map(self):
                return {"main.py": ["body"]}

            def get_allowed_files(self):
                return {"main.py": "/tmp/main.py"}

            def get_mode_map(self):
                return {"body": 0}

            def get_static_stl_map(self):
                return {}

        class _Source:
            filename = "main.py"
            path = "/tmp/main.py"
            is_graph = False

        monkeypatch.setattr("services.engine.render_orchestrator.get_manifest", lambda *a: _Manifest())
        monkeypatch.setattr("services.engine.render_orchestrator.render_source_for_mode", lambda m, mode: _Source())
        monkeypatch.setattr("services.engine.render_orchestrator.validate_params", lambda raw, *a: dict(raw))
        monkeypatch.setattr("services.engine.render_orchestrator.source_content_hash", lambda *a: "deadbeef")
        monkeypatch.setattr(
            "services.engine.generator_output.resolve_render_inputs",
            lambda manifest, mode, raw, validate, material_injector: (validate(raw), None),
        )

    def _payload(self, **extra):
        from services.engine.render_orchestrator import extract_render_payload

        return extract_render_payload({"project": "proj", "mode": "solid", "parameters": {}, **extra})

    def test_public_preview_request_is_a_403_payload_error(self, env):
        from services.engine.render_orchestrator import RenderPayloadError

        err = self._payload(tessellation="preview")
        assert isinstance(err, RenderPayloadError)
        assert (err.status_code, err.error_code) == (403, "tessellation_not_allowed")

    def test_print_payload_and_artifact_name_are_unchanged(self, env):
        plain = self._payload()
        explicit = self._payload(tessellation="print")
        assert plain["tessellation"] == explicit["tessellation"] == PRINT
        assert plain["stl_prefix"] == explicit["stl_prefix"]

    def test_preview_payload_gets_its_own_artifact_name(self, env, pipeline):
        print_payload = self._payload()
        preview_payload = self._payload(tessellation="preview")
        assert preview_payload["tessellation"] == PREVIEW
        assert preview_payload["stl_prefix"] != print_payload["stl_prefix"]

    def test_cache_lookup_uses_the_payload_profile(self, env, pipeline, monkeypatch):
        from services.engine import render_orchestrator

        seen = []
        monkeypatch.setattr(render_orchestrator.render_cache, "get",
                            lambda *a, **k: seen.append(k.get("tessellation")))
        render_orchestrator._check_cache(self._payload(tessellation="preview"), "body", "stl")
        render_orchestrator._check_cache(self._payload(), "body", "stl")
        assert seen == [PREVIEW, PRINT]
