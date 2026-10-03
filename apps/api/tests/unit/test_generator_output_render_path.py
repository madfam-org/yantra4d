"""GOC-1 through the render path: worker, render cache, orchestrator, route, GC.

The rule every test here pins: a generated part carries ``sha256``,
``media_type``, ``instance_id`` and ``variables_url`` whether it came from the
worker or from the cache, on the filesystem store and on an object store, and
the sidecar it points at is stored, cached and collected with the artifact.
"""
import json
import sys
import time
from pathlib import Path

import pytest

from config import Config
from services.engine import generator_output as go
from services.engine import render_orchestrator as orch
from services.engine.render_cache import RenderCache
from services.storage import FilesystemArtifactStore

WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

# Imported after the sys.path line above, which is what makes it importable.
import render_worker

SLUG = "demo"
PART = "body"
PREFIX = f"{SLUG}_preview_0a1b2c_"
ARTIFACT = f"{PREFIX}{PART}.stl"
GLB = f"{PREFIX}{PART}.glb"
SIDECAR = f"{ARTIFACT}.variables.json"
MESH = b"solid body\nendsolid body\n"
GOC_FIELDS = ("sha256", "media_type", "instance_id", "variables_url")

MANIFEST = {
    "project": {"name": "Demo", "slug": SLUG, "version": "1.0.0"},
    "modes": [{"id": "unit", "scad_file": "main.scad", "label": "Unit", "parts": [PART],
               "estimate": {"base_units": 1, "formula": "constant"}}],
    "parts": [{"id": PART, "render_mode": 0, "label": "Body", "default_color": "#fff"}],
    "parameters": [
        {"id": "width", "type": "slider", "default": 40, "min": 10, "max": 100},
        {"id": "lid", "type": "checkbox", "default": True},
    ],
    "estimate_constants": {"base_time": 1, "per_unit": 0.1, "per_part": 0.5},
}


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    monkeypatch.setattr(Config, "RENDER_GENERATOR_OUTPUT", True)
    monkeypatch.setattr(Config, "RENDER_INJECT_FULL_PARAMS", False)
    monkeypatch.setattr(Config, "RENDER_MATERIAL_INJECTION", True)


@pytest.fixture
def demo(tmp_path):
    cart = tmp_path / SLUG
    cart.mkdir()
    (cart / "project.json").write_text(json.dumps(MANIFEST))
    (cart / "main.scad").write_text("cube(width);\n")
    from manifest import get_manifest
    return get_manifest(SLUG)


@pytest.fixture
def inputs(demo):
    _params, generator_inputs = go.resolve_render_inputs(demo, "unit", {"width": 42}, material_injector=None)
    return generator_inputs


@pytest.fixture
def staging(tmp_path, monkeypatch):
    staging_dir = tmp_path / "render-output"
    staging_dir.mkdir()
    monkeypatch.setattr(render_worker, "STATIC_FOLDER", str(staging_dir))
    return staging_dir


@pytest.fixture
def events(monkeypatch, demo):
    published = []
    monkeypatch.setattr(render_worker, "_publish_job_event",
                        lambda job_id, payload, emit_final=False: published.append(payload))
    monkeypatch.setattr(render_worker, "_set_active_job", lambda *a, **k: None)
    monkeypatch.setattr(render_worker, "_clear_active_job", lambda *a: None)
    monkeypatch.setattr(render_worker, "_is_cancelled", lambda job_id: False)
    monkeypatch.setattr(render_worker, "get_manifest", lambda slug: demo)
    monkeypatch.setattr("services.engine.openscad.backend_cache_signature", lambda: "Manifold|test")
    return published


@pytest.fixture
def rendering(staging, monkeypatch):
    def fake_render(cmd, scad_path=None, is_cancelled=None):
        (staging / ARTIFACT).write_bytes(MESH)
        return True, "render ok"

    def fake_stream(cmd, part, *args, **kwargs):
        (staging / ARTIFACT).write_bytes(MESH)
        yield json.dumps({"event": "part_done", "part": part})

    monkeypatch.setattr(render_worker, "run_openscad_render", fake_render)
    monkeypatch.setattr(render_worker, "stream_openscad_render", fake_stream)
    monkeypatch.setattr(render_worker, "build_openscad_command", lambda *a, **k: ["true"])
    monkeypatch.setattr(render_worker, "stl_to_glb", lambda src, dst: (Path(dst).write_bytes(b"glTF\x02"), True)[1])
    monkeypatch.setattr(render_worker, "convert_mesh", lambda *a, **k: False)
    return staging


