"""Tests for projects API routes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path):
    """Create a test Flask app with a temporary projects directory."""
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

    def test_update_assembly_steps(self, client, tmp_path):
        steps = [{"step": 1, "label": {"en": "Print"}, "visible_parts": ["main"]}]
        res = client.put(
            "/api/projects/test-project/manifest/assembly-steps",
            json={"assembly_steps": steps},
        )
        assert res.status_code == 200
        assert res.get_json()["status"] == "success"
        # Verify persisted
        res2 = client.get("/api/projects/test-project/manifest")
        assert res2.get_json()["assembly_steps"] == steps

    def test_update_assembly_steps_missing_body(self, client):
        res = client.put(
            "/api/projects/test-project/manifest/assembly-steps",
            json={},
        )
        assert res.status_code == 400

    def test_update_assembly_steps_unknown_project(self, client):
        res = client.put(
            "/api/projects/nonexistent/manifest/assembly-steps",
            json={"assembly_steps": []},
        )
        assert res.status_code == 404

    def test_serve_static_part_404(self, client):
        res = client.get("/api/projects/test-project/parts/missing.stl")
        assert res.status_code == 404
