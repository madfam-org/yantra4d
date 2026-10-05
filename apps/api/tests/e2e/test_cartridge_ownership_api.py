"""Forks and imports are writable by the account that created them, or an admin.

The creating account's ``sub`` is recorded at creation, outside the cartridge
(``services/core/cartridge_ownership.py``). Every route that writes into an
existing cartridge refuses anyone else with 403 ``not_cartridge_owner``. Commons
cartridges stay ``read_only_cartridge`` for everyone (test_read_only_cartridges_api.py).

Auth is genuinely on here (``decode_token`` patched, the same pattern as
test_private_projects_api.py), so each request travels the real middleware.
"""
import json
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.editor.editor import NOT_OWNER_ERROR_CODE, READ_ONLY_ERROR_CODE
from services.core.cartridge_ownership import (
    OWNERS_DIRNAME,
    forget_owner,
    owner_sub,
    owners_dir,
    record_owner,
)
from services.core.project_access import (
    PRIVATE_PROJECTS_ENV,
    PROJECT_ACCESS_GRANTS_ENV,
    private_project_slugs,
    project_access_grants,
)
from services.core.tier_service import TIER_OVERRIDES_ENV, load_tier_overrides
from utils.project_resolver import project_write_root

OWNER_SUB = "0f5e1c9a-owner-sub"
OTHER_SUB = "7d2b44e1-other-sub"

# Premium is the top tier: it reaches the TOP_TIER-gated sync route, and it
# shows that the top tier is not an admin — it does not open someone's cartridge.
TOKENS = {
    "tok-owner": {"sub": OWNER_SUB, "email": "owner@example.com", "yantra4d_tier": "premium"},
    "tok-other": {"sub": OTHER_SUB, "email": "other@example.com", "yantra4d_tier": "premium"},
    "tok-admin": {"sub": "a11d-admin-sub", "email": "admin@example.com", "yantra4d_tier": "premium",
                  "roles": ["admin"]},
    "tok-essentials": {"sub": "e55e-sub", "email": "e@example.com"},
}

FORK = "owned-fork"
IMPORTED = "owned-import"
LEGACY = "legacy-fork"           # a fork with no recorded creator
COMMONS = "commons-widget"

METAS = {
    FORK: {"source": {"type": "fork", "forked_from": COMMONS}},
    IMPORTED: {"source": {"type": "github", "repo_url": "https://github.com/example/widget"}},
    LEGACY: {"source": {"type": "fork", "forked_from": COMMONS}},
}


def _auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def _manifest(slug):
    return {
        "project": {"thumbnail": "t.png", "tags": ["t"], "difficulty": "beginner",
                    "name": slug, "slug": slug, "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"},
                   "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
        "assembly_steps": [{"step": 1, "label": "manual", "_auto_generated": False}],
    }


def _make(root: Path, slug: str, *, git=True) -> Path:
    project_dir = root / slug
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(json.dumps(_manifest(slug)))
    (project_dir / "main.scad").write_text("cube(10);")
    if slug in METAS:
        (project_dir / "project.meta.json").write_text(json.dumps(METAS[slug]))
    if git:
        from services.editor.git_operations import git_init
        git_init(project_dir)
        (project_dir / "pending.scad").write_text("sphere(2);")
    return project_dir


def _snapshot(project_dir: Path) -> dict[str, bytes]:
    return {str(p.relative_to(project_dir)): p.read_bytes()
            for p in sorted(project_dir.rglob("*")) if p.is_file()}


def _fake_decode(token):
    if token in TOKENS:
        return TOKENS[token]
    raise ValueError("invalid token")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (PRIVATE_PROJECTS_ENV, PROJECT_ACCESS_GRANTS_ENV, TIER_OVERRIDES_ENV):
        monkeypatch.delenv(name, raising=False)
    private_project_slugs()
    project_access_grants()
    load_tier_overrides()
    yield


@pytest.fixture(autouse=True)
def _stub_side_effects():
    """Stub what would leave the process: assembly analysis, GitHub, git pull/push."""
    with patch("routes.projects.assembly.analyze_directory", return_value={"nodes": []}), \
         patch("routes.projects.assembly.generate_assembly_steps",
               return_value=[{"step": 1, "label": "auto", "_auto_generated": True}]), \
         patch("routes.editor.git_ops.get_github_token", return_value="gh-token"), \
         patch("routes.editor.git_ops.git_pull", return_value={"success": True}), \
         patch("routes.editor.git_ops.git_push", return_value={"success": True}), \
         patch("routes.editor.github._get_token", return_value="gh-token"), \
         patch("routes.editor.github.sync_repo", return_value={"success": True, "updated_files": []}):
        yield