def _task(staging, demo, inputs, stream=False):
    task = {
        "job_id": "job-1", "engine": "openscad", "part": PART,
        "scad_path": str(Path(demo.project_dir) / "main.scad"),
        "output_path": str(staging / ARTIFACT), "export_format": "stl",
        "payload": {"project_slug": SLUG, "mode": "unit", "params": {"width": 42.0}, "mode_map": {PART: 0},
                    "stl_prefix": PREFIX, "scad_filename": "main.scad", "scad_content_hash": "abc123",
                    "render_revision": "", "generator_inputs": inputs},
    }
    if stream:
        task.update(part_index=0, num_parts=1, part_base=0, part_weight=100)
    return task


def _store(kind, staging, s3_store):
    return FilesystemArtifactStore(staging) if kind == "fs" else s3_store


class TestWorkerWritesTheSidecar:
    @pytest.mark.parametrize("backend", ["fs", "s3"])
    @pytest.mark.parametrize("stream", [False, True])
    def test_sidecar_published_cached_and_announced(self, rendering, events, demo, inputs, monkeypatch,
                                                    s3_store, backend, stream):
        store = _store(backend, rendering, s3_store)
        cache = RenderCache(store=store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        task = _task(rendering, demo, inputs, stream=stream)
        (render_worker.process_stream_task if stream else render_worker.process_sync_task)(task)

        done = [e for e in events if e.get("event") == "part_done" and e.get("url")]
        assert len(done) == 1, events
        done = done[0]
        assert done["variables_url"] == f"/static/{SIDECAR}"
        assert done["media_type"] == "model/stl"
        assert done["generator_output"] == {"format_version": "1.0.0", "complete": False,
                                            "variables_sha256": inputs["variables_sha256"]}
        assert store.exists(SIDECAR)
        with store.open(SIDECAR) as body:
            doc = json.loads(body.read())
        assert doc["instance_id"] == done["instance_id"]
        assert doc["geometry"][0]["sha256"] == done["sha256"]
        assert [g["path"] for g in doc["geometry"]] == [ARTIFACT, GLB]
        entry = cache.get(SLUG, "main.scad", {"width": 42.0}, PART, "stl", scad_content_hash="abc123")
        assert go.part_fields_from_cache(entry) == {k: done[k] for k in GOC_FIELDS}
        if backend == "s3":
            assert list(rendering.iterdir()) == []

    def test_no_generator_inputs_means_no_sidecar_and_no_new_fields(self, rendering, events, demo, monkeypatch):
        store = FilesystemArtifactStore(rendering)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))
        render_worker.process_sync_task(_task(rendering, demo, None))
        done = next(e for e in events if e.get("event") == "part_done")
        assert not any(k in done for k in (*GOC_FIELDS, "generator_output"))
        assert not (rendering / SIDECAR).exists()


class TestRenderCacheCarriesTheFields:
    def test_round_trip_and_sidecar_presence(self, tmp_path):
        store = FilesystemArtifactStore(tmp_path)
        (tmp_path / ARTIFACT).write_bytes(MESH)
        (tmp_path / SIDECAR).write_bytes(b"{}")
        cache = RenderCache(store=store)
        fields = {"sha256": "a" * 64, "media_type": "model/stl", "instance_id": "b" * 64,
                  "variables_key": SIDECAR, "unrelated": "dropped"}
        cache.put(SLUG, "main.scad", {}, PART, "stl", ARTIFACT, 1, generator_fields=fields)
        entry = cache.get(SLUG, "main.scad", {}, PART, "stl")
        assert entry["variables_key"] == SIDECAR and "unrelated" not in entry
        (tmp_path / SIDECAR).unlink()
        assert cache.get(SLUG, "main.scad", {}, PART, "stl") is None


