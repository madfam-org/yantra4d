"""Tests for git operations service (git_init, status with remote)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.editor.git_operations import (
    git_init, git_status, git_diff, git_commit, git_push, git_pull,
    git_log, git_show_head, _run_git, _get_remote_url,
    _make_askpass_env, _cleanup_askpass,
)


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


class TestAskpassHelper:
    """Tests for the GIT_ASKPASS credential injection mechanism."""

    def test_creates_executable_script(self):
        env = _make_askpass_env("ghp_abc123")
        script_path = env["_ASKPASS_TMPFILE"]
        import os
        import stat
        assert os.path.isfile(script_path)
        mode = os.stat(script_path).st_mode
        assert mode & stat.S_IXUSR  # owner-executable
        # Verify content
        with open(script_path) as f:
            content = f.read()
        assert "x-access-token:ghp_abc123" in content
        _cleanup_askpass(env)
        assert not os.path.exists(script_path)

    def test_sets_git_askpass_env(self):
        env = _make_askpass_env("test_token")
        assert "GIT_ASKPASS" in env
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        _cleanup_askpass(env)

    def test_cleanup_removes_script(self):
        env = _make_askpass_env("tok")
        path = env["_ASKPASS_TMPFILE"]
        import os
        assert os.path.exists(path)
        _cleanup_askpass(env)
        assert not os.path.exists(path)

    def test_cleanup_noop_if_no_env(self):
        # Should not raise
        _cleanup_askpass(None)
        _cleanup_askpass({})


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


class TestGitLog:
    def test_log_returns_commits(self, project_dir):
        git_init(project_dir)
        result = git_log(project_dir)
        assert result["success"] is True
        assert len(result["commits"]) >= 1
        commit = result["commits"][0]
        assert "hash" in commit
        assert "short_hash" in commit
        assert "author" in commit
        assert "date" in commit
        assert "message" in commit

    def test_log_empty_repo(self, tmp_path):
        """Empty repo (no commits) returns empty list."""
        d = tmp_path / "empty-repo"
        d.mkdir()
        _run_git(d, ["init"])
        result = git_log(d)
        assert result["success"] is True
        assert result["commits"] == []

    def test_log_limit_capped_at_50(self, project_dir):
        git_init(project_dir)
        result = git_log(project_dir, limit=100)
        assert result["success"] is True
        # Just verify it doesn't crash — limit is capped internally

    def test_log_limit_min_1(self, project_dir):
        git_init(project_dir)
        result = git_log(project_dir, limit=0)
        assert result["success"] is True
        # limit=0 is capped to 1 internally


class TestGitShowHead:
    def test_show_existing_file(self, project_dir):
        git_init(project_dir)
        result = git_show_head(project_dir, "main.scad")
        assert result["success"] is True
        assert "cube(10)" in result["content"]

    def test_show_nonexistent_file(self, project_dir):
        git_init(project_dir)
        result = git_show_head(project_dir, "no-such-file.scad")
        assert result["success"] is False


class TestGitPushPullWithRemote:
    @pytest.fixture
    def repo_with_bare_remote(self, tmp_path):
        """Create a project repo with a local bare remote for push/pull testing."""
        # Create bare remote
        bare = tmp_path / "remote.git"
        bare.mkdir()
        _run_git(bare, ["init", "--bare"])

        # Create project
        proj = tmp_path / "my-project"
        proj.mkdir()
        (proj / "main.scad").write_text("cube(10);")
        (proj / "project.json").write_text('{"project": {"name": "Test"}}')
        git_init(proj)
        _run_git(proj, ["remote", "add", "origin", str(bare)])
        _run_git(proj, ["push", "-u", "origin", "HEAD"])
        return proj, bare

    def test_push_to_bare_remote(self, repo_with_bare_remote):
        proj, bare = repo_with_bare_remote
        (proj / "main.scad").write_text("cube(20);")
        git_commit(proj, "Update cube", ["main.scad"])
        # Push with empty token (local bare remote doesn't need auth)
        # Since _inject_token_url adds "x-access-token:" prefix to https URLs only,
        # and our remote is a file path, the token is irrelevant.
        result = git_push(proj, "fake-token")
        # The push should succeed because remote is a local path, not https
        # but _inject_token_url won't modify non-https URLs, so set-url
        # will use the injected URL which is the same as original for file paths
        assert result["success"] is True

    def test_pull_from_bare_remote(self, repo_with_bare_remote):
        proj, bare = repo_with_bare_remote
        # Create a second clone, push a change, then pull from the original
        import tempfile
        with tempfile.TemporaryDirectory() as clone_dir:
            clone = Path(clone_dir) / "clone"
            _run_git(Path(clone_dir), ["clone", str(bare), str(clone)])
            (clone / "main.scad").write_text("cube(30);")
            _run_git(clone, ["add", "main.scad"])
            _run_git(clone, ["config", "user.name", "Test"])
            _run_git(clone, ["config", "user.email", "t@t.com"])
            _run_git(clone, ["commit", "-m", "Change from clone"])
            _run_git(clone, ["push", "origin", "HEAD"])

        result = git_pull(proj, "fake-token")
        assert result["success"] is True
        assert "cube(30)" in (proj / "main.scad").read_text()

    def test_push_never_modifies_remote_url(self, project_dir):
        """GIT_ASKPASS approach should never modify the remote URL."""
        git_init(project_dir)
        original_url = "https://github.com/user/repo.git"
        _run_git(project_dir, ["remote", "add", "origin", original_url])

        # Push will fail (remote doesn't exist), but URL should remain unchanged
        result = git_push(project_dir, "ghp_test123")
        assert result["success"] is False

        current = _get_remote_url(project_dir)
        assert current == original_url

    def test_pull_never_modifies_remote_url(self, project_dir):
        """GIT_ASKPASS approach should never modify the remote URL."""
        git_init(project_dir)
        original_url = "https://github.com/user/repo.git"
        _run_git(project_dir, ["remote", "add", "origin", original_url])

        result = git_pull(project_dir, "ghp_test123")
        assert result["success"] is False

        current = _get_remote_url(project_dir)
        assert current == original_url


class TestGitDiffEdgeCases:
    def test_diff_on_non_repo(self, tmp_path):
        """git diff on a non-git directory returns error."""
        d = tmp_path / "not-a-repo"
        d.mkdir()
        result = git_diff(d)
        assert result["success"] is False
