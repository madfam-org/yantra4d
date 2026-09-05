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


class TestPrivateCartridgeRoot:
    """The second cartridge root (RFC 0038 P2).

    The public commons is one submodule at PROJECTS_DIR; the client-private
    cartridges mount at PRIVATE_PROJECTS_DIR. Resolution spans both; writes
    never leave the public root.
    """

    @staticmethod
    def _roots(tmp_path, monkeypatch):
        from config import Config
        public = tmp_path / "projects"
        private = tmp_path / "private-projects"
        public.mkdir()
        private.mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", public)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", private)
        return public, private

    def test_private_slug_resolves_from_the_second_root(self, tmp_path, monkeypatch):
        _public, private = self._roots(tmp_path, monkeypatch)
        (private / "tablaco").mkdir()

        project_dir, err = resolve_project_dir("tablaco")
        assert err is None
        assert project_dir == (private / "tablaco").resolve()

    def test_public_slug_still_resolves_from_the_first_root(self, tmp_path, monkeypatch):
        public, _private = self._roots(tmp_path, monkeypatch)
        (public / "gridfinity").mkdir()

        project_dir, err = resolve_project_dir("gridfinity")
        assert err is None
        assert project_dir == (public / "gridfinity").resolve()

    def test_unknown_slug_is_not_found_in_either_root(self, tmp_path, monkeypatch):
        self._roots(tmp_path, monkeypatch)

        project_dir, err = resolve_project_dir("no-such-cartridge")
        assert project_dir is None
        assert err == "Project not found"

    def test_public_root_wins_a_slug_collision(self, tmp_path, monkeypatch):
        public, private = self._roots(tmp_path, monkeypatch)
        (public / "dup").mkdir()
        (private / "dup").mkdir()

        project_dir, err = resolve_project_dir("dup")
        assert err is None
        assert project_dir == (public / "dup").resolve()

    def test_traversal_out_of_the_private_root_is_rejected(self, tmp_path, monkeypatch):
        _public, private = self._roots(tmp_path, monkeypatch)
        secret = tmp_path / "secret"
        secret.mkdir()

        # Reaches tmp_path/secret from either root; must be refused by both.
        project_dir, err = resolve_project_dir("../secret")
        assert project_dir is None
        assert err == "Project not found"
        assert (private / ".." / "secret").resolve() == secret.resolve()

    def test_a_missing_private_root_is_not_an_error(self, tmp_path, monkeypatch):
        from config import Config
        public = tmp_path / "projects"
        public.mkdir()
        (public / "gridfinity").mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", public)
        # A public clone has no private mount at all.
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path / "absent")

        project_dir, err = resolve_project_dir("gridfinity")
        assert err is None
        assert project_dir == (public / "gridfinity").resolve()

    def test_writes_target_the_public_root_even_when_private_exists(self, tmp_path, monkeypatch):
        from utils.project_resolver import project_write_root
        public, _private = self._roots(tmp_path, monkeypatch)

        assert project_write_root() == public

    def test_roots_are_deduplicated_when_configured_identically(self, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import project_roots
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path)

        assert project_roots() == [tmp_path]
