"""Tests for project fork API endpoint."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path):
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
    # Add a .git dir and .analytics.db to ensure they are excluded
    (project_dir / ".git").mkdir()
    (project_dir / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (project_dir / ".analytics.db").write_text("fake db")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestForkProject:
    def test_fork_success(self, client, tmp_path):
        res = client.post("/api/projects/test-project/fork", json={"new_slug": "my-test-project"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["slug"] == "my-test-project"

        # Verify files copied
        forked = tmp_path / "my-test-project"
        assert (forked / "project.json").is_file()
        assert (forked / "main.scad").is_file()

        # Verify .git and .analytics.db excluded
        assert not (forked / ".git").exists()
        assert not (forked / ".analytics.db").exists()

        # Verify meta written
        meta = json.loads((forked / "project.meta.json").read_text())
        assert meta["source"]["type"] == "fork"
        assert meta["source"]["forked_from"] == "test-project"

    def test_fork_invalid_slug(self, client):
        res = client.post("/api/projects/test-project/fork", json={"new_slug": "A B"})
        assert res.status_code == 400

    def test_fork_missing_slug(self, client):
        res = client.post("/api/projects/test-project/fork", json={})
        assert res.status_code == 400

    def test_fork_nonexistent_project(self, client):
        res = client.post("/api/projects/nonexistent/fork", json={"new_slug": "my-copy"})
        assert res.status_code == 404

    def test_fork_slug_already_exists(self, client, tmp_path):
        # First fork
        client.post("/api/projects/test-project/fork", json={"new_slug": "my-copy"})
        # Second fork with same slug
        res = client.post("/api/projects/test-project/fork", json={"new_slug": "my-copy"})
        assert res.status_code == 409
