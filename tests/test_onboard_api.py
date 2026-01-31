"""Tests for onboard API routes."""
import io
import json
import sys
from pathlib import Path

import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "web_interface" / "backend"))


@pytest.fixture(autouse=True)
def disable_auth():
    with patch("config.Config.AUTH_ENABLED", False):
        yield


@pytest.fixture
def app():
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestAnalyzeAPI:
    def test_analyze_scad_files(self, client):
        data = {
            'files': (io.BytesIO(b'cube(10);'), 'test.scad'),
        }
        res = client.post("/api/projects/analyze", data=data, content_type='multipart/form-data')
        assert res.status_code == 200
        result = res.get_json()
        assert "manifest" in result
        assert "analysis" in result


class TestCreateAPI:
    def test_create_project(self, client, tmp_path):
        manifest = {
            "project": {"name": "New Project", "slug": "new-project", "version": "1.0.0"},
            "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
            "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
            "parameters": [],
            "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
        }
        data = {
            'manifest': json.dumps(manifest),
            'files': (io.BytesIO(b'cube(10);'), 'main.scad'),
        }
        res = client.post("/api/projects/create", data=data, content_type='multipart/form-data')
        assert res.status_code == 201
        result = res.get_json()
        assert result["slug"] == "new-project"
        # Verify files written to PROJECTS_DIR (which is tmp_path via conftest)
        from config import Config
        project_dir = Config.PROJECTS_DIR / "new-project"
        assert (project_dir / "project.json").exists()
        assert (project_dir / "main.scad").exists()

    def test_create_duplicate_slug_409(self, client, tmp_path):
        # Create a project dir so it already exists
        from config import Config
        existing_dir = Config.PROJECTS_DIR / "existing"
        existing_dir.mkdir(exist_ok=True)
        manifest = {
            "project": {"name": "Existing", "slug": "existing", "version": "1.0.0"},
            "modes": [], "parts": [], "parameters": [],
            "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
        }
        data = {
            'manifest': json.dumps(manifest),
        }
        res = client.post("/api/projects/create", data=data, content_type='multipart/form-data')
        assert res.status_code == 409
