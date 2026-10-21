"""Tests for animation API routes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

PRO_CLAIMS = {"sub": "test-user", "yantra4d_tier": "pro"}

MANIFEST_DATA = {
    "project": {
        "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
        "name": "Anim Test", "slug": "anim-test", "version": "1.0.0",
    },
    "modes": [{
        "id": "default", "scad_file": "main.scad",
        "label": {"en": "Default"}, "parts": ["main"],
        "estimate": {"base_units": 1, "formula": "constant"},
    }],
    "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
    "parameters": [
        {"id": "height", "type": "number", "default": 10, "min": 1, "max": 100, "label": {"en": "Height"}},
        {"id": "width", "type": "slider", "default": 5, "min": 1, "max": 20, "label": {"en": "Width"}},
    ],
    "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    "animations": [{
        "id": "grow",
        "label": {"en": "Grow"},
        "description": {"en": "Animate height"},
        "from_state": {"height": 10},
        "to_state": {"height": 50},
        "frames": 3,
        "duration_ms": 1000,
        "easing": "linear",
        "mode": "default",
    }],
}


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

    project_dir = tmp_path / "anim-test"
    project_dir.mkdir()
    (project_dir / "project.json").write_text(json.dumps(MANIFEST_DATA))
    (project_dir / "main.scad").write_text("cube(10);")

    # Stub resolve_tier to return "pro" so tier gates pass
    # (AUTH_ENABLED=false sets auth_claims=None → guest → denied otherwise)
    import routes.projects.animations as anim_mod
    monkeypatch.setattr(anim_mod, "resolve_tier", lambda _: "pro")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestListAnimations:
    def test_returns_animations(self, client):
        res = client.get("/api/projects/anim-test/animations")
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 1
        assert data["animations"][0]["id"] == "grow"

    def test_no_animations(self, client, tmp_path, monkeypatch):
        no_anim_manifest = {**MANIFEST_DATA, "animations": []}
        project_dir = tmp_path / "no-anim"
        project_dir.mkdir()
        (project_dir / "project.json").write_text(json.dumps(no_anim_manifest))
        (project_dir / "main.scad").write_text("cube(1);")

        res = client.get("/api/projects/no-anim/animations")
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 0
        assert data["animations"] == []

    def test_nonexistent_project_returns_404(self, client):
        res = client.get("/api/projects/nonexistent-abc/animations")
        assert res.status_code == 404


class TestRenderAnimation:
    def test_unknown_animation_returns_404(self, client):
        res = client.post("/api/projects/anim-test/animations/nonexistent/render",
                          json={"parameters": {}})
        assert res.status_code == 404

    def test_render_route_carries_rate_limit(self, app, client):
        """Flipbook render (N frames x M parts) must be rate-limited.

        Rate limit headers (headers_enabled=True in extensions.py) prove the
        @limiter.limit decorator is registered with the intended value; the
        limiter runs before the view, so the 404 body is irrelevant here.
        The conftest fixture disables the limiter before create_app(), which
        skips hook registration, so re-init the limiter on this fresh app.
        """
        from extensions import limiter
        app.config["RATELIMIT_ENABLED"] = True
        limiter.enabled = True
        limiter.init_app(app)
        try:
            res = client.post("/api/projects/anim-test/animations/nonexistent/render",
                              json={"parameters": {}})
            assert res.status_code == 404
            assert res.headers.get("X-RateLimit-Limit") == "10"
        finally:
            limiter.enabled = False


# ---------------------------------------------------------------------------
# Rendering goes through the render worker: the route queues one task per
# frame part on RENDER_QUEUE and relays the worker's events. The worker runs
# inline against an in-memory Redis (tests/inline_render_worker.py); only the
# engines are faked.
# ---------------------------------------------------------------------------

CQ_MANIFEST = {
    **MANIFEST_DATA,
    "project": {**MANIFEST_DATA["project"], "name": "CQ Anim", "slug": "cq-anim"},
    "modes": [{
        "id": "default", "scad_file": "main.py", "engine": "cadquery",
        "label": {"en": "Default"}, "parts": ["body", "lid"],
        "estimate": {"base_units": 1, "formula": "constant"},
    }],
    "parts": [
        {"id": "body", "render_mode": 0, "label": {"en": "Body"}, "default_color": "#fff"},
        {"id": "lid", "render_mode": 1, "label": {"en": "Lid"}, "default_color": "#fff"},
    ],
    "animations": [{**MANIFEST_DATA["animations"][0], "frames": 2}],
}


def _events(res) -> list[dict]:
    events = []
    for block in res.data.decode().strip().split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


@pytest.fixture
def queue(monkeypatch, tmp_path):
    from inline_render_worker import install
    return install(monkeypatch, tmp_path / "static")


@pytest.fixture
def engines(monkeypatch):
    """Fake engines inside the WORKER module, recording what they were asked."""
    import render_worker

    calls = []

    def build(engine):
        def _build(output_path, script_path, params, *rest):
            return [engine, output_path, script_path, json.dumps(params)]
        return _build

    def run(cmd, scad_path=None, is_cancelled=None):
        calls.append({"engine": cmd[0], "output": cmd[1], "script": cmd[2],
                      "params": json.loads(cmd[3]), "scad_path": scad_path})
        if engines.fail:
            return False, engines.fail
        Path(cmd[1]).write_bytes(b"solid x\nendsolid x\n")
        return True, "rendered"

    def to_glb(src, dst):
        Path(dst).write_bytes(b"glTF")
        return True

    cache_puts = []
    monkeypatch.setattr(render_worker, "build_openscad_command",
                        lambda out, scad, params, mode: ["openscad", out, scad, json.dumps(params)])
    monkeypatch.setattr(render_worker, "build_cadquery_command", build("cadquery"))
    monkeypatch.setattr(render_worker, "run_openscad_render", run)
    monkeypatch.setattr(render_worker, "run_cadquery_render", run)
    monkeypatch.setattr(render_worker, "stl_to_glb", to_glb)
    monkeypatch.setattr(render_worker.render_cache, "put", lambda *a, **k: cache_puts.append(a))
    engines.fail = None
    engines.calls = calls
    engines.cache_puts = cache_puts
    return engines


class TestRenderAnimationOnWorker:
    def test_every_frame_is_a_worker_job(self, client, queue, engines):
        res = client.post("/api/projects/anim-test/animations/grow/render", json={"parameters": {}})
        assert res.status_code == 200
        assert "text/event-stream" in res.content_type
        events = _events(res)

        # One sync task per frame part, all on the shared render queue.
        assert len(queue.pushed) == 3
        assert all(task["stream"] is False and task["engine"] == "openscad" for task in queue.pushed)
        assert [task["payload"]["params"]["height"] for task in queue.pushed] == [10, 30, 50]
        assert all(task["payload"]["cache_write"] is False for task in queue.pushed)
        assert engines.cache_puts == []
        # The engine ran in the worker, against the cartridge's own file.
        assert [call["engine"] for call in engines.calls] == ["openscad"] * 3
        assert all(call["scad_path"].endswith("anim-test/main.scad") for call in engines.calls)

        # Contract unchanged: frame_done x3, then complete with GLB urls.
        assert [e["event"] for e in events if e["event"] != "job"] == [
            "frame_done", "frame_done", "frame_done", "complete",
        ]
        complete = events[-1]
        assert complete["progress"] == 100
        assert [f["frame_index"] for f in complete["frames"]] == [0, 1, 2]
        for frame in complete["frames"]:
            (part,) = frame["parts"]
            assert part["part"] == "main"
            assert part["url"].startswith("/static/anim_anim-test_grow_f")
            assert part["url"].endswith("_main.glb")

    def test_stream_announces_its_cancel_handle(self, client, queue, engines):
        events = _events(client.post("/api/projects/anim-test/animations/grow/render",
                                     json={"parameters": {}, "request_id": "req-anim-1"}))
        jobs = [e for e in events if e["event"] == "job"]
        assert jobs[0] == {**jobs[0], "request_id": "req-anim-1", "job_ids": []}
        assert jobs[-1]["job_ids"] == [task["job_id"] for task in queue.pushed]
        assert all(task["request_id"] == "req-anim-1" for task in queue.pushed)

    def test_frames_with_different_base_params_never_share_a_file(self, client, queue, engines):
        a = _events(client.post("/api/projects/anim-test/animations/grow/render", json={"parameters": {"width": 3}}))
        b = _events(client.post("/api/projects/anim-test/animations/grow/render", json={"parameters": {"width": 4}}))
        urls_a = {p["url"] for f in a[-1]["frames"] for p in f["parts"]}
        urls_b = {p["url"] for f in b[-1]["frames"] for p in f["parts"]}
        assert urls_a and urls_b and not (urls_a & urls_b)

    def test_base_params_are_validated_like_api_render(self, client, queue, engines):
        _events(client.post("/api/projects/anim-test/animations/grow/render",
                            json={"parameters": {"width": 99, "not_a_param": "x; rm"}}))
        params = queue.pushed[0]["payload"]["params"]
        assert params["width"] == 20.0  # clamped to the slider's max
        assert "not_a_param" not in params

    def test_engine_failure_streams_error_event(self, client, queue, engines):
        engines.fail = "OpenSCAD crashed"
        events = _events(client.post("/api/projects/anim-test/animations/grow/render", json={"parameters": {}}))
        errors = [e for e in events if e["event"] == "error"]
        assert len(errors) == 1
        assert errors[0]["frame"] == 0
        assert "OpenSCAD crashed" in errors[0]["error"]
        assert len(queue.pushed) == 1  # stops at the first failed frame
        assert not any(e["event"] == "complete" for e in events)

    def test_worker_unavailable_is_503(self, client, queue, engines):
        from services.engine import render_orchestrator
        queue.kv.pop(render_orchestrator.RENDER_WORKER_HEARTBEAT_KEY)
        res = client.post("/api/projects/anim-test/animations/grow/render", json={"parameters": {}})
        assert res.status_code == 503
        assert res.get_json()["error_code"] == "render_worker_unavailable"
        assert queue.pushed == []

    def test_client_disconnect_cancels_the_request(self, client, queue, engines):
        from services.engine import render_orchestrator
        res = client.post("/api/projects/anim-test/animations/grow/render",
                          json={"parameters": {}, "request_id": "req-gone"}, buffered=False)
        stream = iter(res.response)
        first = next(stream)
        assert b'"event": "job"' in (first if isinstance(first, bytes) else first.encode())
        res.close()  # the Studio's Cancel aborts the fetch
        assert queue.kv.get(f"{render_orchestrator.CANCEL_REQUEST_PREFIX}req-gone") == "1"

    def test_completed_stream_does_not_cancel(self, client, queue, engines):
        from services.engine import render_orchestrator
        _events(client.post("/api/projects/anim-test/animations/grow/render",
                            json={"parameters": {}, "request_id": "req-done"}))
        assert f"{render_orchestrator.CANCEL_REQUEST_PREFIX}req-done" not in queue.kv

    def test_cadquery_frames_render_on_the_worker_per_part(self, client, queue, engines, tmp_path):
        project_dir = tmp_path / "cq-anim"
        project_dir.mkdir()
        (project_dir / "project.json").write_text(json.dumps(CQ_MANIFEST))
        (project_dir / "main.py").write_text("import cadquery as cq\n")

        events = _events(client.post("/api/projects/cq-anim/animations/grow/render", json={"parameters": {}}))
        assert events[-1]["event"] == "complete"
        # 2 frames x 2 parts, each a CadQuery job selecting its own part.
        assert [(c["engine"], c["params"]["target_part"]) for c in engines.calls] == [
            ("cadquery", "body"), ("cadquery", "lid"), ("cadquery", "body"), ("cadquery", "lid"),
        ]
        assert all(task["engine"] == "cadquery" for task in queue.pushed)
