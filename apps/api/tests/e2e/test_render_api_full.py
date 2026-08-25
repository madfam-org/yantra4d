"""Tests for render API routes — full render, streaming, and cancel."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

    # Patch module-level STATIC_FOLDER in the render orchestrator (captured at import)
    import services.engine.render_orchestrator as orchestrator_mod
    monkeypatch.setattr(orchestrator_mod, "STATIC_FOLDER", str(static_dir))

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [
            {"id": "single", "scad_file": "main.scad", "label": {"en": "Single"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}},
            {"id": "grid", "scad_file": "grid.scad", "label": {"en": "Grid"}, "parts": ["grid_a", "grid_b"], "estimate": {"base_units": 1, "formula": "grid", "formula_vars": ["rows", "cols"]}},
        ],
        "parts": [
            {"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"},
            {"id": "grid_a", "render_mode": 0, "label": {"en": "Grid A"}, "default_color": "#ffffff"},
            {"id": "grid_b", "render_mode": 1, "label": {"en": "Grid B"}, "default_color": "#ffffff"},
        ],
        "parameters": [
            {"id": "rows", "type": "number", "default": 3, "min": 1, "max": 20, "label": {"en": "Rows"}},
            {"id": "cols", "type": "number", "default": 3, "min": 1, "max": 20, "label": {"en": "Cols"}},
        ],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")
    (project_dir / "grid.scad").write_text("cube(5);")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _mock_validate_params(monkeypatch):
    """Bypass validate_params so unit tests don't need a real manifest."""
    monkeypatch.setattr("services.engine.render_orchestrator.validate_params", lambda data, project_slug=None: {
        k: v for k, v in data.items()
        if k not in ("mode", "scad_file", "parameters", "project", "export_format")
    })


class TestRenderEndpoint:
    def test_render_success(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(
                [{"type": "main", "url": "/static/test-project_preview_main.stl"}],
                "Render complete",
                (0, 1),
            ),
        ):
            res = client.post("/api/render", json={"mode": "single", "project": "test-project"})

        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert len(data["parts"]) == 1
        assert data["parts"][0]["type"] == "main"

    def test_render_failure(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(None, "OpenSCAD error: syntax error", (0, 1)),
        ):
            res = client.post("/api/render", json={"mode": "single", "project": "test-project"})

        assert res.status_code == 500
        data = res.get_json()
        assert data["status"] == "error"

    def test_render_worker_unavailable_returns_503(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(None, "Render worker unavailable or not healthy", (0, 0)),
        ):
            res = client.post("/api/render", json={"mode": "single", "project": "test-project"})

        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_code"] == "render_worker_unavailable"

    def test_render_invalid_scad(self, client):
        res = client.post("/api/render", json={"scad_file": "nonexistent.scad", "project": "test-project"})
        assert res.status_code == 400

    def test_render_no_body(self, client):
        res = client.post("/api/render", content_type="application/json")
        assert res.status_code == 400

    def test_render_cache_hit(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(
                [{"type": "main", "url": "/static/test-project_preview_main.stl"}],
                "[main] cache HIT\n",
                (1, 1),
            ),
        ):
            res = client.post("/api/render", json={"mode": "single", "project": "test-project"})

        assert res.status_code == 200
        assert res.headers.get("X-Cache") == "HIT"

    def test_render_export_format_3mf(self, client):
        with patch("routes.engine.render.export_format_allowed", return_value=True), \
             patch(
                 "routes.engine.render.render_parts_sync",
                 return_value=(
                     [{"type": "main", "url": "/static/test-project_preview_main.3mf"}],
                     "",
                     (0, 1),
                 ),
             ):
            res = client.post("/api/render", json={
                "mode": "single", "project": "test-project", "export_format": "3mf",
            })
            assert res.status_code == 200

    def test_render_invalid_export_format_falls_back(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(
                [{"type": "main", "url": "/static/test-project_preview_main.stl"}],
                "",
                (0, 1),
            ),
        ):
            res = client.post("/api/render", json={
                "mode": "single", "project": "test-project", "export_format": "exe",
            })
            assert res.status_code == 200

    def test_render_rate_limit_headers(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(
                [{"type": "main", "url": "/static/test-project_preview_main.stl"}],
                "",
                (0, 1),
            ),
        ):
            res = client.post("/api/render", json={"mode": "single", "project": "test-project"})
            assert res.status_code == 200
            assert "X-RateLimit-Tier" in res.headers

    def test_render_grid_multiple_parts(self, client):
        with patch(
            "routes.engine.render.render_parts_sync",
            return_value=(
                [
                    {"type": "grid_a", "url": "/static/test-project_preview_grid_a.stl"},
                    {"type": "grid_b", "url": "/static/test-project_preview_grid_b.stl"},
                ],
                "ok",
                (0, 2),
            ),
        ):
            res = client.post("/api/render", json={"mode": "grid", "project": "test-project"})

        assert res.status_code == 200
        data = res.get_json()
        assert len(data["parts"]) == 2


class TestRenderStreamEndpoint:
    def test_stream_invalid_scad(self, client):
        res = client.post("/api/render-stream", json={"scad_file": "bad.scad", "project": "test-project"})
        assert res.status_code == 400

    def test_stream_no_body(self, client):
        res = client.post("/api/render-stream", content_type="application/json")
        assert res.status_code == 400

    def test_stream_returns_sse(self, client):
        with patch(
            "routes.engine.render.render_parts_stream",
            return_value=iter([
                'data: {"event":"progress","progress":50}\n\n',
                'data: {"event":"complete","parts":[{"type":"main","url":"/static/main.stl"}],"progress":100}\n\n',
            ]),
        ):
            res = client.post("/api/render-stream", json={"mode": "single", "project": "test-project"})

        assert res.status_code == 200
        assert "text/event-stream" in res.content_type


class TestCancelEndpoint:
    @patch("routes.engine.render.cancel_all_renders", return_value=True)
    def test_cancel_active(self, mock_cancel, client):
        res = client.post("/api/render-cancel")
        assert res.status_code == 200
        data = res.get_json()
        assert data["cancelled"] is True
        assert data["status"] == "cancelled"

    @patch("routes.engine.render.cancel_all_renders", return_value=False)
    def test_cancel_no_active(self, mock_cancel, client):
        res = client.post("/api/render-cancel")
        assert res.status_code == 200
        data = res.get_json()
        assert data["cancelled"] is False
        assert data["status"] == "no_active_render"


class TestEstimateEdgeCases:
    def test_estimate_missing_mode(self, client):
        res = client.post("/api/estimate", json={"project": "test-project"})
        assert res.status_code == 200

    def test_estimate_with_scad_file_fallback(self, client):
        res = client.post("/api/estimate", json={"scad_file": "main.scad", "project": "test-project"})
        assert res.status_code == 200
        data = res.get_json()
        assert "estimated_seconds" in data

    def test_estimate_nonexistent_project(self, client):
        with pytest.raises(RuntimeError, match="not found"):
            client.post("/api/estimate", json={"project": "no-such-project"})
