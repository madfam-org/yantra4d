"""Tests for git operations API routes."""
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
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])

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

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _init_git(project_dir):
    """Initialize git repo in project dir."""
    from services.editor.git_operations import git_init
    git_init(project_dir)


def _make_github_project(tmp_path, slug="my-project"):
    """Add project.meta.json and .git to make it a GitHub project."""
    project_dir = tmp_path / slug
    _init_git(project_dir)
    meta = {"source": {"type": "github", "repo_url": "https://github.com/user/repo.git"}}
    (project_dir / "project.meta.json").write_text(json.dumps(meta))
    return project_dir


class TestGitStatus:
    def test_status_success(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.get("/api/projects/my-project/git/status")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "branch" in data

    def test_status_no_git(self, client):
        res = client.get("/api/projects/my-project/git/status")
        assert res.status_code == 400

    def test_status_nonexistent_project(self, client):
        res = client.get("/api/projects/nonexistent/git/status")
        assert res.status_code == 404


class TestGitDiff:
    def test_diff_clean(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.get("/api/projects/my-project/git/diff")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_diff_with_file_param(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.get("/api/projects/my-project/git/diff?file=main.scad")
        assert res.status_code == 200

    def test_diff_no_git(self, client):
        res = client.get("/api/projects/my-project/git/diff")
        assert res.status_code == 400


class TestGitLog:
    def test_log_success(self, client, tmp_path):
        project_dir = tmp_path / "my-project"
        _init_git(project_dir)
        # Make a commit so there's history
        (project_dir / "main.scad").write_text("cube(20);")
        from services.editor.git_operations import git_commit
        git_commit(project_dir, "Initial commit", ["main.scad"])

        res = client.get("/api/projects/my-project/git/log")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert "commits" in data
        assert len(data["commits"]) >= 1

    def test_log_with_limit(self, client, tmp_path):
        project_dir = tmp_path / "my-project"
        _init_git(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")
        from services.editor.git_operations import git_commit
        git_commit(project_dir, "Commit 1", ["main.scad"])

        res = client.get("/api/projects/my-project/git/log?limit=1")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["commits"]) <= 1

    def test_log_invalid_limit(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.get("/api/projects/my-project/git/log?limit=0")
        assert res.status_code == 400

    def test_log_no_git(self, client):
        res = client.get("/api/projects/my-project/git/log")
        assert res.status_code == 400

    def test_log_nonexistent_project(self, client):
        res = client.get("/api/projects/nonexistent/git/log")
        assert res.status_code == 404


class TestGitCommit:
    def test_commit_success(self, client, tmp_path):
        project_dir = tmp_path / "my-project"
        _init_git(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")

        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "Update cube size",
            "files": ["main.scad"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_commit_missing_message(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "",
            "files": ["main.scad"],
        })
        assert res.status_code == 400

    def test_commit_missing_files(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "msg",
            "files": [],
        })
        assert res.status_code == 400

    def test_commit_no_body(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", content_type="application/json")
        assert res.status_code == 400

    def test_commit_no_git(self, client):
        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "msg", "files": ["main.scad"],
        })
        assert res.status_code == 400


class TestGitPush:
    @patch("routes.editor.git_ops.get_github_token", return_value="ghp_test123")
    @patch("routes.editor.git_ops.git_push", return_value={"success": True})
    def test_push_success(self, mock_push, mock_token, client, tmp_path):
        _make_github_project(tmp_path)
        res = client.post("/api/projects/my-project/git/push")
        assert res.status_code == 200

    @patch("routes.editor.git_ops.get_github_token", return_value=None)
    def test_push_no_token(self, mock_token, client, tmp_path):
        _make_github_project(tmp_path)
        res = client.post("/api/projects/my-project/git/push")
        assert res.status_code == 401

    def test_push_no_meta(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/push")
        assert res.status_code == 400

    def test_push_nonexistent(self, client):
        res = client.post("/api/projects/nonexistent/git/push")
        assert res.status_code == 404


class TestGitPull:
    @patch("routes.editor.git_ops.get_github_token", return_value="ghp_test123")
    @patch("routes.editor.git_ops.git_pull", return_value={"success": True})
    def test_pull_success(self, mock_pull, mock_token, client, tmp_path):
        _make_github_project(tmp_path)
        res = client.post("/api/projects/my-project/git/pull")
        assert res.status_code == 200

    @patch("routes.editor.git_ops.get_github_token", return_value=None)
    def test_pull_no_token(self, mock_token, client, tmp_path):
        _make_github_project(tmp_path)
        res = client.post("/api/projects/my-project/git/pull")
        assert res.status_code == 401


class TestConnectRemote:
    def test_connect_success(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_connect_invalid_url(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "not-a-url",
        })
        assert res.status_code == 400

    def test_connect_empty_url(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "",
        })
        assert res.status_code == 400

    def test_connect_no_git(self, client):
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        assert res.status_code == 400

    def test_connect_creates_meta(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        assert res.status_code == 200
        meta = json.loads((tmp_path / "my-project" / "project.meta.json").read_text())
        assert meta["source"]["type"] == "github"
        assert meta["source"]["repo_url"] == "https://github.com/user/repo.git"

    def test_connect_update_existing_remote(self, client, tmp_path):
        project_dir = tmp_path / "my-project"
        _init_git(project_dir)
        # First connect
        client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        # Update
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo2.git",
        })
        assert res.status_code == 200

class TestGitRenderHead:
    @patch("routes.editor.git_ops.git_archive_head")
    @patch("routes.editor.git_ops.run_openscad_render")
    def test_render_head_success(self, mock_render, mock_archive, client, tmp_path):
        _init_git(tmp_path / "my-project")

        # Mock successful archive
        def fake_archive(src, dst):
            with open(dst / "main.scad", "w") as f:
                f.write("test")
            return {"success": True}
        mock_archive.side_effect = fake_archive
        mock_render.return_value = (True, "output")

        payload = {"project": "my-project", "parts": ["main"], "stl_prefix": "pref_", "export_format": "stl", "params": {}, "mode_map": {}, "scad_filename": "main.scad", "scad_file": "main.scad"}
        res = client.post("/api/projects/my-project/git/render-head", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"

    @patch("routes.editor.git_ops.git_archive_head")
    def test_render_head_no_scad(self, mock_archive, client, tmp_path):
        _init_git(tmp_path / "my-project")
        mock_archive.return_value = {"success": True}
        res = client.post("/api/projects/my-project/git/render-head", json={"project": "my-project"})
        # Archive succeeds but SCAD file doesn't exist in HEAD → 404
        assert res.status_code == 404

    @patch("routes.editor.git_ops.git_archive_head")
    def test_render_head_archive_fails(self, mock_archive, client, tmp_path):
        _init_git(tmp_path / "my-project")
        mock_archive.return_value = {"success": False, "error": "fatal"}
        payload = {"project": "my-project", "parts": ["main"], "stl_prefix": "pref_", "export_format": "stl", "params": {}, "mode_map": {}, "scad_filename": "main.scad", "scad_file": "main.scad"}
        res = client.post("/api/projects/my-project/git/render-head", json=payload)
        assert res.status_code == 500

class TestGitOpsErrors:
    def test_commit_message_too_long(self, client, tmp_path):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", json={"message": "x"*1001, "files": ["ab"]})
        assert res.status_code == 400

    @patch("routes.editor.git_ops.git_status")
    def test_status_fails(self, mock_status, client, tmp_path):
        _init_git(tmp_path / "my-project")
        mock_status.return_value = {"success": False, "error": "err"}
        res = client.get("/api/projects/my-project/git/status")
        assert res.status_code == 500
