"""Tests for git operations API routes."""
import json
import shutil
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
    # Local development mode (auth off + debugger on): the same unlock that
    # opens private projects lets any caller write forks and imports, so these
    # tests exercise write mechanics without minting identities. Ownership is
    # covered in test_cartridge_ownership_api.py.
    flask_app.debug = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _init_git(project_dir):
    """Initialize git repo in project dir."""
    from services.editor.git_operations import git_init
    git_init(project_dir)


def _as_fork(project_dir, *, git=True):
    """Make the project a fork: commit and connect-remote write only forks and imports."""
    if git:
        _init_git(project_dir)
    meta = {"source": {"type": "fork", "forked_from": "x"}}
    (project_dir / "project.meta.json").write_text(json.dumps(meta))
    return project_dir


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
        _as_fork(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")

        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "Update cube size",
            "files": ["main.scad"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_commit_missing_message(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "",
            "files": ["main.scad"],
        })
        assert res.status_code == 400

    def test_commit_missing_files(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", json={
            "message": "msg",
            "files": [],
        })
        assert res.status_code == 400

    def test_commit_no_body(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", content_type="application/json")
        assert res.status_code == 400

    def test_commit_no_git(self, client, tmp_path):
        _as_fork(tmp_path / "my-project", git=False)
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
        # No project.meta.json: not a fork or import, so not writable through
        # the API — the write guard refuses before the route looks for a remote.
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/push")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "read_only_cartridge"

    @patch("routes.editor.git_ops.get_github_token", return_value="tok")
    def test_push_fork_without_remote(self, mock_token, client, tmp_path):
        _as_fork(tmp_path / "my-project")
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
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_connect_invalid_url(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "not-a-url",
        })
        assert res.status_code == 400

    def test_connect_empty_url(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "",
        })
        assert res.status_code == 400

    def test_connect_no_git(self, client, tmp_path):
        _as_fork(tmp_path / "my-project", git=False)
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        assert res.status_code == 400

    def test_connect_turns_a_fork_into_a_github_project(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        assert res.status_code == 200
        meta = json.loads((tmp_path / "my-project" / "project.meta.json").read_text())
        assert meta["source"]["type"] == "github"
        assert meta["source"]["repo_url"] == "https://github.com/user/repo.git"

    def test_connect_update_existing_remote(self, client, tmp_path):
        project_dir = tmp_path / "my-project"
        _as_fork(project_dir)
        # First connect
        client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo.git",
        })
        # Update
        res = client.post("/api/projects/my-project/git/connect-remote", json={
            "remote_url": "https://github.com/user/repo2.git",
        })
        assert res.status_code == 200

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="needs the git binary")


@pytest.fixture
def queue(monkeypatch, tmp_path):
    """Route -> render queue -> real render worker (inline) -> channels -> route."""
    from inline_render_worker import install
    return install(monkeypatch, tmp_path / "static")


@pytest.fixture
def head_engine(monkeypatch):
    """Fake OpenSCAD inside the worker that records the file it was handed."""
    import render_worker

    seen = []

    def run(cmd, scad_path=None, is_cancelled=None):
        seen.append({"scad_path": scad_path, "content": Path(scad_path).read_text(),
                     "checkout": Path(scad_path).parent})
        Path(cmd[1]).write_bytes(b"solid x\nendsolid x\n")
        return True, "rendered"

    def to_glb(src, dst):
        Path(dst).write_bytes(b"glTF")
        return True

    cache_puts = []
    monkeypatch.setattr(render_worker, "build_openscad_command",
                        lambda out, scad, params, mode: ["openscad", out, scad])
    monkeypatch.setattr(render_worker, "run_openscad_render", run)
    monkeypatch.setattr(render_worker, "stl_to_glb", to_glb)
    monkeypatch.setattr(render_worker.render_cache, "put", lambda *a, **k: cache_puts.append(a))
    head_engine.seen = seen
    head_engine.cache_puts = cache_puts
    return head_engine


HEAD_PAYLOAD = {"project": "my-project", "mode": "default", "parameters": {}, "export_format": "stl"}