class TestOrchestratorCachePaths:
    @pytest.fixture
    def cached(self, tmp_path, monkeypatch, demo, inputs):
        store = FilesystemArtifactStore(tmp_path / "static")
        (tmp_path / "static").mkdir()
        (tmp_path / "static" / ARTIFACT).write_bytes(MESH)
        (tmp_path / "static" / SIDECAR).write_bytes(b"{}")
        cache = RenderCache(store=store)
        monkeypatch.setattr(orch, "render_cache", cache)
        monkeypatch.setattr(orch, "is_render_worker_available", lambda: False)
        monkeypatch.setattr(orch, "is_request_cancelled", lambda request_id: False)
        monkeypatch.setattr(orch, "clear_request_cancel", lambda request_id: None)
        payload = {"parts": [PART], "stl_prefix": PREFIX, "export_format": "stl", "project_slug": SLUG,
                   "scad_filename": "main.scad", "params": {"width": 42.0}, "scad_content_hash": "abc123",
                   "request_id": "req-1", "generator_inputs": inputs}
        fields = {"sha256": "a" * 64, "media_type": "model/stl", "instance_id": "b" * 64, "variables_key": SIDECAR}
        return cache, payload, fields

    def test_a_hit_answers_with_the_miss_fields(self, cached):
        cache, payload, fields = cached
        cache.put(SLUG, "main.scad", payload["params"], PART, "stl", ARTIFACT, len(MESH),
                  scad_content_hash="abc123", generator_fields=fields)
        parts, _log, stats = orch.render_parts_sync({}, payload, "openscad", "x", "stl", "guest")
        assert stats == (1, 1)
        assert parts[0]["variables_url"] == f"/static/{SIDECAR}"
        assert parts[0]["instance_id"] == "b" * 64

    def test_an_entry_without_a_sidecar_is_a_miss(self, cached):
        cache, payload, _fields = cached
        cache.put(SLUG, "main.scad", payload["params"], PART, "stl", ARTIFACT, len(MESH), scad_content_hash="abc123")
        parts, error, _stats = orch.render_parts_sync({}, payload, "openscad", "x", "stl", "guest")
        assert parts is None and "unavailable" in error  # it went looking for the worker

    def test_the_stream_hit_carries_the_fields_and_the_summary(self, cached):
        cache, payload, fields = cached
        cache.put(SLUG, "main.scad", payload["params"], PART, "stl", ARTIFACT, len(MESH),
                  scad_content_hash="abc123", generator_fields=fields)
        frames = [json.loads(f[6:]) for f in orch.render_parts_stream({}, payload, "openscad", "x", "stl")]
        done = next(f for f in frames if f["event"] == "part_done")
        complete = next(f for f in frames if f["event"] == "complete")
        assert done["stream_protocol"] == "1.2.0"
        assert done["cached"] is True and done["variables_url"] == f"/static/{SIDECAR}"
        assert complete["parts"][0]["instance_id"] == "b" * 64
        assert complete["generator_output"]["variables_sha256"] == payload["generator_inputs"]["variables_sha256"]

    def test_the_summary_never_leaks_into_a_part(self):
        clean = orch._sanitize_terminal_payload({"event": "part_done", "type": PART, "url": "/static/x",
                                                 "generator_output": {"complete": True}})
        assert "generator_output" not in clean


class TestPayloadAndEnvelope:
    def test_extract_render_payload_carries_the_generator_inputs(self, demo):
        payload = orch.extract_render_payload({"project": SLUG, "mode": "unit", "parameters": {"width": 42}})
        assert payload["params"] == {"width": 42.0}
        inputs = payload["generator_inputs"]
        assert {v["id"]: v["source"] for v in inputs["variables"]} == {"lid": "source_default", "width": "request"}

    def test_the_render_route_adds_generator_output(self, demo, monkeypatch):
        from app import create_app
        part = {"type": PART, "url": f"/static/{ARTIFACT}", "size_bytes": 1, "sha256": "a" * 64,
                "media_type": "model/stl", "instance_id": "b" * 64, "variables_url": f"/static/{SIDECAR}"}
        monkeypatch.setattr("routes.engine.render.render_parts_sync", lambda *a: ([part], "", (0, 1)))
        app = create_app()
        app.config["TESTING"] = True
        res = app.test_client().post("/api/render", json={"project": SLUG, "mode": "unit",
                                                          "parameters": {"width": 42}})
        body = res.get_json()
        assert res.status_code == 200, body
        assert body["parts"] == [part]
        assert body["generator_output"]["format_version"] == "1.0.0"
        assert body["generator_output"]["complete"] is False

    def test_flag_off_keeps_the_envelope_as_it_was(self, demo, monkeypatch):
        monkeypatch.setattr(Config, "RENDER_GENERATOR_OUTPUT", False)
        payload = orch.extract_render_payload({"project": SLUG, "mode": "unit", "parameters": {"width": 42}})
        assert payload["generator_inputs"] is None
        assert go.envelope_fields(payload) == {}


class TestGarbageCollection:
    def test_old_sidecars_are_collected_other_json_is_not(self, tmp_path):
        import os

        from services.engine.render_gc import _gc_sweep
        static = tmp_path / "static"
        static.mkdir()
        for name in (ARTIFACT, SIDECAR, "manifest.json"):
            (static / name).write_bytes(b"x")
            old = time.time() - 2 * 86400
            os.utime(static / name, (old, old))
        removed = _gc_sweep(str(static), 86400, store=FilesystemArtifactStore(static))
        assert removed == 2
        assert sorted(p.name for p in static.iterdir()) == ["manifest.json"]