def _app(monkeypatch, *, auth_enabled=True, debug=False):
    from config import Config
    monkeypatch.setattr(Config, "AUTH_ENABLED", auth_enabled)
    monkeypatch.setattr(Config, "GITHUB_IMPORT_ENABLED", True)
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.debug = debug
    return flask_app


@pytest.fixture
def cartridges():
    root = project_write_root()
    root.mkdir(parents=True, exist_ok=True)
    dirs = {slug: _make(root, slug) for slug in (FORK, IMPORTED, LEGACY)}
    dirs[COMMONS] = _make(root, COMMONS, git=False)
    record_owner(FORK, TOKENS["tok-owner"])
    record_owner(IMPORTED, TOKENS["tok-owner"])
    return dirs


@pytest.fixture
def client(monkeypatch, cartridges):
    flask_app = _app(monkeypatch)
    with patch("middleware.auth.decode_token", side_effect=_fake_decode):
        yield flask_app.test_client()


# (id, method, path, request kwargs, imports only)
WRITE_ROUTES = [
    ("scad-autosave", "put", "/api/projects/{slug}/files/main.scad", {"json": {"content": "cube(20);"}}, False),
    ("create-file", "post", "/api/projects/{slug}/files", {"json": {"path": "extra.scad", "content": "x=1;"}}, False),
    ("delete-file", "delete", "/api/projects/{slug}/files/main.scad", {}, False),
    ("assembly-steps", "put", "/api/projects/{slug}/manifest/assembly-steps",
     {"json": {"assembly_steps": [{"step": 1, "label": "edited"}]}}, False),
    ("assembly-steps-write", "post", "/api/projects/{slug}/assembly-steps/write", {"json": {"merge": False}}, False),
    ("git-connect-remote", "post", "/api/projects/{slug}/git/connect-remote",
     {"json": {"remote_url": "https://github.com/example/widget.git"}}, False),
    ("git-commit", "post", "/api/projects/{slug}/git/commit",
     {"json": {"message": "edit", "files": ["pending.scad"]}}, False),
    ("git-pull", "post", "/api/projects/{slug}/git/pull", {}, True),
    # Writes nothing locally, but acts on the cartridge's remote: owner-only too.
    ("git-push", "post", "/api/projects/{slug}/git/push", {}, True),
    ("github-sync", "post", "/api/github/sync", {"json": {"slug": "{slug}"}}, True),
]
ROUTE_IDS = [r[0] for r in WRITE_ROUTES]


def _call(client, route, slug, token):
    _id, method, template, kwargs, _imports_only = route
    kwargs = json.loads(json.dumps(kwargs).replace("{slug}", slug))
    return getattr(client, method)(template.format(slug=slug), headers=_auth(token), **kwargs)


def _targets(route):
    return [IMPORTED] if route[4] else [FORK, IMPORTED]


class TestOwnerWrites:
    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=ROUTE_IDS)
    def test_owner_is_allowed(self, client, route):
        for slug in _targets(route):
            res = _call(client, route, slug, "tok-owner")
            assert res.status_code in (200, 201), (route[0], slug, res.get_json())

    def test_owner_autosave_persists(self, client, cartridges):
        res = client.put(f"/api/projects/{FORK}/files/main.scad", json={"content": "cube(20);"},
                         headers=_auth("tok-owner"))
        assert res.status_code == 200
        assert (cartridges[FORK] / "main.scad").read_text() == "cube(20);"


