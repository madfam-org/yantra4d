"""Tests for projects API routes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "web_interface" / "backend"))


@pytest.fixture
def app(tmp_path):
    """Create a test Flask app with a temporary projects directory."""
    import os
    os.environ["PROJECTS_DIR"] = str(tmp_path)

    # Reload config to pick up new env var
    import importlib
    import config
    importlib.reload(config)

    # Create a test project
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    # Clear manifest cache
    import manifest as manifest_mod
    manifest_mod._manifest_cache.clear()

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestProjectsAPI:
    def test_list_projects(self, client):
        res = client.get("/api/projects")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) >= 1
        assert data[0]["slug"] == "test-project"

    def test_get_project_manifest(self, client):
        res = client.get("/api/projects/test-project/manifest")
        assert res.status_code == 200
        data = res.get_json()
        assert data["project"]["slug"] == "test-project"

    def test_unknown_project_404(self, client):
        res = client.get("/api/projects/nonexistent/manifest")
        assert res.status_code == 404
