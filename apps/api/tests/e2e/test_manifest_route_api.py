"""Tests for manifest route API."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [{"id": "size", "type": "number", "default": 20, "min": 5, "max": 100, "label": {"en": "Size"}}],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    # /api/manifest with no slug falls back to SCAD_DIR
    monkeypatch.setattr(Config, "SCAD_DIR", project_dir)
    monkeypatch.setattr(Config, "MULTI_PROJECT", False)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestManifestRouteAPI:
    def test_get_manifest(self, client):
        res = client.get("/api/manifest")
        assert res.status_code == 200
        data = res.get_json()
        assert "project" in data
        assert "modes" in data
        assert "parameters" in data
        assert data["project"]["slug"] == "test-project"

    def test_multi_project_requires_slug(self, tmp_path, monkeypatch):
        from config import Config

        project_dir = tmp_path / "mp-project"
        project_dir.mkdir()
        (project_dir / "project.json").write_text('{"project":{"name":"X","slug":"x","version":"1.0.0","thumbnail":"t.png","tags":[],"difficulty":"beginner"},"modes":[],"parts":[],"parameters":[],"estimate_constants":{}}')
        monkeypatch.setattr(Config, "SCAD_DIR", project_dir)
        monkeypatch.setattr(Config, "MULTI_PROJECT", True)

        from app import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            res = c.get("/api/manifest")
            assert res.status_code == 400