class TestOthersAreRefused:
    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=ROUTE_IDS)
    def test_non_owner_gets_403_and_nothing_is_written(self, client, cartridges, route):
        for slug in _targets(route):
            before = _snapshot(cartridges[slug])
            res = _call(client, route, slug, "tok-other")
            assert res.status_code == 403, (route[0], slug, res.get_json())
            body = res.get_json()
            assert body["error_code"] == NOT_OWNER_ERROR_CODE == "not_cartridge_owner"
            assert "Fork" in body["error"]
            assert OWNER_SUB not in res.get_data(as_text=True)
            assert _snapshot(cartridges[slug]) == before

    def test_below_pro_is_refused_by_tier_first(self, client):
        res = client.put(f"/api/projects/{FORK}/files/main.scad", json={"content": "x"},
                         headers=_auth("tok-essentials"))
        assert res.status_code == 403
        assert res.get_json()["error_code"] != NOT_OWNER_ERROR_CODE

    def test_commons_is_read_only_even_for_admin(self, client):
        res = client.put(f"/api/projects/{COMMONS}/files/main.scad", json={"content": "x"},
                         headers=_auth("tok-admin"))
        assert res.status_code == 403
        assert res.get_json()["error_code"] == READ_ONLY_ERROR_CODE


class TestAdminOverride:
    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=ROUTE_IDS)
    def test_admin_may_write_any_fork_or_import(self, client, route):
        for slug in _targets(route):
            res = _call(client, route, slug, "tok-admin")
            assert res.status_code in (200, 201), (route[0], slug, res.get_json())


class TestLegacyOwnerless:
    @pytest.mark.parametrize("route", [r for r in WRITE_ROUTES if not r[4]], ids=[r[0] for r in WRITE_ROUTES if not r[4]])
    def test_fails_closed_for_everyone_but_admins(self, client, cartridges, route):
        before = _snapshot(cartridges[LEGACY])
        for token in ("tok-owner", "tok-other"):
            res = _call(client, route, LEGACY, token)
            assert res.status_code == 403, (route[0], token, res.get_json())
            assert res.get_json()["error_code"] == NOT_OWNER_ERROR_CODE
        assert _snapshot(cartridges[LEGACY]) == before
        res = _call(client, route, LEGACY, "tok-admin")
        assert res.status_code in (200, 201), (route[0], res.get_json())

    def test_malformed_record_reads_as_ownerless(self, client, cartridges):
        (owners_dir() / f"{FORK}.json").write_text("{not json")
        res = client.put(f"/api/projects/{FORK}/files/main.scad", json={"content": "x"},
                         headers=_auth("tok-owner"))
        assert res.status_code == 403
        assert res.get_json()["error_code"] == NOT_OWNER_ERROR_CODE


class TestCreationRecordsTheCreator:
    def test_fork_records_the_forking_account_only(self, client):
        res = client.post(f"/api/projects/{COMMONS}/fork", json={"new_slug": "my-new-fork"},
                          headers=_auth("tok-owner"))
        assert res.status_code == 200, res.get_json()
        record = json.loads((owners_dir() / "my-new-fork.json").read_text())
        assert set(record) == {"sub", "recorded_at"}
        assert record["sub"] == OWNER_SUB

        ok = client.put("/api/projects/my-new-fork/files/main.scad", json={"content": "cube(3);"},
                        headers=_auth("tok-owner"))
        assert ok.status_code == 200
        refused = client.put("/api/projects/my-new-fork/files/main.scad", json={"content": "cube(4);"},
                             headers=_auth("tok-other"))
        assert refused.status_code == 403
        assert refused.get_json()["error_code"] == NOT_OWNER_ERROR_CODE

    def test_forking_someone_elses_fork_gives_you_your_own(self, client):
        res = client.post(f"/api/projects/{FORK}/fork", json={"new_slug": "their-copy"},
                          headers=_auth("tok-other"))
        assert res.status_code == 200
        assert client.put("/api/projects/their-copy/files/main.scad", json={"content": "x=2;"},
                          headers=_auth("tok-other")).status_code == 200
        assert client.put("/api/projects/their-copy/files/main.scad", json={"content": "x=3;"},
                          headers=_auth("tok-owner")).status_code == 403

    def test_a_fork_whose_record_cannot_be_written_is_rolled_back(self, client):
        with patch("routes.projects.projects.record_owner", side_effect=OSError("disk full")):
            res = client.post(f"/api/projects/{COMMONS}/fork", json={"new_slug": "doomed-fork"},
                              headers=_auth("tok-owner"))
        assert res.status_code == 500
        assert not (project_write_root() / "doomed-fork").exists()
        assert not (owners_dir() / "doomed-fork.json").exists()

    def test_github_import_records_the_importing_account(self, client):
        def fake_clone(repo_url, dest, github_token=None, shallow=False):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "main.scad").write_text("cube(5);")
            return True

        with patch("services.editor.github_import.clone_repo", side_effect=fake_clone):
            res = client.post("/api/github/import", json={
                "repo_url": "https://github.com/example/new-widget",
                "slug": "imported-widget",
                "manifest": _manifest("imported-widget"),
            }, headers=_auth("tok-owner"))
        assert res.status_code == 201, res.get_json()
        record = json.loads((owners_dir() / "imported-widget.json").read_text())
        assert record["sub"] == OWNER_SUB

        assert client.put("/api/projects/imported-widget/files/main.scad", json={"content": "cube(6);"},
                          headers=_auth("tok-owner")).status_code == 200
        refused = client.post("/api/github/sync", json={"slug": "imported-widget"}, headers=_auth("tok-other"))
        assert refused.status_code == 403
        assert refused.get_json()["error_code"] == NOT_OWNER_ERROR_CODE

    def test_an_import_whose_record_cannot_be_written_is_rolled_back(self, client):
        def fake_clone(repo_url, dest, github_token=None, shallow=False):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "main.scad").write_text("cube(5);")
            return True

        with patch("services.editor.github_import.clone_repo", side_effect=fake_clone), \
             patch("routes.editor.github.record_owner", side_effect=OSError("disk full")):
            res = client.post("/api/github/import", json={
                "repo_url": "https://github.com/example/new-widget",
                "slug": "doomed-import",
                "manifest": _manifest("doomed-import"),
            }, headers=_auth("tok-owner"))
        assert res.status_code == 500
        assert not (project_write_root() / "doomed-import").exists()


