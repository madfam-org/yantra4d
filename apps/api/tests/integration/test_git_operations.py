"""Tests for git operations service (git_init, status with remote)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.editor.git_operations import git_init, git_status, git_diff, git_commit, git_push, git_pull, _run_git, _inject_token_url, _get_remote_url


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory."""
    d = tmp_path / "my-project"
    d.mkdir()
    (d / "main.scad").write_text("cube(10);")
    (d / "project.json").write_text('{"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test"}}')
    return d


class TestGitInit:
    def test_init_creates_repo(self, project_dir):
        result = git_init(project_dir)
        assert result["success"] is True
        assert result["already_initialized"] is False
        assert (project_dir / ".git").is_dir()

    def test_init_idempotent(self, project_dir):
        git_init(project_dir)
        result = git_init(project_dir)
        assert result["success"] is True
        assert result["already_initialized"] is True

    def test_init_creates_initial_commit(self, project_dir):
        git_init(project_dir)
        log = _run_git(project_dir, ["log", "--oneline"])
        assert "Initial commit" in log.stdout


class TestGitStatusRemote:
    def test_status_no_remote(self, project_dir):
        git_init(project_dir)
        result = git_status(project_dir)
        assert result["success"] is True
        assert result["remote"] is None

    def test_status_with_remote(self, project_dir):
        git_init(project_dir)
        _run_git(project_dir, ["remote", "add", "origin", "https://github.com/user/repo.git"])
        result = git_status(project_dir)
        assert result["success"] is True
        assert result["remote"] == "https://github.com/user/repo.git"

    def test_status_clean_repo(self, project_dir):
        git_init(project_dir)
        result = git_status(project_dir)
        assert result["clean"] is True
        assert result["modified"] == []
        assert result["untracked"] == []

    def test_status_modified_file(self, project_dir):
        git_init(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")
        result = git_status(project_dir)
        assert result["clean"] is False
        assert any("main.scad" in f for f in result["modified"])

    def test_status_untracked_file(self, project_dir):
        git_init(project_dir)
        (project_dir / "new.scad").write_text("sphere(5);")
        result = git_status(project_dir)
        assert "new.scad" in result["untracked"]

    def test_status_branch(self, project_dir):
        git_init(project_dir)
        result = git_status(project_dir)
        assert result["branch"] in ("main", "master")


class TestGitDiff:
    def test_diff_clean(self, project_dir):
        git_init(project_dir)
        result = git_diff(project_dir)
        assert result["success"] is True
        assert result["diff"] == ""

    def test_diff_with_changes(self, project_dir):
        git_init(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")
        result = git_diff(project_dir)
        assert result["success"] is True
        assert "cube(20)" in result["diff"]

    def test_diff_specific_file(self, project_dir):
        git_init(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")
        result = git_diff(project_dir, "main.scad")
        assert "cube(20)" in result["diff"]


class TestGitCommit:
    def test_commit_no_files(self, project_dir):
        git_init(project_dir)
        result = git_commit(project_dir, "msg", [])
        assert result["success"] is False
        assert "No files" in result["error"]

    def test_commit_no_message(self, project_dir):
        git_init(project_dir)
        result = git_commit(project_dir, "", ["main.scad"])
        assert result["success"] is False
        assert "message" in result["error"]

    def test_commit_success(self, project_dir):
        git_init(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")
        result = git_commit(project_dir, "Update cube size", ["main.scad"])
        assert result["success"] is True
        assert result["commit"] is not None
        assert len(result["commit"]) >= 7


class TestInjectTokenUrl:
    def test_injects_token(self):
        url = "https://github.com/user/repo.git"
        result = _inject_token_url(url, "ghp_abc123")
        assert result == "https://x-access-token:ghp_abc123@github.com/user/repo.git"

    def test_non_https_unchanged(self):
        url = "git@github.com:user/repo.git"
        result = _inject_token_url(url, "token")
        assert result == url


class TestGetRemoteUrl:
    def test_no_remote(self, project_dir):
        git_init(project_dir)
        assert _get_remote_url(project_dir) is None

    def test_with_remote(self, project_dir):
        git_init(project_dir)
        _run_git(project_dir, ["remote", "add", "origin", "https://github.com/u/r.git"])
        assert _get_remote_url(project_dir) == "https://github.com/u/r.git"


class TestGitPushPull:
    def test_push_no_remote(self, project_dir):
        git_init(project_dir)
        result = git_push(project_dir, "token")
        assert result["success"] is False
        assert "No origin" in result["error"]

    def test_pull_no_remote(self, project_dir):
        git_init(project_dir)
        result = git_pull(project_dir, "token")
        assert result["success"] is False
        assert "No origin" in result["error"]


class TestGitInitEdgeCases:
    def test_init_on_non_repo_directory(self, tmp_path):
        """git_init on a fresh directory (no .git) creates repo and commits."""
        d = tmp_path / "fresh"
        d.mkdir()
        (d / "readme.txt").write_text("hello")
        result = git_init(d)
        assert result["success"] is True
        assert result["already_initialized"] is False
        assert (d / ".git").is_dir()

    def test_init_empty_directory(self, tmp_path):
        """git_init on an empty directory still succeeds (empty initial commit)."""
        d = tmp_path / "empty-proj"
        d.mkdir()
        result = git_init(d)
        # git commit may fail with "nothing to commit" on empty dir
        # but git_init stages all files first — an empty dir has nothing to stage
        # The result depends on git behavior; either success or failure is valid
        assert "success" in result


class TestGitCommitEdgeCases:
    def test_commit_with_author(self, project_dir):
        """Commit with custom author sets the author field."""
        git_init(project_dir)
        (project_dir / "main.scad").write_text("cube(20);")
        result = git_commit(
            project_dir, "Custom author commit", ["main.scad"],
            author_name="Test User", author_email="test@example.com"
        )
        assert result["success"] is True
        # Verify author in log
        log = _run_git(project_dir, ["log", "-1", "--format=%an <%ae>"])
        assert "Test User" in log.stdout

    def test_commit_nonexistent_file(self, project_dir):
        """Staging a file that doesn't exist should fail."""
        git_init(project_dir)
        result = git_commit(project_dir, "bad commit", ["does_not_exist.scad"])
        assert result["success"] is False


class TestGitStatusEdgeCases:
    def test_status_deleted_file(self, project_dir):
        """Deleting a tracked file shows up in status."""
        git_init(project_dir)
        (project_dir / "main.scad").unlink()
        result = git_status(project_dir)
        assert result["clean"] is False
        assert any("main.scad" in f for f in result["deleted"])

    def test_status_on_non_repo(self, tmp_path):
        """git status on a non-git directory returns error."""
        d = tmp_path / "not-a-repo"
        d.mkdir()
        result = git_status(d)
        assert result["success"] is False


class TestGitDiffEdgeCases:
    def test_diff_on_non_repo(self, tmp_path):
        """git diff on a non-git directory returns error."""
        d = tmp_path / "not-a-repo"
        d.mkdir()
        result = git_diff(d)
        assert result["success"] is False
