"""Read-only commons cartridges, enforced on the server.

Only a cartridge the API created for someone is written through the API: a
fork (``project.meta.json`` ``source.type == "fork"``) or an imported
repository (``source.type == "github"``). A built-in commons cartridge has no
``project.meta.json``; it, and anything whose source type is missing or
unknown, answers every write with 403 ``read_only_cartridge`` and is left
byte-for-byte untouched. Reads are unaffected.

Every route that writes into an existing cartridge is covered here, including
``PUT /files/<path>``, which is the call the Studio's SCAD editor autosave
(``useEditorRender`` -> ``editorService.writeFile``) makes.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.editor.editor import READ_ONLY_ERROR_CODE, WRITABLE_SOURCE_TYPES, _project_source_type
from services.core.project_access import (
    LOCKED_ERROR_CODE,
    PRIVATE_PROJECTS_ENV,
    PROJECT_ACCESS_GRANTS_ENV,
    private_project_slugs,
    project_access_grants,
)
from services.core.tier_service import TIER_OVERRIDES_ENV, load_tier_overrides

COMMONS = "commons-widget"        # built-in: no project.meta.json
TYPELESS = "typeless-widget"      # project.meta.json without source.type
UNKNOWN_TYPE = "odd-widget"       # a source.type the API never writes
CORRUPT = "corrupt-widget"        # unreadable project.meta.json
FORK = "my-fork"
IMPORTED = "my-import"

METAS = {
    TYPELESS: {"source": {}},
    UNKNOWN_TYPE: {"source": {"type": "submodule"}},
    FORK: {"source": {"type": "fork", "forked_from": COMMONS}},
    IMPORTED: {"source": {"type": "github", "repo_url": "https://github.com/example/widget"}},
}

READ_ONLY_SLUGS = [COMMONS, TYPELESS, UNKNOWN_TYPE, CORRUPT]
WRITABLE_SLUGS = [FORK, IMPORTED]


def _manifest(slug, private=False):
    manifest = {
        "project": {
            "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
            "name": slug, "slug": slug, "version": "1.0.0",
        },
        "modes": [{
            "id": "default", "scad_file": "main.scad", "label": {"en": "Default"},
            "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"},
        }],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
        "assembly_steps": [{"step": 1, "label": "manual", "_auto_generated": False}],
    }
    if private:
        manifest["access_control"] = {"view": "private"}
    return manifest


def _make_cartridge(root: Path, slug: str, *, private=False, git=False) -> Path:
    project_dir = root / slug
    project_dir.mkdir()
    (project_dir / "project.json").write_text(json.dumps(_manifest(slug, private)))
    (project_dir / "main.scad").write_text("cube(10);")
    if slug in METAS:
        (project_dir / "project.meta.json").write_text(json.dumps(METAS[slug]))
    elif slug == CORRUPT:
        (project_dir / "project.meta.json").write_text("{not json")
    if git:
        from services.editor.git_operations import git_init
        git_init(project_dir)
        # Something for the commit route to commit.
        (project_dir / "pending.scad").write_text("sphere(2);")
    return project_dir


def _snapshot(project_dir: Path) -> dict[str, bytes]:
    """Every file under a cartridge, so a refusal can be shown to write nothing."""
    return {
        str(p.relative_to(project_dir)): p.read_bytes()
        for p in sorted(project_dir.rglob("*"))
        if p.is_file()
    }


@pytest.fixture
def app(tmp_path):
    for slug in [*READ_ONLY_SLUGS, *WRITABLE_SLUGS]:
        # .git up front so the git routes reach the guard rather than stopping
        # at "no git repository"; the editor routes' auto_git is checked by the
        # cartridges without one.
        _make_cartridge(tmp_path, slug, git=slug in WRITABLE_SLUGS)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    # Local development mode (auth off + debugger on): forks and imports are
    # writable by any caller, so these tests isolate the read-only rule.
    # Ownership is covered in test_cartridge_ownership_api.py.
    flask_app.debug = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# Each write route as (id, method, path template, request kwargs). ``{slug}`` is
# substituted per cartridge.
WRITE_ROUTES = [
    ("scad-autosave", "put", "/api/projects/{slug}/files/main.scad", {"json": {"content": "cube(20);"}}),
    ("create-file", "post", "/api/projects/{slug}/files", {"json": {"path": "extra.scad", "content": "sphere(1);"}}),
    ("delete-file", "delete", "/api/projects/{slug}/files/main.scad", {}),
    ("assembly-steps", "put", "/api/projects/{slug}/manifest/assembly-steps",
     {"json": {"assembly_steps": [{"step": 1, "label": "edited"}]}}),
    ("assembly-steps-write", "post", "/api/projects/{slug}/assembly-steps/write", {"json": {"merge": False}}),
    ("git-connect-remote", "post", "/api/projects/{slug}/git/connect-remote",
     {"json": {"remote_url": "https://github.com/example/widget.git"}}),
    ("git-commit", "post", "/api/projects/{slug}/git/commit", {"json": {"message": "edit", "files": ["pending.scad"]}}),
]
ROUTE_IDS = [r[0] for r in WRITE_ROUTES]


@pytest.fixture(autouse=True)
def _stub_assembly_generation():
    """Assembly generation parses geometry; its output is irrelevant here."""
    with patch("routes.projects.assembly.analyze_directory", return_value={"nodes": []}), \
         patch("routes.projects.assembly.generate_assembly_steps",
               return_value=[{"step": 1, "label": "auto", "_auto_generated": True}]):
        yield


def _call(client, route, slug):
    _id, method, template, kwargs = route
    return getattr(client, method)(template.format(slug=slug), **kwargs)


class TestReadOnlyCartridgesRefuseEveryWrite:
    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=ROUTE_IDS)
    @pytest.mark.parametrize("slug", READ_ONLY_SLUGS)
    def test_refused_with_stable_code_and_nothing_written(self, client, tmp_path, route, slug):
        project_dir = tmp_path / slug
        before = _snapshot(project_dir)

        res = _call(client, route, slug)

        assert res.status_code == 403, res.get_json()
        body = res.get_json()
        assert body["error_code"] == READ_ONLY_ERROR_CODE == "read_only_cartridge"
        assert "Fork" in body["error"]
        assert _snapshot(project_dir) == before
        # The editor routes auto-initialise git; a refusal must come first.
        assert not (project_dir / ".git").exists()

    def test_commons_git_routes_are_refused_even_with_a_repository(self, client, tmp_path):
        """A commons cartridge that already has a .git cannot be promoted to an import.

        connect-remote would otherwise write ``source.type = "github"`` into it,
        after which every other write would be allowed.
        """
        project_dir = tmp_path / COMMONS
        from services.editor.git_operations import git_init
        git_init(project_dir)

        for route in WRITE_ROUTES:
            if route[0].startswith("git-"):
                res = _call(client, route, COMMONS)
                assert res.status_code == 403, (route[0], res.get_json())
                assert res.get_json()["error_code"] == READ_ONLY_ERROR_CODE
        assert not (project_dir / "project.meta.json").exists()

    def test_reads_are_unaffected(self, client):
        assert client.get(f"/api/projects/{COMMONS}/files").status_code == 200
        res = client.get(f"/api/projects/{COMMONS}/files/main.scad")
        assert res.status_code == 200
        assert res.get_json()["content"] == "cube(10);"

    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=ROUTE_IDS)
    def test_unknown_project_still_404s(self, client, route):
        assert _call(client, route, "no-such-widget").status_code == 404


class TestForksAndImportsAreWritable:
    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=ROUTE_IDS)
    @pytest.mark.parametrize("slug", WRITABLE_SLUGS)
    def test_allowed(self, client, route, slug):
        res = _call(client, route, slug)
        assert res.status_code in (200, 201), (route[0], slug, res.get_json())

    @pytest.mark.parametrize("slug", WRITABLE_SLUGS)
    def test_scad_autosave_persists(self, client, tmp_path, slug):
        res = client.put(f"/api/projects/{slug}/files/main.scad", json={"content": "cube(20);"})
        assert res.status_code == 200
        assert (tmp_path / slug / "main.scad").read_text() == "cube(20);"

    def test_editor_write_still_auto_inits_git_on_a_fork(self, client, tmp_path):
        """auto_git is unchanged for a writable cartridge — the guard only runs first."""
        fork_dir = tmp_path / "fresh-fork"
        fork_dir.mkdir()
        (fork_dir / "project.json").write_text(json.dumps(_manifest("fresh-fork")))
        (fork_dir / "main.scad").write_text("cube(1);")
        (fork_dir / "project.meta.json").write_text(json.dumps({"source": {"type": "fork"}}))

        res = client.put("/api/projects/fresh-fork/files/main.scad", json={"content": "cube(2);"})
        assert res.status_code == 200
        assert (fork_dir / ".git").is_dir()

    def test_a_fork_can_still_be_connected_to_a_remote(self, client, tmp_path):
        res = client.post(f"/api/projects/{FORK}/git/connect-remote",
                          json={"remote_url": "https://github.com/example/widget.git"})
        assert res.status_code == 200
        meta = json.loads((tmp_path / FORK / "project.meta.json").read_text())
        assert meta["source"]["type"] == "github"

    def test_fork_route_produces_a_writable_cartridge(self, client, tmp_path):
        """End to end: forking a commons cartridge is how it becomes editable."""
        assert client.put(f"/api/projects/{COMMONS}/files/main.scad",
                          json={"content": "cube(3);"}).status_code == 403
        res = client.post(f"/api/projects/{COMMONS}/fork", json={"new_slug": "commons-widget-copy"})
        assert res.status_code == 200, res.get_json()
        res = client.put("/api/projects/commons-widget-copy/files/main.scad", json={"content": "cube(3);"})
        assert res.status_code == 200
        assert (tmp_path / COMMONS / "main.scad").read_text() == "cube(10);"


class TestProjectSourceType:
    def test_writable_types_are_exactly_fork_and_import(self):
        assert WRITABLE_SOURCE_TYPES == frozenset({"fork", "github"})

    @pytest.mark.parametrize("content, expected", [
        (None, None),
        ("{not json", None),
        ("[]", None),
        ('{"source": "fork"}', None),
        ('{"source": {"type": 7}}', None),
        ('{"source": {}}', None),
        ('{"source": {"type": "fork"}}', "fork"),
        ('{"source": {"type": "github"}}', "github"),
    ])
    def test_reads_meta_defensively(self, tmp_path, content, expected):
        if content is not None:
            (tmp_path / "project.meta.json").write_text(content)
        assert _project_source_type(tmp_path) == expected


# ──────────────────────────────────────────────
# Identity and privacy run before the read-only check, exactly as before
# ──────────────────────────────────────────────

PRIVATE_FORK = "private-fork"
PRIVATE_COMMONS = "private-commons"

TOKENS = {
    "tok-essentials": {"sub": "u1", "email": "someone@example.com"},
    "tok-pro": {"sub": "u2", "email": "other-maker@example.com", "yantra4d_tier": "pro"},
    "tok-pro-granted": {"sub": "u3", "email": "owner@example.com", "yantra4d_tier": "pro"},
}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    from config import Config

    for name in (PRIVATE_PROJECTS_ENV, PROJECT_ACCESS_GRANTS_ENV, TIER_OVERRIDES_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PROJECT_ACCESS_GRANTS_ENV, json.dumps({PRIVATE_FORK: ["owner@example.com"]}))
    private_project_slugs()
    project_access_grants()
    load_tier_overrides()

    private_fork = _make_cartridge(tmp_path, FORK)
    private_fork.rename(tmp_path / PRIVATE_FORK)
    (tmp_path / PRIVATE_FORK / "project.json").write_text(json.dumps(_manifest(PRIVATE_FORK, private=True)))
    _make_cartridge(tmp_path, COMMONS).rename(tmp_path / PRIVATE_COMMONS)
    (tmp_path / PRIVATE_COMMONS / "project.json").write_text(json.dumps(_manifest(PRIVATE_COMMONS, private=True)))

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    def fake_decode(token):
        if token in TOKENS:
            return TOKENS[token]
        raise ValueError("invalid token")

    with patch("middleware.auth.decode_token", side_effect=fake_decode):
        yield flask_app.test_client()


class TestAccessOrderIsUnchanged:
    def _autosave(self, client, slug, token=None):
        return client.put(f"/api/projects/{slug}/files/main.scad", json={"content": "cube(20);"},
                          headers=_auth(token) if token else {})

    def test_below_pro_is_refused_by_tier_first(self, auth_client):
        res = self._autosave(auth_client, PRIVATE_FORK, "tok-essentials")
        assert res.status_code == 403
        assert res.get_json()["error_code"] != READ_ONLY_ERROR_CODE

    def test_another_users_private_fork_stays_locked(self, auth_client, tmp_path):
        res = self._autosave(auth_client, PRIVATE_FORK, "tok-pro")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == LOCKED_ERROR_CODE
        assert (tmp_path / PRIVATE_FORK / "main.scad").read_text() == "cube(10);"
        assert not (tmp_path / PRIVATE_FORK / ".git").exists()

    def test_the_entitled_caller_writes_the_private_fork(self, auth_client, tmp_path):
        from services.core.cartridge_ownership import record_owner
        record_owner(PRIVATE_FORK, TOKENS["tok-pro-granted"])
        res = self._autosave(auth_client, PRIVATE_FORK, "tok-pro-granted")
        assert res.status_code == 200
        assert (tmp_path / PRIVATE_FORK / "main.scad").read_text() == "cube(20);"

    def test_private_commons_answers_locked_not_read_only(self, auth_client):
        """Privacy is settled first, so the refusal reveals nothing new about it."""
        res = self._autosave(auth_client, PRIVATE_COMMONS, "tok-pro")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == LOCKED_ERROR_CODE

    def test_private_commons_is_read_only_even_when_entitled(self, auth_client, monkeypatch):
        monkeypatch.setenv(PROJECT_ACCESS_GRANTS_ENV, json.dumps({PRIVATE_COMMONS: ["owner@example.com"]}))
        res = self._autosave(auth_client, PRIVATE_COMMONS, "tok-pro-granted")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == READ_ONLY_ERROR_CODE
