"""Tests for GitHub import service."""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


sys.path.insert(0, str(Path(__file__).parent.parent))

from services.editor.github_import import (
    validate_repo_url, _build_clone_url, _clean_repo_url,
    check_repo_exists, clone_repo, find_scad_files, check_manifest,
    validate_repo, import_repo, sync_repo,
)


class TestValidateRepoUrl:
    def test_valid_https(self):
        assert validate_repo_url("https://github.com/user/repo") is True

    def test_valid_with_git_suffix(self):
        assert validate_repo_url("https://github.com/user/repo.git") is True

    def test_valid_with_trailing_slash(self):
        assert validate_repo_url("https://github.com/user/repo/") is True

    def test_invalid_non_github(self):
        assert validate_repo_url("https://gitlab.com/user/repo") is False

    def test_invalid_no_repo(self):
        assert validate_repo_url("https://github.com/user") is False

    def test_empty(self):
        assert validate_repo_url("") is False


class TestBuildCloneUrl:
    def test_no_token(self):
        assert _build_clone_url("https://github.com/u/r") == "https://github.com/u/r"

    def test_with_token(self):
        result = _build_clone_url("https://github.com/u/r", "tok123")
        assert result == "https://x-access-token:tok123@github.com/u/r"

    def test_non_https_unchanged(self):
        assert _build_clone_url("git://github.com/u/r", "tok") == "git://github.com/u/r"


class TestCleanRepoUrl:
    def test_strips_credentials(self):
        assert _clean_repo_url("https://x-access-token:tok@github.com/u/r") == "https://github.com/u/r"

    def test_no_credentials(self):
        assert _clean_repo_url("https://github.com/u/r") == "https://github.com/u/r"