class TestCanWriteFlag:
    def _meta(self, client, slug, token):
        res = client.get(f"/api/projects/{slug}/meta", headers=_auth(token))
        assert res.status_code == 200
        assert res.headers["Cache-Control"] == "private, no-store"
        return res

    def test_owner_sees_can_write_and_is_owner(self, client):
        body = self._meta(client, FORK, "tok-owner").get_json()
        assert body["can_write"] is True
        assert body["is_owner"] is True
        assert body["source"]["type"] == "fork"

    def test_other_user_sees_read_only_and_never_the_owner(self, client):
        res = self._meta(client, FORK, "tok-other")
        assert res.get_json()["can_write"] is False
        assert res.get_json()["is_owner"] is False
        assert OWNER_SUB not in res.get_data(as_text=True)

    def test_admin_can_write_but_is_not_the_owner(self, client):
        body = self._meta(client, FORK, "tok-admin").get_json()
        assert body["can_write"] is True
        assert body["is_owner"] is False

    def test_anonymous_and_below_pro_cannot_write(self, client):
        assert self._meta(client, FORK, None).get_json()["can_write"] is False
        assert self._meta(client, FORK, "tok-essentials").get_json()["can_write"] is False

    def test_commons_and_legacy(self, client):
        assert self._meta(client, COMMONS, "tok-admin").get_json()["can_write"] is False
        assert self._meta(client, LEGACY, "tok-owner").get_json()["can_write"] is False
        assert self._meta(client, LEGACY, "tok-admin").get_json()["can_write"] is True


