"""Tests for centralized project resolution utility."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.project_resolver import resolve_project_dir


class TestResolveProjectDir:
    def test_valid_project(self, tmp_path, monkeypatch):
        from config import Config
        slug = "my-project"
        (tmp_path / slug).mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        project_dir, err = resolve_project_dir(slug)
        assert err is None
        assert project_dir == (tmp_path / slug).resolve()

    def test_missing_project(self, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        _, err = resolve_project_dir("nonexistent")
        assert err == "Project not found"

    def test_path_traversal_rejected(self, tmp_path, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        # Create a directory outside PROJECTS_DIR
        outside = tmp_path.parent / "secret"
        outside.mkdir(exist_ok=True)

        _, err = resolve_project_dir("../secret")
        assert err == "Project not found"

    def test_require_git_fails_without_git(self, tmp_path, monkeypatch):
        from config import Config
        slug = "my-project"
        (tmp_path / slug).mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        _, err = resolve_project_dir(slug, require_git=True)
        assert "git repository" in err

    def test_require_git_succeeds_with_git(self, tmp_path, monkeypatch):
        from config import Config
        slug = "my-project"
        proj = tmp_path / slug
        proj.mkdir()
        (proj / ".git").mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        project_dir, err = resolve_project_dir(slug, require_git=True)
        assert err is None
        assert project_dir is not None

    def test_auto_git_initializes(self, tmp_path, monkeypatch):
        from config import Config
        slug = "my-project"
        proj = tmp_path / slug
        proj.mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

        # Mock git_init to just create .git dir
        called = []

        def mock_git_init(path):
            called.append(path)
            (path / ".git").mkdir()

        monkeypatch.setattr("services.editor.git_operations.git_init", mock_git_init)

        _project_dir, err = resolve_project_dir(slug, auto_git=True)
        assert err is None
        assert len(called) == 1
