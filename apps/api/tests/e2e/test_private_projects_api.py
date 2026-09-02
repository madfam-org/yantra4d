"""E2E tests for private projects — the `project_locked` refusal end to end.

Auth is genuinely on for these (the shared conftest turns it off globally), and
`decode_token` is patched the way tests/unit/test_auth_middleware.py does it, so
every request travels the real middleware path with a real Bearer header.

Every address here is an example.com address. The production grant map is a
Kubernetes secret and never repository content.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.project_access import (
    PRIVATE_PROJECTS_ENV,
    PROJECT_ACCESS_GRANTS_ENV,
    private_project_slugs,
    project_access_grants,
)
from services.core.tier_service import TIER_OVERRIDES_ENV, load_tier_overrides

PUBLIC_SLUG = "open-widget"
PRIVATE_SLUG = "secret-widget"

# token string -> claims the patched decode_token returns for it
TOKENS = {
    "tok-essentials": {"sub": "u1", "email": "someone@example.com"},
    "tok-madfam": {"sub": "u2", "email": "boss@example.com", "yantra4d_tier": "madfam"},
    "tok-granted": {"sub": "u3", "email": "guest-of-honour@example.com"},
    "tok-admin": {"sub": "u4", "email": "admin@example.com", "roles": ["admin"]},
}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _manifest(slug, private=False):
    manifest = {
        "project": {
            "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
            "name": slug, "slug": slug, "version": "1.0.0",
        },
        "modes": [{
            "id": "single", "scad_file": "main.scad", "label": {"en": "Single"},
            "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"},
        }],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"},
                   "default_color": "#ffffff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    if private:
        manifest["access_control"] = {"view": "private"}
    return manifest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Reset the three call-time config loaders between tests."""
    for name in (PRIVATE_PROJECTS_ENV, PROJECT_ACCESS_GRANTS_ENV, TIER_OVERRIDES_ENV):
        monkeypatch.delenv(name, raising=False)
    private_project_slugs()
    project_access_grants()
    load_tier_overrides()
    yield


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Two cartridges — one public, one private — with auth switched on."""
    from config import Config

    for slug, private in ((PUBLIC_SLUG, False), (PRIVATE_SLUG, True)):
        project_dir = tmp_path / slug
        project_dir.mkdir()
        (project_dir / "project.json").write_text(json.dumps(_manifest(slug, private)))
        (project_dir / "main.scad").write_text("cube(10);")

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / f"{PUBLIC_SLUG}_preview_main.stl").write_bytes(b"solid a\nendsolid")
    (static_dir / f"{PRIVATE_SLUG}_preview_main.stl").write_bytes(b"solid b\nendsolid")

    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)
    monkeypatch.setattr(Config, "AUTH_ENABLED", True)

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    # In production Config.STATIC_DIR and Flask's static_folder are the same
    # directory; point the app at the temp one so /static behaves the same here.
    flask_app.static_folder = str(static_dir)

    def fake_decode(token):
        if token in TOKENS:
            return TOKENS[token]
        raise ValueError("invalid token")

    with patch("middleware.auth.decode_token", side_effect=fake_decode):
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestManifestRoute:
    def test_public_project_is_unaffected(self, client):
        res = client.get(f"/api/projects/{PUBLIC_SLUG}/manifest")
        assert res.status_code == 200
        assert res.headers["Cache-Control"] == "public, max-age=300"
        assert res.headers.get("ETag")

    def test_anonymous_gets_locked_with_auth_required(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest")
        assert res.status_code == 403
        body = res.get_json()
        assert body["error_code"] == "project_locked"
        assert body["auth_required"] is True
        assert body["status"] == "error"

    def test_signed_in_but_unentitled_gets_locked_without_auth_required(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest",
                         headers=auth("tok-essentials"))
        assert res.status_code == 403
        body = res.get_json()
        assert body["error_code"] == "project_locked"
        assert body["auth_required"] is False

    def test_top_tier_claim_is_allowed(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest",
                         headers=auth("tok-madfam"))
        assert res.status_code == 200
        assert res.get_json()["project"]["slug"] == PRIVATE_SLUG

    def test_admin_role_is_allowed(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest",
                         headers=auth("tok-admin"))
        assert res.status_code == 200

    def test_granted_email_is_allowed(self, client, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({PRIVATE_SLUG: ["guest-of-honour@example.com"]}),
        )
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest",
                         headers=auth("tok-granted"))
        assert res.status_code == 200

    def test_tier_override_identity_is_allowed(self, client, monkeypatch):
        """A staff identity configured in TIER_OVERRIDES reaches the top tier."""
        monkeypatch.setenv(
            TIER_OVERRIDES_ENV, json.dumps({"someone@example.com": "madfam"}),
        )
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest",
                         headers=auth("tok-essentials"))
        assert res.status_code == 200

    def test_private_manifest_is_never_publicly_cached(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/manifest",
                         headers=auth("tok-madfam"))
        assert res.headers["Cache-Control"] == "private, no-store"
        assert "ETag" not in res.headers

    def test_env_forced_private_beats_a_public_manifest(self, client, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, PUBLIC_SLUG)
        assert client.get(f"/api/projects/{PUBLIC_SLUG}/manifest").status_code == 403
        assert client.get(f"/api/projects/{PUBLIC_SLUG}/manifest",
                          headers=auth("tok-madfam")).status_code == 200

    def test_unknown_project_still_404s(self, client):
        res = client.get("/api/projects/no-such-thing/manifest")
        assert res.status_code == 404


class TestProjectListing:
    def test_anonymous_does_not_see_the_private_project(self, client):
        res = client.get("/api/projects")
        assert res.status_code == 200
        slugs = {p["slug"] for p in res.get_json()}
        assert PUBLIC_SLUG in slugs
        assert PRIVATE_SLUG not in slugs

    def test_unentitled_user_does_not_see_it_either(self, client):
        res = client.get("/api/projects", headers=auth("tok-essentials"))
        slugs = {p["slug"] for p in res.get_json()}
        assert PRIVATE_SLUG not in slugs

    def test_top_tier_sees_it(self, client):
        res = client.get("/api/projects", headers=auth("tok-madfam"))
        slugs = {p["slug"] for p in res.get_json()}
        assert PRIVATE_SLUG in slugs
        assert PUBLIC_SLUG in slugs

    def test_a_caller_dependent_list_is_not_shared_cached(self, client):
        res = client.get("/api/projects")
        assert res.headers["Cache-Control"] == "private, no-store"


class TestOtherProjectRoutes:
    def test_meta_is_gated(self, client):
        assert client.get(f"/api/projects/{PRIVATE_SLUG}/meta").status_code == 403
        assert client.get(f"/api/projects/{PUBLIC_SLUG}/meta").status_code == 200

    def test_parts_are_gated(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/parts/main.stl")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"

    def test_storefront_is_gated(self, client):
        assert client.get(f"/api/projects/{PRIVATE_SLUG}/storefront").status_code == 403
        assert client.get(f"/api/projects/{PUBLIC_SLUG}/storefront").status_code == 200

    def test_share_link_is_gated(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/share/some-preset")
        assert res.status_code == 403

    def test_download_is_gated(self, client):
        res = client.get(f"/api/projects/{PRIVATE_SLUG}/download/stl/{PRIVATE_SLUG}_preview_main.stl")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"


class TestRenderRoutes:
    def test_render_is_refused_for_anonymous(self, client):
        res = client.post("/api/render", json={"project": PRIVATE_SLUG, "mode": "single"})
        assert res.status_code == 403
        body = res.get_json()
        assert body["error_code"] == "project_locked"
        assert body["auth_required"] is True

    def test_render_is_refused_for_an_unentitled_user(self, client):
        res = client.post("/api/render", json={"project": PRIVATE_SLUG, "mode": "single"},
                          headers=auth("tok-essentials"))
        assert res.status_code == 403
        assert res.get_json()["auth_required"] is False

    def test_render_stream_is_refused_for_anonymous(self, client):
        res = client.post("/api/render-stream", json={"project": PRIVATE_SLUG, "mode": "single"})
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"

    def test_render_cancel_is_refused_for_anonymous(self, client):
        res = client.post("/api/render-cancel", json={"project": PRIVATE_SLUG})
        assert res.status_code == 403

    def test_render_cancel_without_a_slug_is_not_gated(self, client):
        """No slug, no project gate: the scoped-cancel contract decides the answer.

        A bodyless cancel is a 400 `cancel_target_required` (a target is
        mandatory since the scoped rewrite), never a 403 `project_locked`; a
        targeted cancel with no slug goes through untouched by the gate.
        """
        res = client.post("/api/render-cancel", json={})
        assert res.status_code == 400
        assert res.get_json()["error_code"] == "cancel_target_required"

        res = client.post("/api/render-cancel", json={"request_id": "req-without-slug"})
        assert res.status_code != 403

    def test_public_render_is_not_blocked_by_the_gate(self, client):
        """The public path must not acquire a 403 — whatever else it returns."""
        res = client.post("/api/render", json={"project": PUBLIC_SLUG, "mode": "single"})
        assert res.status_code != 403


class TestStaticArtifacts:
    def test_public_artifact_is_served(self, client):
        res = client.get(f"/static/{PUBLIC_SLUG}_preview_main.stl")
        assert res.status_code == 200
        assert "no-store" not in res.headers.get("Cache-Control", "")

    def test_private_artifact_is_refused_for_anonymous(self, client):
        res = client.get(f"/static/{PRIVATE_SLUG}_preview_main.stl")
        assert res.status_code == 403
        body = res.get_json()
        assert body["error_code"] == "project_locked"
        assert body["auth_required"] is True

    def test_private_artifact_is_served_to_an_entitled_caller(self, client):
        res = client.get(f"/static/{PRIVATE_SLUG}_preview_main.stl",
                         headers=auth("tok-madfam"))
        assert res.status_code == 200
        assert res.headers["Cache-Control"] == "private, no-store"

    def test_unrelated_static_file_is_unaffected(self, client, app):
        from config import Config
        (Config.STATIC_DIR / "logo.txt").write_text("hello")
        res = client.get("/static/logo.txt")
        assert res.status_code == 200
        assert "no-store" not in res.headers.get("Cache-Control", "")

    def test_env_forced_private_covers_artifacts_too(self, client, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, PUBLIC_SLUG)
        assert client.get(f"/static/{PUBLIC_SLUG}_preview_main.stl").status_code == 403


class TestLegacyQueryStringRoutes:
    """The pre-multi-project routes take ``?project=<slug>`` (or a body slug)
    instead of a path slug. They serve the same manifest content, so they
    answer the same gate. Production served a private cartridge's manifest
    through ``/api/manifest?project=`` while ``/api/projects/<slug>/manifest``
    refused it; these pin the four routes that read a manifest by slug.
    """

    def test_legacy_manifest_public_project_is_unaffected(self, client):
        res = client.get(f"/api/manifest?project={PUBLIC_SLUG}")
        assert res.status_code == 200
        assert res.headers["Cache-Control"] == "public, max-age=300"
        assert res.headers.get("ETag")
        assert res.get_json()["project"]["slug"] == PUBLIC_SLUG

    def test_legacy_manifest_is_locked_for_anonymous(self, client):
        res = client.get(f"/api/manifest?project={PRIVATE_SLUG}")
        assert res.status_code == 403
        body = res.get_json()
        assert body["error_code"] == "project_locked"
        assert body["auth_required"] is True

    def test_legacy_manifest_is_locked_for_an_unentitled_user(self, client):
        res = client.get(f"/api/manifest?project={PRIVATE_SLUG}",
                         headers=auth("tok-essentials"))
        assert res.status_code == 403
        assert res.get_json()["auth_required"] is False

    def test_legacy_manifest_is_served_to_an_entitled_caller_uncached(self, client):
        res = client.get(f"/api/manifest?project={PRIVATE_SLUG}",
                         headers=auth("tok-madfam"))
        assert res.status_code == 200
        assert res.get_json()["project"]["slug"] == PRIVATE_SLUG
        assert res.headers["Cache-Control"] == "private, no-store"
        assert "ETag" not in res.headers

    def test_legacy_manifest_env_forced_private_beats_a_public_manifest(self, client, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, PUBLIC_SLUG)
        assert client.get(f"/api/manifest?project={PUBLIC_SLUG}").status_code == 403
        assert client.get(f"/api/manifest?project={PUBLIC_SLUG}",
                          headers=auth("tok-madfam")).status_code == 200

    def test_legacy_manifest_unknown_project_still_404s(self, client):
        assert client.get("/api/manifest?project=no-such-widget").status_code == 404

    def test_legacy_config_is_gated(self, client):
        assert client.get(f"/api/config?project={PUBLIC_SLUG}").status_code == 200
        res = client.get(f"/api/config?project={PRIVATE_SLUG}")
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"
        ok = client.get(f"/api/config?project={PRIVATE_SLUG}", headers=auth("tok-madfam"))
        assert ok.status_code == 200
        assert ok.headers["Cache-Control"] == "private, no-store"
        assert "parts_map" in ok.get_json()

    def test_estimate_is_gated(self, client):
        body = {"project": PRIVATE_SLUG, "mode": "single", "params": {}}
        res = client.post("/api/estimate", json=body)
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"
        assert client.post("/api/estimate", json={**body, "project": PUBLIC_SLUG}).status_code == 200
        assert client.post("/api/estimate", json=body, headers=auth("tok-madfam")).status_code == 200

    def test_ai_session_is_gated(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "AI_API_KEY", "test-key")
        body = {"project": PRIVATE_SLUG, "mode": "configurator"}
        res = client.post("/api/ai/session", json=body, headers=auth("tok-essentials"))
        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"
        ok = client.post("/api/ai/session", json=body, headers=auth("tok-madfam"))
        assert ok.status_code == 200
        assert ok.get_json()["session_id"]
