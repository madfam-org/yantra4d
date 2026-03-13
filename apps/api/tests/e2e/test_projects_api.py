"""Tests for projects API routes."""
import json
import sys
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path):
    """Create a test Flask app with a temporary projects directory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
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

    def test_list_projects_with_stats(self, client):
        """stats=1 query param adds stats object to each project."""
        res = client.get("/api/projects?stats=1")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) >= 1
        # Each project should have a stats object (even if all zeros)
        for project in data:
            assert "stats" in project
            assert "renders" in project["stats"]
            assert "exports" in project["stats"]
            assert "preset_applies" in project["stats"]

    def test_list_projects_without_stats(self, client):
        """Without stats=1, projects should not have stats object."""
        res = client.get("/api/projects")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) >= 1
        for project in data:
            assert "stats" not in project

    def test_serve_static_part_404(self, client):
        res = client.get("/api/projects/test-project/parts/missing.stl")
        assert res.status_code == 404

    def test_serve_static_part_manifest_not_found(self, client):
        res = client.get("/api/projects/unknown/parts/missing.stl")
        assert res.status_code == 404

    def test_serve_static_part_out_of_bounds(self, client, tmp_path):
        (tmp_path / "test-project" / "parts").mkdir(exist_ok=True)
        res = client.get("/api/projects/test-project/parts/../project.json")
        assert res.status_code == 403

    def test_get_manifest_304(self, client):
        res = client.get("/api/projects/test-project/manifest")
        etag = res.headers.get("ETag")
        assert etag is not None
        
        res2 = client.get("/api/projects/test-project/manifest", headers={"If-None-Match": etag})
        assert res2.status_code == 304

    def test_get_project_meta_missing(self, client):
        res = client.get("/api/projects/test-project/meta")
        assert res.get_json() == {}

    def test_get_project_meta_found(self, client, tmp_path):
        import json
        meta_path = tmp_path / "test-project" / "project.meta.json"
        meta_path.write_text(json.dumps({"source": {"type": "github"}}))
        res = client.get("/api/projects/test-project/meta")
        assert res.get_json()["source"]["type"] == "github"

    def test_get_project_meta_unknown(self, client):
        res = client.get("/api/projects/unknown/meta")
        assert res.status_code == 404

    @patch("routes.projects.projects.os.path.exists")
    def test_stats_no_db(self, mock_exists, client):
        mock_exists.return_value = False
        res = client.get("/api/projects?stats=1")
        assert res.status_code == 200

    @patch("routes.projects.projects.sqlite3.connect")
    @patch("routes.projects.projects.os.path.exists")
    def test_stats_with_db(self, mock_exists, mock_connect, client):
        mock_exists.return_value = True
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            {"project": "test-project", "event_type": "render", "count": 5}
        ]
        res = client.get("/api/projects?stats=1")
        assert res.status_code == 200
        data = res.get_json()
        assert data[0]["stats"]["renders"] == 5

    @patch("routes.projects.projects.sqlite3.connect")
    @patch("routes.projects.projects.os.path.exists")
    def test_stats_with_db_exception(self, mock_exists, mock_connect, client):
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("db error")
        res = client.get("/api/projects?stats=1")
        assert res.status_code == 200

    @patch("routes.projects.projects.shutil.copytree")
    def test_fork_project_fails(self, mock_copytree, client):
        mock_copytree.side_effect = Exception("copy failed")
        res = client.post("/api/projects/test-project/fork", json={"new_slug": "ab-cd"})
        assert res.status_code == 500

    @patch("routes.projects.projects.json.dump")
    def test_update_assembly_steps_fails(self, mock_dump, client):
        mock_dump.side_effect = Exception("dump failed")
        res = client.put("/api/projects/test-project/manifest/assembly-steps", json={"assembly_steps": []})
        assert res.status_code == 500