@requires_git
class TestGitRenderHead:
    def test_head_renders_on_the_worker_from_the_committed_tree(self, client, tmp_path, queue, head_engine):
        project_dir = tmp_path / "my-project"
        _init_git(project_dir)  # commits main.scad = "cube(10);"
        (project_dir / "main.scad").write_text("sphere(5); // uncommitted")

        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        (part,) = data["parts"]
        assert part["type"] == "main"
        assert part["url"].startswith("/static/my-project_") and part["url"].endswith("head_main.stl")
        assert part["viewer_url"].endswith("head_main.glb")
        assert "[main] rendered" in data["log"]

        # One worker job, sourced from HEAD by the worker itself.
        (task,) = queue.pushed
        assert task["stream"] is False
        assert task["source"] == {"kind": "git_head", "entry": "main.scad"}
        assert task["scad_path"] == "main.scad"  # relative: no working-tree path on the queue
        assert task["payload"]["cache_write"] is False
        assert head_engine.cache_puts == []

        # The engine read the COMMITTED file from a private checkout...
        (seen,) = head_engine.seen
        assert seen["content"] == "cube(10);"
        assert seen["checkout"].name.startswith("yantra_head_")
        assert project_dir.resolve() not in seen["checkout"].resolve().parents
        # ...which is gone once the job ends.
        assert not seen["checkout"].exists()

    def test_body_project_cannot_redirect_the_render(self, client, tmp_path, queue, head_engine):
        _init_git(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/render-head",
                          json={**HEAD_PAYLOAD, "project": "some-other-project"})
        assert res.status_code == 200
        assert queue.pushed[0]["payload"]["project_slug"] == "my-project"

    def test_scad_missing_in_head_is_404(self, client, tmp_path, queue, head_engine):
        import subprocess
        project_dir = tmp_path / "my-project"
        _init_git(project_dir)
        subprocess.run(["git", "rm", "-q", "--cached", "main.scad"], cwd=project_dir, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "untrack"], cwd=project_dir, check=True)
        assert (project_dir / "main.scad").is_file()  # still in the working tree

        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 404
        assert "does not exist in HEAD" in res.get_json()["error"]
        assert head_engine.seen == []

    def test_archive_failure_is_500(self, client, tmp_path, queue, head_engine, monkeypatch):
        import render_worker
        _init_git(tmp_path / "my-project")
        monkeypatch.setattr(render_worker, "git_archive_head",
                            lambda src, dst: {"success": False, "error": "fatal"})
        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 500
        assert res.get_json()["error"] == "fatal"
        assert head_engine.seen == []

    def test_worker_without_git_is_503_git_unavailable(self, client, tmp_path, queue, head_engine, monkeypatch):
        import render_worker

        from services.editor.git_operations import git_unavailable_result
        _init_git(tmp_path / "my-project")
        monkeypatch.setattr(render_worker, "git_archive_head", lambda src, dst: git_unavailable_result())
        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 503
        assert res.get_json()["error_code"] == "git_unavailable"
        assert head_engine.seen == []

    def test_engine_failure_is_logged_and_skipped(self, client, tmp_path, queue, head_engine, monkeypatch):
        import render_worker
        _init_git(tmp_path / "my-project")
        monkeypatch.setattr(render_worker, "run_openscad_render",
                            lambda cmd, scad_path=None, is_cancelled=None: (False, "parse error"))
        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 200
        data = res.get_json()
        assert data["parts"] == []
        assert "[main] HEAD render failed: parse error" in data["log"]

    def test_worker_unavailable_is_503(self, client, tmp_path, queue, head_engine):
        from services.engine import render_orchestrator
        _init_git(tmp_path / "my-project")
        queue.kv.pop(render_orchestrator.RENDER_WORKER_HEARTBEAT_KEY)
        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 503
        assert res.get_json()["error_code"] == "render_worker_unavailable"
        assert queue.pushed == []

    def test_no_git_repository_is_400(self, client, queue, head_engine):
        res = client.post("/api/projects/my-project/git/render-head", json=HEAD_PAYLOAD)
        assert res.status_code == 400
        assert queue.pushed == []


class TestGitOpsErrors:
    def test_commit_message_too_long(self, client, tmp_path):
        _as_fork(tmp_path / "my-project")
        res = client.post("/api/projects/my-project/git/commit", json={"message": "x"*1001, "files": ["ab"]})
        assert res.status_code == 400

    @patch("routes.editor.git_ops.git_status")
    def test_status_fails(self, mock_status, client, tmp_path):
        _init_git(tmp_path / "my-project")
        mock_status.return_value = {"success": False, "error": "err"}
        res = client.get("/api/projects/my-project/git/status")
        assert res.status_code == 500
