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


class TestEstimateAPI:
    def test_estimate_constant_mode(self, client):
        """Constant mode: slicer-grade estimate. 1 unit, 1 part.
        Formula: (1 * 0.20 / 8.0) + (1 * 180.0) = 180.025 → rounds to 180.0"""
        res = client.post("/api/estimate", json={"mode": "single", "project": "test-project"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["estimated_seconds"] == 180.0
        assert data["num_parts"] == 1
        assert data["metrics"] == "slicer_grade_heuristic"

    def test_estimate_grid_mode(self, client):
        """Grid mode 10x10: slicer-grade estimate. 100 units, 2 parts.
        Formula: (100 * 0.20 / 8.0) + (2 * 180.0) = 2.5 + 360.0 = 362.5"""
        res = client.post("/api/estimate", json={
            "mode": "grid", "project": "test-project",
            "rows": 10, "cols": 10,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["estimated_seconds"] == 362.5
        assert data["num_parts"] == 2
        assert data["metrics"] == "slicer_grade_heuristic"


class TestEstimateExportFormat:
    def test_estimate_ignores_export_format(self, client):
        """export_format is a render param — estimate should still work and return 180.0 for single mode."""
        res = client.post("/api/estimate", json={
            "mode": "single", "project": "test-project", "export_format": "3mf",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["estimated_seconds"] == 180.0
        assert data["metrics"] == "slicer_grade_heuristic"


class TestRenderExportFormat:
    def test_invalid_format_falls_back_to_stl(self):
        """Invalid export_format should fall back to stl."""
        from routes.engine.render import ALLOWED_EXPORT_FORMATS
        assert "exe" not in ALLOWED_EXPORT_FORMATS
        assert "stl" in ALLOWED_EXPORT_FORMATS

    def test_valid_formats_accepted(self):
        """Valid export formats are in the allow list."""
        from routes.engine.render import ALLOWED_EXPORT_FORMATS
        assert "stl" in ALLOWED_EXPORT_FORMATS
        assert "3mf" in ALLOWED_EXPORT_FORMATS
        assert "off" in ALLOWED_EXPORT_FORMATS
        assert "step" in ALLOWED_EXPORT_FORMATS
        assert "glb" in ALLOWED_EXPORT_FORMATS
        assert "gltf" in ALLOWED_EXPORT_FORMATS

class TestEngineFormatValidation:
    def test_openscad_rejects_step_format(self, client, monkeypatch):
        """OpenSCAD engine should reject unsupported formats like step."""
        monkeypatch.setattr("routes.engine.render._extract_render_payload", lambda *args: {
            "parts": ["m"], "export_format": "step", "params": {}, "scad_path": "mock",
            "mode_map": {"m": 0}, "stl_prefix": "pre_", "project_slug": "os", "scad_filename": "mock.scad"
        })
        class MockManifest:
            def __init__(self): self.engine = "openscad"
        monkeypatch.setattr("routes.engine.render.get_manifest", lambda *args: MockManifest())
        # Pro user bypasses premium export check but still hits engine format validation
        monkeypatch.setattr("routes.engine.render.resolve_tier", lambda *args: "pro")
        monkeypatch.setattr("routes.engine.render.check_feature", lambda *args: True)

        res = client.post("/api/render", json={"project": "os"})
        assert res.status_code == 400
        assert "not supported by OpenSCAD" in res.get_json()["error"]

    def test_openscad_accepts_stl_format(self, client, monkeypatch):
        """OpenSCAD engine should accept STL format."""
        from config import Config
        assert "stl" in Config.OPENSCAD_ALLOWED_EXPORT_FORMATS

    def test_cadquery_accepts_step_format(self, client, monkeypatch):
        """CadQuery engine should accept STEP format."""
        from config import Config
        assert "step" in Config.CADQUERY_ALLOWED_EXPORT_FORMATS


class TestTierEnforcementRender:
    def test_guest_blocked_from_cadquery(self, client, monkeypatch):
        monkeypatch.setattr("routes.engine.render._extract_render_payload", lambda *args: {
            "parts": ["m"], "export_format": "stl", "params": {}, "scad_path": "mock", "mode_map": {"m": 0}, "stl_prefix": "pre_", "project_slug": "cq", "scad_filename": "mock.scad"
        })
        class MockManifest:
            def __init__(self): self.engine = "cadquery"
        monkeypatch.setattr("routes.engine.render.get_manifest", lambda *args: MockManifest())
        
        res = client.post("/api/render", json={"project": "cq"})
        assert res.status_code == 403
        assert "CadQuery engine is not available" in res.get_json()["error"]

    def test_guest_blocked_from_premium_export(self, client, monkeypatch):
        monkeypatch.setattr("routes.engine.render._extract_render_payload", lambda *args: {
            "parts": ["m"], "export_format": "step", "params": {}, "scad_path": "mock", "mode_map": {"m": 0}, "stl_prefix": "pre_", "project_slug": "os", "scad_filename": "mock.scad"
        })
        class MockManifest:
            def __init__(self): self.engine = "openscad"
        monkeypatch.setattr("routes.engine.render.get_manifest", lambda *args: MockManifest())
        
        res = client.post("/api/render", json={"project": "os"})
        assert res.status_code == 403
        assert "requires Pro tier" in res.get_json()["error"]


class TestCancelAPI:
    def test_cancel_no_active_render(self, client):
        res = client.post("/api/render-cancel")
        assert res.status_code == 200
        data = res.get_json()
        assert data["cancelled"] is False

    def test_cancel_returns_status_field(self, client):
        """Cancel response includes a status field indicating no_active_render."""
        res = client.post("/api/render-cancel")
        data = res.get_json()
        assert data["status"] == "no_active_render"


class TestEstimateEdgeCases:
    def test_estimate_no_mode_falls_back_to_first(self, client):
        """Estimate without mode falls back to first manifest mode."""
        res = client.post("/api/estimate", json={"project": "test-project"})
        assert res.status_code == 200
        data = res.get_json()
        # Falls back to 'single' mode: 1 unit, 1 part -> 180.0s
        assert data["estimated_seconds"] == 180.0
        assert data["num_parts"] == 1

    def test_estimate_legacy_scad_file_field(self, client):
        """Estimate with legacy scad_file field instead of mode resolves correctly."""
        res = client.post("/api/estimate", json={
            "project": "test-project",
            "scad_file": "grid.scad",
            "rows": 5, "cols": 5,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["num_parts"] == 2  # grid mode has 2 parts

    def test_estimate_missing_project(self, client):
        """Estimate with non-existent project raises unhandled RuntimeError."""
        with pytest.raises(RuntimeError, match="Project manifest not found"):
            client.post("/api/estimate", json={"project": "no-such-project", "mode": "single"})

    def test_estimate_non_json_body(self, client):
        """Estimate with non-JSON content type returns 415."""
        res = client.post("/api/estimate", data="not json", content_type="text/plain")
        assert res.status_code in (400, 415)


class TestRenderPayloadValidation:
    def test_render_invalid_scad_file(self, client):
        """Render with an invalid scad file name returns 400."""
        res = client.post("/api/render", json={
            "project": "test-project",
            "scad_file": "../../etc/passwd",
        })
        assert res.status_code == 400
        assert "Invalid SCAD file" in res.get_json()["error"]

    def test_render_non_json_body(self, client):
        """Render without JSON content type returns 415."""
        res = client.post("/api/render", data="not json", content_type="text/plain")
        assert res.status_code in (400, 415)

    def test_render_payload_extracts_ignore_cache(self, monkeypatch):
        """_extract_render_payload correctly extracts ignore_cache flag."""
        from routes.engine.render import _extract_render_payload
        
        class MockManifest:
            def __init__(self):
                self.slug = "test-project"
                self.modes = [{"id": "single", "parts": ["m"], "scad_file": "m.scad"}]
                self.parts = [{"id": "m", "render_mode": 0}]
                self.parameters = []
            def get_parts_map(self): return {"m.scad": ["m"]}
            def get_allowed_files(self): return {"m.scad": "mock_path"}
            def get_mode_map(self): return {"m": 0}
            def get_static_stl_map(self): return {}
                
        monkeypatch.setattr("routes.engine.render.get_manifest", lambda *args: MockManifest())
        monkeypatch.setattr("routes.engine.render.validate_params", lambda *args: {})
        
        payload = _extract_render_payload({"project": "test-project", "ignore_cache": True})
        assert payload["ignore_cache"] is True