class TestIdentityNeverLeavesTheServer:
    def test_record_lives_outside_every_cartridge(self, cartridges):
        assert owners_dir().name == OWNERS_DIRNAME
        assert owners_dir().parent == project_write_root()
        for project_dir in cartridges.values():
            assert not owners_dir().resolve().is_relative_to(project_dir.resolve())

    def test_absent_from_git_history_after_edits_and_commits(self, client, cartridges):
        # A fresh fork gets its repository from auto_git on the first editor write.
        res = client.post(f"/api/projects/{COMMONS}/fork", json={"new_slug": "git-check"},
                          headers=_auth("tok-owner"))
        assert res.status_code == 200
        assert client.put("/api/projects/git-check/files/main.scad", json={"content": "cube(7);"},
                          headers=_auth("tok-owner")).status_code == 200
        assert client.post("/api/projects/git-check/git/commit",
                           json={"message": "edit", "files": ["main.scad"]},
                           headers=_auth("tok-owner")).status_code == 200

        fork_dir = project_write_root() / "git-check"
        history = subprocess.run(["git", "log", "-p", "--all"], cwd=fork_dir,
                                 capture_output=True, text=True, check=True).stdout
        tracked = subprocess.run(["git", "ls-files"], cwd=fork_dir,
                                 capture_output=True, text=True, check=True).stdout
        assert "cube(7);" in history  # the history is real
        assert OWNER_SUB not in history
        assert OWNERS_DIRNAME not in tracked
        for path in fork_dir.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                assert OWNER_SUB not in path.read_text(errors="ignore"), path

    def test_absent_from_downloads_and_project_responses(self, client):
        for url in (
            f"/api/projects/{FORK}/download/scad/main.scad",
            f"/api/projects/{FORK}/manifest",
            f"/api/projects/{FORK}/meta",
            f"/api/projects/{FORK}/files",
            f"/api/projects/{FORK}/files/main.scad",
            f"/api/projects/{FORK}/wasm-bundle",
            "/api/projects",
        ):
            res = client.get(url, headers=_auth("tok-owner"))
            assert OWNER_SUB not in res.get_data(as_text=True), (url, res.status_code)

    def test_record_is_not_reachable_by_path(self, client):
        for url in (
            f"/api/projects/{FORK}/download/scad/..%2F{OWNERS_DIRNAME}%2F{FORK}.json",
            f"/api/projects/{FORK}/files/..%2F{OWNERS_DIRNAME}%2F{FORK}.json",
            f"/api/projects/{OWNERS_DIRNAME}/files",
            f"/api/projects/{OWNERS_DIRNAME}/meta",
        ):
            res = client.get(url, headers=_auth("tok-admin"))
            assert res.status_code in (400, 404), (url, res.status_code)
            assert OWNER_SUB not in res.get_data(as_text=True)


class TestAuthDisabled:
    """Auth off follows the private-project rule: only local dev mode (debugger on) unlocks."""

    def test_auth_off_without_debug_refuses_forks(self, monkeypatch, cartridges):
        client = _app(monkeypatch, auth_enabled=False, debug=False).test_client()
        res = client.put(f"/api/projects/{FORK}/files/main.scad", json={"content": "x"})
        assert res.status_code == 403
        assert res.get_json()["error_code"] == NOT_OWNER_ERROR_CODE
        assert client.get(f"/api/projects/{FORK}/meta").get_json()["can_write"] is False

    def test_local_dev_mode_writes_forks_but_not_commons(self, monkeypatch, cartridges):
        client = _app(monkeypatch, auth_enabled=False, debug=True).test_client()
        assert client.put(f"/api/projects/{FORK}/files/main.scad", json={"content": "x"}).status_code == 200
        assert client.put(f"/api/projects/{LEGACY}/files/main.scad", json={"content": "x"}).status_code == 200
        res = client.put(f"/api/projects/{COMMONS}/files/main.scad", json={"content": "x"})
        assert res.status_code == 403
        assert res.get_json()["error_code"] == READ_ONLY_ERROR_CODE

    def test_a_fork_made_without_identity_is_ownerless(self, monkeypatch, cartridges):
        client = _app(monkeypatch, auth_enabled=False, debug=True).test_client()
        assert client.post(f"/api/projects/{COMMONS}/fork", json={"new_slug": "anon-fork"}).status_code == 200
        assert not (owners_dir() / "anon-fork.json").exists()


class TestOwnershipStore:
    def test_owner_only_counts_in_the_write_root(self, tmp_path):
        record_owner("elsewhere", {"sub": OWNER_SUB})
        other_root = tmp_path / "some-other-root" / "elsewhere"
        other_root.mkdir(parents=True)
        assert owner_sub("elsewhere", other_root) is None
        in_root = project_write_root() / "elsewhere"
        in_root.mkdir(parents=True, exist_ok=True)
        assert owner_sub("elsewhere", in_root) == OWNER_SUB

    def test_creation_without_identity_clears_a_stale_record(self):
        record_owner("reused-slug", {"sub": OTHER_SUB})
        assert record_owner("reused-slug", None) is False
        assert not (owners_dir() / "reused-slug.json").exists()

    def test_invalid_slugs_are_rejected(self):
        with pytest.raises(ValueError):
            record_owner("../escape", {"sub": OWNER_SUB})
        forget_owner("../escape")  # no-op, no error