class TestCheckRepoExists:
    @patch("services.editor.github_import.subprocess.run")
    def test_accessible(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert check_repo_exists("https://github.com/u/r") is True

    @patch("services.editor.github_import.subprocess.run")
    def test_not_accessible(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128)
        assert check_repo_exists("https://github.com/u/r") is False

    @patch("services.editor.github_import.subprocess.run", side_effect=FileNotFoundError)
    def test_git_not_found(self, mock_run):
        assert check_repo_exists("https://github.com/u/r") is False

    @patch("services.editor.github_import.subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd="git", timeout=15))
    def test_timeout(self, mock_run):
        assert check_repo_exists("https://github.com/u/r") is False


class TestCloneRepo:
    @patch("services.editor.github_import.subprocess.run")
    def test_clone_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        dest = tmp_path / "repo"
        assert clone_repo("https://github.com/u/r", dest) is True

    @patch("services.editor.github_import.subprocess.run")
    def test_clone_shallow(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        dest = tmp_path / "repo"
        clone_repo("https://github.com/u/r", dest, shallow=True)
        cmd = mock_run.call_args_list[0][0][0]
        assert "--depth" in cmd

    @patch("services.editor.github_import.subprocess.run")
    def test_clone_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=128, stderr="fatal error")
        dest = tmp_path / "repo"
        assert clone_repo("https://github.com/u/r", dest) is False

    @patch("services.editor.github_import.subprocess.run", side_effect=FileNotFoundError)
    def test_clone_git_not_installed(self, mock_run, tmp_path):
        dest = tmp_path / "repo"
        assert clone_repo("https://github.com/u/r", dest) is False

    @patch("services.editor.github_import.subprocess.run")
    def test_clone_with_token_resets_remote(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        dest = tmp_path / "repo"
        clone_repo("https://github.com/u/r", dest, github_token="tok123")
        assert mock_run.call_count == 2  # clone + set-url


class TestFindScadFiles:
    def test_finds_scad_files(self, tmp_path):
        (tmp_path / "main.scad").write_text("cube(10);")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "helper.scad").write_text("sphere(5);")
        files = find_scad_files(tmp_path)
        assert len(files) == 2
        paths = [f["path"] for f in files]
        assert "main.scad" in paths

    def test_skips_hidden(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "hook.scad").write_text("x")
        (tmp_path / "main.scad").write_text("cube(10);")
        files = find_scad_files(tmp_path)
        assert len(files) == 1

    def test_empty_repo(self, tmp_path):
        assert find_scad_files(tmp_path) == []


class TestCheckManifest:
    def test_valid_manifest(self, tmp_path):
        (tmp_path / "project.json").write_text('{"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test"}}')
        result = check_manifest(tmp_path)
        assert result["project"]["name"] == "Test"

    def test_no_manifest(self, tmp_path):
        assert check_manifest(tmp_path) is None

    def test_invalid_json(self, tmp_path):
        (tmp_path / "project.json").write_text("not json")
        assert check_manifest(tmp_path) is None


class TestValidateRepo:
    def test_invalid_url(self):
        result = validate_repo("not-a-url")
        assert result["valid"] is False

    @patch("services.editor.github_import.check_repo_exists", return_value=False)
    def test_repo_not_found(self, mock_check):
        result = validate_repo("https://github.com/u/r")
        assert result["valid"] is False
        assert "not found" in result["error"].lower() or "not accessible" in result["error"].lower()

    @patch("services.editor.github_import.clone_repo", return_value=False)
    @patch("services.editor.github_import.check_repo_exists", return_value=True)
    def test_clone_failure(self, mock_check, mock_clone):
        result = validate_repo("https://github.com/u/r")
        assert result["valid"] is False

    @patch("services.editor.github_import.clone_repo")
    @patch("services.editor.github_import.check_repo_exists", return_value=True)
    def test_no_scad_files(self, mock_check, mock_clone):
        def fake_clone(url, dest, github_token=None, shallow=False):
            dest.mkdir(parents=True, exist_ok=True)
            return True
        mock_clone.side_effect = fake_clone
        result = validate_repo("https://github.com/u/r")
        assert result["valid"] is False
        assert "No .scad" in result["error"]

    @patch("services.editor.github_import.clone_repo")
    @patch("services.editor.github_import.check_repo_exists", return_value=True)
    def test_success(self, mock_check, mock_clone):
        def fake_clone(url, dest, github_token=None, shallow=False):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "main.scad").write_text("cube(10);")
            return True
        mock_clone.side_effect = fake_clone
        result = validate_repo("https://github.com/u/r")
        assert result["valid"] is True
        assert len(result["scad_files"]) == 1


class TestImportRepo:
    @patch("services.editor.github_import.clone_repo")
    def test_import_success(self, mock_clone, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        def fake_clone(url, dest, github_token=None, shallow=False):
            dest.mkdir(parents=True, exist_ok=True)
            return True
        mock_clone.side_effect = fake_clone

        manifest = {"project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test"}}
        result = import_repo("https://github.com/u/r", "test-import", manifest)
        assert result["success"] is True
        assert (tmp_path / "test-import" / "project.json").exists()
        assert (tmp_path / "test-import" / "project.meta.json").exists()

    @patch("services.editor.github_import.clone_repo", return_value=True)
    def test_import_already_exists(self, mock_clone, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        (tmp_path / "existing").mkdir()
        result = import_repo("https://github.com/u/r", "existing", {})
        assert result["success"] is False
        assert "already exists" in result["error"]

    @patch("services.editor.github_import.clone_repo", return_value=False)
    def test_import_clone_fails(self, mock_clone, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        result = import_repo("https://github.com/u/r", "new-proj", {})
        assert result["success"] is False


class TestSyncRepo:
    def test_sync_no_meta(self, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        (tmp_path / "proj").mkdir()
        result = sync_repo("proj")
        assert result["success"] is False

    def test_sync_invalid_meta(self, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "project.meta.json").write_text("not json")
        result = sync_repo("proj")
        assert result["success"] is False

    def test_sync_non_github(self, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "project.meta.json").write_text(json.dumps({"source": {"type": "local"}}))
        result = sync_repo("proj")
        assert result["success"] is False

    @patch("services.editor.github_import.clone_repo")
    def test_sync_legacy_reclone(self, mock_clone, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        proj = tmp_path / "proj"
        proj.mkdir()
        meta = {"source": {"type": "github", "repo_url": "https://github.com/u/r"}}
        (proj / "project.meta.json").write_text(json.dumps(meta))

        def fake_clone(url, dest, github_token=None, shallow=False):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "main.scad").write_text("cube(10);")
            return True
        mock_clone.side_effect = fake_clone

        result = sync_repo("proj")
        assert result["success"] is True
        assert len(result["updated_files"]) >= 1
