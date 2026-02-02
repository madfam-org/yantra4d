"""Tests for git operations service (git_init, status with remote)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.git_operations import git_init, git_status, _run_git


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory."""
    d = tmp_path / "my-project"
    d.mkdir()
    (d / "main.scad").write_text("cube(10);")
    (d / "project.json").write_text('{"project": {"name": "Test"}}')
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