class TestAdminFlags:
    """PATCH /api/admin/projects/<slug>/flags applies only to writable cartridges."""

    URL = "/api/admin/projects/{slug}/flags"

    def test_admin_on_commons_is_refused_and_nothing_is_written(self, client, cartridges):
        before = _snapshot(cartridges[COMMONS])
        res = client.patch(self.URL.format(slug=COMMONS), json={"unlisted": True}, headers=_auth("tok-admin"))
        assert res.status_code == 403
        assert res.get_json()["error_code"] == READ_ONLY_ERROR_CODE
        assert _snapshot(cartridges[COMMONS]) == before

    def test_admin_on_another_users_fork_is_allowed(self, client, cartridges):
        res = client.patch(self.URL.format(slug=FORK), json={"is_demo": True}, headers=_auth("tok-admin"))
        assert res.status_code == 200, res.get_json()
        written = json.loads((cartridges[FORK] / "project.json").read_text())
        assert written["project"]["is_demo"] is True

    def test_non_admin_keeps_the_existing_refusal(self, client, cartridges):
        for slug in (FORK, COMMONS):
            before = _snapshot(cartridges[slug])
            # Even the fork's own creator: the route is admin-only, as before.
            res = client.patch(self.URL.format(slug=slug), json={"is_demo": True}, headers=_auth("tok-owner"))
            assert res.status_code == 403
            assert res.get_json()["error"] == "Insufficient permissions"
            assert _snapshot(cartridges[slug]) == before


