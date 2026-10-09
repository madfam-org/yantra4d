"""Tests for centralized project resolution utility."""
import os
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

    def test_writes_never_target_a_curated_root(self, tmp_path, monkeypatch):
        from utils.project_resolver import project_write_root
        public, private = self._roots(tmp_path, monkeypatch)

        assert project_write_root() not in (public, private)

    def test_roots_are_deduplicated_when_configured_identically(self, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import project_roots
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", tmp_path)

        assert project_roots() == [tmp_path]


class TestUserProjectsRoot:
    """The third root: user-authored cartridges (forks, imports, onboarding).

    Curated roots (commons, private) are read-only content; every new
    cartridge is written into USER_PROJECTS_DIR, which resolves LAST, and a new
    slug must be free in every root.
    """

    @staticmethod
    def _roots(tmp_path, monkeypatch):
        from config import Config
        public = tmp_path / "projects"
        private = tmp_path / "private-projects"
        user = tmp_path / "user-projects"
        for root in (public, private, user):
            root.mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", public)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", private)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", user)
        monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [public, private, user])
        return public, private, user

    def test_resolution_order_is_commons_private_user(self, tmp_path, monkeypatch):
        from utils.project_resolver import curated_project_roots, project_roots
        public, private, user = self._roots(tmp_path, monkeypatch)

        assert project_roots() == [public, private, user]
        assert curated_project_roots() == [public, private]

    def test_write_root_is_the_user_root(self, tmp_path, monkeypatch):
        from utils.project_resolver import project_write_root
        _public, _private, user = self._roots(tmp_path, monkeypatch)

        assert project_write_root() == user

    def test_write_root_is_a_path_when_configured_as_a_string(self, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import project_write_root
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", str(tmp_path / "u"))

        assert project_write_root() == tmp_path / "u"

    def test_user_slug_resolves_from_the_user_root(self, tmp_path, monkeypatch):
        _public, _private, user = self._roots(tmp_path, monkeypatch)
        (user / "my-fork").mkdir()

        project_dir, err = resolve_project_dir("my-fork")
        assert err is None
        assert project_dir == (user / "my-fork").resolve()

    def test_commons_wins_a_collision_with_the_user_root(self, tmp_path, monkeypatch):
        public, _private, user = self._roots(tmp_path, monkeypatch)
        (public / "dup").mkdir()
        (user / "dup").mkdir()

        project_dir, _err = resolve_project_dir("dup")
        assert project_dir == (public / "dup").resolve()

    def test_private_wins_a_collision_with_the_user_root(self, tmp_path, monkeypatch):
        _public, private, user = self._roots(tmp_path, monkeypatch)
        (private / "dup").mkdir()
        (user / "dup").mkdir()

        project_dir, _err = resolve_project_dir("dup")
        assert project_dir == (private / "dup").resolve()

    def test_traversal_out_of_the_user_root_is_rejected(self, tmp_path, monkeypatch):
        self._roots(tmp_path, monkeypatch)
        (tmp_path / "secret").mkdir()

        project_dir, err = resolve_project_dir("../secret")
        assert project_dir is None
        assert err == "Project not found"

    def test_a_missing_user_root_is_not_an_error(self, tmp_path, monkeypatch):
        from config import Config
        public, _private, _user = self._roots(tmp_path, monkeypatch)
        (public / "gridfinity").mkdir()
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", tmp_path / "absent")

        project_dir, err = resolve_project_dir("gridfinity")
        assert err is None
        assert project_dir == (public / "gridfinity").resolve()

    def test_single_root_deployment_writes_into_that_root(self, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import project_roots, project_write_root
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", tmp_path)

        assert project_roots() == [tmp_path]
        assert project_write_root() == tmp_path


class TestSlugInUse:
    """A new slug must be free in EVERY root, so no write shadows anything."""

    @staticmethod
    def _roots(tmp_path, monkeypatch, extra=None):
        from config import Config
        public = tmp_path / "projects"
        private = tmp_path / "private-projects"
        user = tmp_path / "user-projects"
        for root in (public, private, user):
            root.mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", public)
        monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", private)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", user)
        dirs = [public, private] + ([extra] if extra else []) + [user]
        monkeypatch.setattr(Config, "CARTRIDGES_DIRS", dirs)
        return public, private, user

    def test_free_slug_is_not_in_use(self, tmp_path, monkeypatch):
        from utils.project_resolver import slug_in_use
        self._roots(tmp_path, monkeypatch)

        assert slug_in_use("brand-new") is None

    def test_taken_in_each_root(self, tmp_path, monkeypatch):
        from utils.project_resolver import slug_in_use
        public, private, user = self._roots(tmp_path, monkeypatch)
        (public / "in-commons").mkdir()
        (private / "in-private").mkdir()
        (user / "in-user").mkdir()

        assert slug_in_use("in-commons") == (public / "in-commons").resolve()
        assert slug_in_use("in-private") == (private / "in-private").resolve()
        assert slug_in_use("in-user") == (user / "in-user").resolve()

    def test_taken_in_an_extra_manifest_root(self, tmp_path, monkeypatch):
        """CARTRIDGES_DIRS extras resolve BEFORE the user root in the manifest
        service, so a user slug there would be hidden: it counts as taken."""
        from utils.project_resolver import find_project_dir, slug_in_use
        extra = tmp_path / "node-cartridges"
        extra.mkdir()
        (extra / "npm-cart").mkdir()
        self._roots(tmp_path, monkeypatch, extra=extra)

        assert find_project_dir("npm-cart") is None
        assert slug_in_use("npm-cart") == (extra / "npm-cart").resolve()

    def test_traversal_is_never_in_use(self, tmp_path, monkeypatch):
        from utils.project_resolver import slug_in_use
        self._roots(tmp_path, monkeypatch)
        (tmp_path / "secret").mkdir()

        assert slug_in_use("../secret") is None


class TestShadowedUserSlugs:
    @staticmethod
    def _roots(tmp_path, monkeypatch):
        return TestUserProjectsRoot._roots(tmp_path, monkeypatch)

    def test_none_when_no_collision(self, tmp_path, monkeypatch):
        from utils.project_resolver import shadowed_user_slugs
        public, _private, user = self._roots(tmp_path, monkeypatch)
        (public / "gridfinity").mkdir()
        (user / "my-fork").mkdir()

        assert shadowed_user_slugs() == []

    def test_lists_user_slugs_hidden_by_a_curated_root(self, tmp_path, monkeypatch):
        from utils.project_resolver import shadowed_user_slugs
        public, private, user = self._roots(tmp_path, monkeypatch)
        (public / "later-in-commons").mkdir()
        (private / "later-in-private").mkdir()
        for slug in ("later-in-commons", "later-in-private", "unique"):
            (user / slug).mkdir()
        (user / "stray-file").write_text("not a cartridge")

        assert shadowed_user_slugs() == ["later-in-commons", "later-in-private"]

    def test_missing_user_root_has_nothing_shadowed(self, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import shadowed_user_slugs
        self._roots(tmp_path, monkeypatch)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", tmp_path / "absent")

        assert shadowed_user_slugs() == []

    def test_single_root_deployment_has_nothing_shadowed(self, tmp_path, monkeypatch):
        from config import Config
        from utils.project_resolver import shadowed_user_slugs
        (tmp_path / "gridfinity").mkdir()
        monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "USER_PROJECTS_DIR", tmp_path)
        monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])

        assert shadowed_user_slugs() == []


