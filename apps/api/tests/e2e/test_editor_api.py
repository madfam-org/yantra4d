"""Tests for SCAD file editor API routes."""
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

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test", "slug": "my-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")
    (project_dir / "helper.scad").write_text("module base() { cube(5); }")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestListFiles:
    def test_list_files(self, client):
        res = client.get("/api/projects/my-project/files")
        assert res.status_code == 200
        data = res.get_json()
        paths = [f["path"] for f in data]
        assert "main.scad" in paths
        assert "helper.scad" in paths

    def test_list_files_skips_hidden(self, client, tmp_path):
        hidden = tmp_path / "my-project" / ".hidden"
        hidden.mkdir()
        (hidden / "secret.scad").write_text("cube(1);")
        res = client.get("/api/projects/my-project/files")
        data = res.get_json()
        paths = [f["path"] for f in data]
        assert all(".hidden" not in p for p in paths)

    def test_list_files_nonexistent_project(self, client):
        res = client.get("/api/projects/nonexistent/files")
        assert res.status_code == 404


class TestReadFile:
    def test_read_file(self, client):
        res = client.get("/api/projects/my-project/files/main.scad")
        assert res.status_code == 200
        data = res.get_json()
        assert data["content"] == "cube(10);"
        assert data["path"] == "main.scad"

    def test_read_nonexistent_file(self, client):
        res = client.get("/api/projects/my-project/files/missing.scad")
        assert res.status_code == 404

    def test_read_non_scad_file(self, client):
        res = client.get("/api/projects/my-project/files/project.json")
        assert res.status_code == 400

    def test_read_path_traversal(self, client):
        res = client.get("/api/projects/my-project/files/../../../etc/passwd")
        assert res.status_code == 400


class TestWriteFile:
    def test_write_file(self, client):
        res = client.put("/api/projects/my-project/files/main.scad", json={"content": "cube(20);"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["size"] == len("cube(20);")

    def test_write_no_content(self, client):
        res = client.put("/api/projects/my-project/files/main.scad", json={})
        assert res.status_code == 400

    def test_write_nonexistent_file(self, client):
        res = client.put("/api/projects/my-project/files/missing.scad", json={"content": "x"})
        assert res.status_code == 404

    def test_write_too_large(self, client):
        big = "x" * (512 * 1024 + 1)
        res = client.put("/api/projects/my-project/files/main.scad", json={"content": big})
        assert res.status_code == 400

    def test_write_non_scad(self, client):
        res = client.put("/api/projects/my-project/files/readme.txt", json={"content": "hi"})
        assert res.status_code == 400

    @patch("routes.editor.editor.git_init")
    def test_write_auto_inits_git(self, mock_git_init, client):
        client.put("/api/projects/my-project/files/main.scad", json={"content": "cube(30);"})
        mock_git_init.assert_called_once()


class TestCreateFile:
    def test_create_file(self, client):
        res = client.post("/api/projects/my-project/files", json={
            "path": "new.scad", "content": "sphere(5);",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["path"] == "new.scad"

    def test_create_no_path(self, client):
        res = client.post("/api/projects/my-project/files", json={"content": "x"})
        assert res.status_code == 400

    def test_create_duplicate(self, client):
        res = client.post("/api/projects/my-project/files", json={
            "path": "main.scad", "content": "x",
        })
        assert res.status_code == 409

    def test_create_non_scad(self, client):
        res = client.post("/api/projects/my-project/files", json={
            "path": "readme.txt", "content": "hi",
        })
        assert res.status_code == 400

    def test_create_too_large(self, client):
        big = "x" * (512 * 1024 + 1)
        res = client.post("/api/projects/my-project/files", json={
            "path": "big.scad", "content": big,
        })
        assert res.status_code == 400

    def test_create_subdirectory(self, client):
        res = client.post("/api/projects/my-project/files", json={
            "path": "sub/nested.scad", "content": "cube(1);",
        })
        assert res.status_code == 201

    def test_create_path_traversal(self, client):
        res = client.post("/api/projects/my-project/files", json={
            "path": "../../evil.scad", "content": "x",
        })
        assert res.status_code == 400


class TestDeleteFile:
    def test_delete_file(self, client):
        res = client.delete("/api/projects/my-project/files/helper.scad")
        assert res.status_code == 200
        data = res.get_json()
        assert data["deleted"] == "helper.scad"

    def test_delete_nonexistent(self, client):
        res = client.delete("/api/projects/my-project/files/missing.scad")
        assert res.status_code == 404

    def test_delete_non_scad(self, client):
        res = client.delete("/api/projects/my-project/files/project.json")
        assert res.status_code == 400

    def test_delete_path_traversal(self, client):
        res = client.delete("/api/projects/my-project/files/../../etc/passwd")
        assert res.status_code == 400
