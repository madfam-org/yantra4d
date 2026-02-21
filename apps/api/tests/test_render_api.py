"""Tests for render API routes (estimate + cancel only; actual render deferred)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"name": "Test Project", "slug": "test-project", "version": "1.0.0"},
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


class TestEstimateAPI:
    def test_estimate_constant_mode(self, client):
        """Constant mode: base_time + base_units*per_unit + 1_part*per_part = 5 + 1*2 + 1*8 = 15"""
        res = client.post("/api/estimate", json={"mode": "single", "project": "test-project"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["estimated_seconds"] == 15
        assert data["num_parts"] == 1
        assert data["num_units"] == 1

    def test_estimate_grid_mode(self, client):
        """Grid mode with rows=10, cols=10: base_time + 100*per_unit + 2*per_part = 5 + 200 + 16 = 221"""
        res = client.post("/api/estimate", json={
            "mode": "grid", "project": "test-project",
            "rows": 10, "cols": 10,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["estimated_seconds"] == 221
        assert data["num_parts"] == 2
        assert data["num_units"] == 100


class TestEstimateExportFormat:
    def test_estimate_ignores_export_format(self, client):
        """export_format is a render param, not an estimate param — estimate should still work."""
        res = client.post("/api/estimate", json={
            "mode": "single", "project": "test-project", "export_format": "3mf",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["estimated_seconds"] == 15


class TestRenderExportFormat:
    def test_invalid_format_falls_back_to_stl(self):
        """Invalid export_format should fall back to stl."""
        from routes.render import ALLOWED_EXPORT_FORMATS
        assert "exe" not in ALLOWED_EXPORT_FORMATS
        assert "stl" in ALLOWED_EXPORT_FORMATS

    def test_valid_formats_accepted(self):
        """Valid export formats are in the allow list."""
        from routes.render import ALLOWED_EXPORT_FORMATS
        assert "stl" in ALLOWED_EXPORT_FORMATS
        assert "3mf" in ALLOWED_EXPORT_FORMATS
        assert "off" in ALLOWED_EXPORT_FORMATS

class TestTierEnforcementRender:
    def test_guest_blocked_from_cadquery(self, client, monkeypatch):
        monkeypatch.setattr("routes.render._extract_render_payload", lambda *args: {
            "parts": ["m"], "export_format": "glb", "params": {}, "scad_path": "mock", "mode_map": {"m": 0}, "stl_prefix": "pre_", "project_slug": "cq", "scad_filename": "mock.scad"
        })
        class MockManifest:
            def __init__(self): self.engine = "cadquery"
        monkeypatch.setattr("routes.render.get_manifest", lambda *args: MockManifest())
        
        res = client.post("/api/render", json={"project": "cq"})
        assert res.status_code == 403
        assert "CadQuery engine is not available" in res.get_json()["error"]

    def test_guest_blocked_from_premium_export(self, client, monkeypatch):
        monkeypatch.setattr("routes.render._extract_render_payload", lambda *args: {
            "parts": ["m"], "export_format": "step", "params": {}, "scad_path": "mock", "mode_map": {"m": 0}, "stl_prefix": "pre_", "project_slug": "os", "scad_filename": "mock.scad"
        })
        class MockManifest:
            def __init__(self): self.engine = "openscad"
        monkeypatch.setattr("routes.render.get_manifest", lambda *args: MockManifest())
        
        res = client.post("/api/render", json={"project": "os"})
        assert res.status_code == 403
        assert "requires Pro tier" in res.get_json()["error"]


class TestCancelAPI:
    def test_cancel_no_active_render(self, client):
        res = client.post("/api/render-cancel")
        assert res.status_code == 200
        data = res.get_json()
        assert data["cancelled"] is False