class TestUserProjectsConfig:
    def test_env_sets_the_user_root_and_it_resolves_last(self, tmp_path, monkeypatch):
        from config import AppConfig
        monkeypatch.setenv("PROJECTS_DIR", str(tmp_path / "projects"))
        monkeypatch.setenv("USER_PROJECTS_DIR", str(tmp_path / "user-projects"))
        extra = tmp_path / "extra"
        extra.mkdir()
        monkeypatch.setenv("CARTRIDGES_DIRS", str(extra))

        cfg = AppConfig()
        assert cfg.USER_PROJECTS_DIR == tmp_path / "user-projects"
        assert cfg.CARTRIDGES_DIRS[0] == tmp_path / "projects"
        assert cfg.CARTRIDGES_DIRS[-1] == tmp_path / "user-projects"
        assert extra in cfg.CARTRIDGES_DIRS[:-1]

    def test_default_is_a_repo_local_user_projects_dir(self, monkeypatch):
        from config import AppConfig
        monkeypatch.delenv("USER_PROJECTS_DIR", raising=False)

        cfg = AppConfig()
        assert cfg.USER_PROJECTS_DIR == cfg.BASE_DIR.parent.parent / "user-projects"

    def test_user_root_is_not_on_the_openscad_include_path(self, tmp_path, monkeypatch):
        from config import AppConfig
        monkeypatch.delenv("OPENSCADPATH", raising=False)
        monkeypatch.setenv("USER_PROJECTS_DIR", str(tmp_path / "user-projects"))

        cfg = AppConfig()
        assert str(tmp_path / "user-projects") not in cfg.OPENSCADPATH.split(os.pathsep)
