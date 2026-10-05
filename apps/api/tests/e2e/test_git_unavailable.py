"""Behaviour when the host has no ``git`` binary.

Version control is an optional capability of the editor. Without git:
- a save into a cartridge with no ``.git`` (a fresh fork) still succeeds,
  untracked, instead of failing on the auto-initialisation;
- the explicit version-control routes and GitHub import/sync answer 503
  ``git_unavailable`` instead of a 500 or a misleading "not accessible".

The binary is made missing for real: PATH points at an empty directory, so
both ``shutil.which`` and ``subprocess`` fail exactly as on a host without git.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

MANIFEST = {
    "project": {
        "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
        "name": "Box", "slug": "box", "version": "1.0.0",
    },
    "modes": [{
        "id": "default", "scad_file": "main.scad", "label": {"en": "Default"},
        "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"},
    }],
    "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
    "parameters": [],
    "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
}


@pytest.fixture
def no_git(tmp_path_factory, monkeypatch):
    empty = tmp_path_factory.mktemp("empty-path")
    monkeypatch.setenv("PATH", str(empty))
    assert shutil.which("git") is None
    return empty


@pytest.fixture
def client(tmp_path):
    cart = tmp_path / "box"
    cart.mkdir()
    (cart / "project.json").write_text(json.dumps(MANIFEST))
    (cart / "main.scad").write_text("cube(10);\n")

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _fork(client):
    res = client.post("/api/projects/box/fork", json={"new_slug": "my-box"})
    assert res.status_code == 200, res.get_json()


class TestWrapper:
    def test_run_git_raises_a_typed_error(self, no_git, tmp_path):
        from services.editor.git_operations import (
            GIT_UNAVAILABLE,
            GitUnavailableError,
            _run_git,
        )
        with pytest.raises(GitUnavailableError, match=GIT_UNAVAILABLE):
            _run_git(tmp_path, ["status"])

    def test_git_init_returns_a_structured_failure(self, no_git, tmp_path):
        from services.editor.git_operations import git_init
        assert git_init(tmp_path) == {
            "success": False, "error": "git unavailable", "git_unavailable": True,
        }
        assert not (tmp_path / ".git").exists()

    def test_git_archive_head_returns_a_structured_failure(self, no_git, tmp_path):
        from services.editor.git_operations import git_archive_head
        assert git_archive_head(tmp_path, tmp_path / "out")["git_unavailable"] is True

    def test_a_vanished_cwd_is_not_reported_as_missing_git(self, tmp_path):
        """With git present, FileNotFoundError from a missing cwd stays itself."""
        from services.editor.git_operations import (
            GitUnavailableError,
            _run_git,
            git_available,
        )
        assert git_available(), "this check runs on a host with git (CI, dev)"
        with pytest.raises(FileNotFoundError) as info:
            _run_git(tmp_path / "gone", ["status"])
        assert not isinstance(info.value, GitUnavailableError)

    def test_auto_git_resolution_does_not_raise(self, no_git, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import resolve_project_dir
        (tmp_path / "proj").mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        project_dir, err = resolve_project_dir("proj", auto_git=True)
        assert err is None
        assert project_dir == (tmp_path / "proj").resolve()


class TestSavesProceedWithoutGit:
    def test_first_save_into_a_fresh_fork_succeeds_untracked(self, client, no_git, user_projects_dir):
        _fork(client)
        res = client.put("/api/projects/my-box/files/main.scad", json={"content": "cube(20);\n"})

        assert res.status_code == 200, res.get_json()
        fork = user_projects_dir / "my-box"
        assert (fork / "main.scad").read_text() == "cube(20);\n"
        assert not (fork / ".git").exists()

    def test_create_and_delete_file_in_a_fork_succeed(self, client, no_git, user_projects_dir):
        _fork(client)
        res = client.post("/api/projects/my-box/files", json={"path": "extra.scad", "content": "sphere(1);\n"})
        assert res.status_code in (200, 201), res.get_json()
        res = client.delete("/api/projects/my-box/files/extra.scad")
        assert res.status_code == 200, res.get_json()
        assert not (user_projects_dir / "my-box" / "extra.scad").exists()

    def test_assembly_steps_save_in_a_fork_succeeds(self, client, no_git):
        _fork(client)
        res = client.put("/api/projects/my-box/manifest/assembly-steps", json={"assembly_steps": []})
        assert res.status_code == 200, res.get_json()


class TestVersionControlRoutesAnswer503:
    @pytest.mark.parametrize("method,path,body", [
        ("get", "/api/projects/my-box/git/status", None),
        ("get", "/api/projects/my-box/git/diff", None),
        ("get", "/api/projects/my-box/git/log", None),
        ("post", "/api/projects/my-box/git/commit", {"message": "m", "files": ["main.scad"]}),
        ("post", "/api/projects/my-box/git/push", {}),
        ("post", "/api/projects/my-box/git/pull", {}),
        ("post", "/api/projects/my-box/git/connect-remote", {"remote_url": "https://github.com/example/repo"}),
        ("post", "/api/projects/my-box/git/render-head", {"project": "my-box", "mode": "default", "parameters": {}}),
    ])
    def test_git_routes(self, client, no_git, method, path, body):
        _fork(client)
        call = getattr(client, method)
        res = call(path, json=body) if body is not None else call(path)

        assert res.status_code == 503, res.get_json()
        assert res.get_json()["error_code"] == "git_unavailable"

    @pytest.mark.parametrize("path,body", [
        ("/api/github/validate", {"repo_url": "https://github.com/example/repo"}),
        ("/api/github/import", {"repo_url": "https://github.com/example/repo", "slug": "imported", "manifest": MANIFEST}),
        ("/api/github/sync", {"slug": "imported"}),
    ])
    def test_github_routes(self, client, no_git, path, body):
        res = client.post(path, json=body)

        assert res.status_code == 503, res.get_json()
        assert res.get_json()["error_code"] == "git_unavailable"

    def test_git_routes_still_work_with_git(self, client):
        from services.editor.git_operations import git_available
        assert git_available(), "this check runs on a host with git (CI, dev)"
        _fork(client)
        client.put("/api/projects/my-box/files/main.scad", json={"content": "cube(20);\n"})
        res = client.get("/api/projects/my-box/git/log")
        assert res.status_code == 200, res.get_json()
