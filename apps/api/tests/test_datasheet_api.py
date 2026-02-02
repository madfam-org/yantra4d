"""Tests for datasheet generation API."""
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
        "project": {"name": "Test Project", "slug": "test-project", "version": "1.0.0", "description": "A test project"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
        "parameters": [
            {"id": "width", "type": "number", "default": 50, "min": 10, "max": 100, "label": {"en": "Width"}},
            {"id": "height", "type": "number", "default": 30, "label": {"en": "Height"}},
        ],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
        "bom": {
            "hardware": [
                {"id": "screw", "label": {"en": "M3 Screw"}, "quantity_formula": "4", "unit": "pcs"},
                {"id": "nut", "label": {"en": "M3 Nut"}, "quantity_formula": "4", "unit": "pcs"},
            ]
        },
        "assembly_steps": [
            {"step": 1, "label": {"en": "Attach base"}, "notes": {"en": "Use M3 screws"}},
            {"step": 2, "label": {"en": "Add top plate"}},
        ],
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestDatasheetHTML:
    def test_html_datasheet(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html")
        assert res.status_code == 200
        assert res.content_type.startswith("text/html")
        html = res.get_data(as_text=True)
        assert "Test Project" in html
        assert "Width" in html

    def test_html_includes_params(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html&width=75")
        html = res.get_data(as_text=True)
        assert "75" in html

    def test_html_includes_bom(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html")
        html = res.get_data(as_text=True)
        assert "M3 Screw" in html

    def test_html_includes_description(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html")
        html = res.get_data(as_text=True)
        assert "A test project" in html

    def test_lang_param(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html&lang=en")
        assert res.status_code == 200


class TestDatasheetPDF:
    def test_pdf_with_reportlab(self, client):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip("reportlab not installed")
        res = client.get("/api/projects/test-project/datasheet?format=pdf")
        assert res.status_code == 200
        assert res.content_type == "application/pdf"
        assert res.headers.get("Content-Disposition")

    def test_pdf_fallback_to_html(self, client, monkeypatch):
        monkeypatch.setattr("routes.datasheet.HAS_REPORTLAB", False)
        res = client.get("/api/projects/test-project/datasheet?format=pdf")
        assert res.status_code == 200
        assert res.content_type.startswith("text/html")


class TestDatasheetErrors:
    def test_nonexistent_project(self, client):
        res = client.get("/api/projects/nonexistent/datasheet")
        assert res.status_code == 404

    def test_default_format(self, client):
        res = client.get("/api/projects/test-project/datasheet")
        assert res.status_code == 200

    def test_param_type_coercion(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html&width=75.5")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "75.5" in html

    def test_param_string_value(self, client):
        res = client.get("/api/projects/test-project/datasheet?format=html&width=abc")
        assert res.status_code == 200
