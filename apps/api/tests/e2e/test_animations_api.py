"""Tests for animation API routes."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

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

    @patch("routes.projects.animations.run_openscad_render")
    @patch("routes.projects.animations.stl_to_glb")
    def test_render_streams_events(self, mock_glb, mock_render, client, tmp_path):
        mock_render.return_value = (True, "")
        mock_glb.return_value = True

        from config import Config
        Config.STATIC_DIR.mkdir(parents=True, exist_ok=True)

        res = client.post("/api/projects/anim-test/animations/grow/render",
                          json={"parameters": {}})
        assert res.status_code == 200
        assert "text/event-stream" in res.content_type

        # Parse SSE events
        lines = res.data.decode().strip().split("\n\n")
        events = []
        for block in lines:
            for line in block.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        # Should have frame_done events + 1 complete event
        frame_done_events = [e for e in events if e["event"] == "frame_done"]
        complete_events = [e for e in events if e["event"] == "complete"]
        assert len(frame_done_events) == 3  # 3 frames
        assert len(complete_events) == 1
        assert complete_events[0]["progress"] == 100

    @patch("routes.projects.animations.run_openscad_render")
    def test_render_error_streams_error_event(self, mock_render, client):
        mock_render.return_value = (False, "OpenSCAD crashed")

        from config import Config
        Config.STATIC_DIR.mkdir(parents=True, exist_ok=True)

        res = client.post("/api/projects/anim-test/animations/grow/render",
                          json={"parameters": {}})
        assert res.status_code == 200

        events = []
        for block in res.data.decode().strip().split("\n\n"):
            for line in block.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        assert "OpenSCAD crashed" in error_events[0]["error"]