class TestAtomicCreation:
    """Two creations of the same new slug: exactly one wins; the loser touches nothing."""

    def _dev_client(self, monkeypatch):
        # Auth off + debugger: no token decoding or user upsert in the threads,
        # so the only shared state is the filesystem under test.
        return _app(monkeypatch, auth_enabled=False, debug=True)

    def test_concurrent_forks_leave_exactly_one_intact_fork(self, monkeypatch, cartridges):
        flask_app = self._dev_client(monkeypatch)
        import routes.projects.projects as projects_mod
        real_copytree = projects_mod.shutil.copytree
        first_is_copying = threading.Event()
        release_first = threading.Event()

        def slow_copytree(*args, **kwargs):
            # The winner pauses mid-copy so the loser arrives while the
            # winner's directory exists but is still being filled.
            first_is_copying.set()
            assert release_first.wait(10)
            return real_copytree(*args, **kwargs)

        results = {}

        def fork(name):
            res = flask_app.test_client().post(f"/api/projects/{COMMONS}/fork", json={"new_slug": "raced-fork"})
            results[name] = (res.status_code, res.get_json())

        # Both requests pass the cheap existence check, as in a real race.
        with patch.object(projects_mod, "slug_in_use", return_value=None), \
             patch.object(projects_mod.shutil, "copytree", side_effect=slow_copytree):
            winner = threading.Thread(target=fork, args=("winner",))
            winner.start()
            assert first_is_copying.wait(10)
            loser = threading.Thread(target=fork, args=("loser",))
            loser.start()
            loser.join(10)
            release_first.set()
            winner.join(10)

        assert results["winner"][0] == 200, results
        assert results["loser"][0] == 409, results
        assert results["loser"][1]["error_code"] == "slug_in_use"
        fork_dir = project_write_root() / "raced-fork"
        assert (fork_dir / "main.scad").read_text() == "cube(10);"
        assert json.loads((fork_dir / "project.meta.json").read_text())["source"]["type"] == "fork"

    def test_free_running_forks_of_one_slug(self, monkeypatch, cartridges):
        flask_app = self._dev_client(monkeypatch)
        import routes.projects.projects as projects_mod
        for round_no in range(5):
            slug = f"free-race-{round_no}"
            start = threading.Barrier(4)
            codes = []

            def fork(slug=slug, start=start, codes=codes):
                client = flask_app.test_client()
                start.wait(10)
                codes.append(client.post(f"/api/projects/{COMMONS}/fork", json={"new_slug": slug}).status_code)

            with patch.object(projects_mod, "slug_in_use", return_value=None):
                threads = [threading.Thread(target=fork) for _ in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(20)
            assert sorted(codes) == [200, 409, 409, 409], (slug, codes)
            assert (project_write_root() / slug / "main.scad").read_text() == "cube(10);"

    def test_a_losing_import_never_touches_the_winner(self, monkeypatch, cartridges):
        flask_app = self._dev_client(monkeypatch)
        import services.editor.github_import as gi

        def fake_clone(repo_url, dest, github_token=None, shallow=False):
            (dest / "main.scad").write_text("cube(5);")
            return True

        winner_dir = project_write_root() / "raced-import"
        winner_dir.mkdir()
        (winner_dir / "keep.scad").write_text("cube(1);")
        with patch.object(gi, "slug_in_use", return_value=None), \
             patch.object(gi, "clone_repo", side_effect=fake_clone):
            res = flask_app.test_client().post("/api/github/import", json={
                "repo_url": "https://github.com/example/w", "slug": "raced-import",
                "manifest": _manifest("raced-import"),
            })
        assert res.status_code == 409
        assert res.get_json()["error_code"] == "slug_in_use"
        assert sorted(p.name for p in winner_dir.iterdir()) == ["keep.scad"]

    def test_a_failed_clone_removes_only_its_own_reservation(self, monkeypatch, cartridges):
        flask_app = self._dev_client(monkeypatch)
        with patch("services.editor.github_import.clone_repo", return_value=False):
            res = flask_app.test_client().post("/api/github/import", json={
                "repo_url": "https://github.com/example/w", "slug": "failed-import",
                "manifest": _manifest("failed-import"),
            })
        assert res.status_code == 400
        assert not (project_write_root() / "failed-import").exists()


BINDINGS_GRAPH = {
    "version": "1.0.0", "units": "mm",
    "nodes": [
        {"id": "outline", "type": "profile_circle", "params": {"r": 45}},
        {"id": "plate", "type": "extrude", "inputs": {"profile": "outline"}, "params": {"height": 8}},
    ],
    "outputs": {"flange": "plate"},
}


class TestGraphBindings:
    """PUT /manifest/bindings follows the same rule (and stays fork-only by its own check)."""


    @pytest.fixture
    def graph_fork(self, cartridges):
        fork_dir = cartridges[FORK]
        manifest = json.loads((fork_dir / "project.json").read_text())
        manifest["modes"][0]["scad_file"] = "part.graph.json"
        manifest["parameters"] = [{"id": "plate_height", "type": "slider", "default": 8, "min": 2,
                                   "max": 30, "step": 1, "label": {"en": "Height"}}]
        (fork_dir / "project.json").write_text(json.dumps(manifest))
        (fork_dir / "part.graph.json").write_text(json.dumps(BINDINGS_GRAPH))
        return fork_dir

    def _put(self, client, token):
        return client.put(f"/api/projects/{FORK}/manifest/bindings",
                          json={"bindings": {"plate_height": "plate.height"}}, headers=_auth(token))

    def test_non_owner_gets_not_cartridge_owner_and_nothing_is_written(self, client, graph_fork):
        before = _snapshot(graph_fork)
        res = self._put(client, "tok-other")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == NOT_OWNER_ERROR_CODE
        assert _snapshot(graph_fork) == before

    def test_owner_and_admin_may_bind(self, client, graph_fork):
        assert self._put(client, "tok-owner").status_code == 200
        assert self._put(client, "tok-admin").status_code == 200


class TestImportedManifestSlug:
    def test_import_manifest_names_the_import_slug(self, monkeypatch, cartridges):
        """A submitted manifest naming another slug is stored under the slug it was imported as."""
        flask_app = _app(monkeypatch, auth_enabled=False, debug=True)
        client = flask_app.test_client()

        def fake_clone(repo_url, dest, github_token=None, shallow=False):
            (dest / "main.scad").write_text("cube(5);")
            return True

        submitted = _manifest("upstream-name")
        with patch("services.editor.github_import.clone_repo", side_effect=fake_clone):
            res = client.post("/api/github/import", json={
                "repo_url": "https://github.com/example/upstream-name",
                "slug": "my-import-slug",
                "manifest": submitted,
            })
        assert res.status_code == 201, res.get_json()
        stored = json.loads((project_write_root() / "my-import-slug" / "project.json").read_text())
        assert stored["project"]["slug"] == "my-import-slug"
        assert stored["project"]["name"] == "upstream-name"
        assert client.get("/api/projects/my-import-slug/manifest").get_json()["project"]["slug"] == "my-import-slug"
        import manifest as manifest_mod
        manifest_mod.manifest_service._manifest_cache.clear()
        assert "my-import-slug" in {p["slug"] for p in client.get("/api/projects").get_json()}
