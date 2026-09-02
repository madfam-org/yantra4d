"""Tests for private-project access control.

Every address here is an example.com address. The real grant map and private
slug list are deployment configuration (a Kubernetes secret), never repository
content.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.project_access import (
    PRIVATE_PROJECTS_ENV,
    PROJECT_ACCESS_GRANTS_ENV,
    artifact_slug_candidates,
    can_view_project,
    is_private_project,
    private_project_slugs,
    project_access_grants,
)
from services.core.tier_service import TIER_OVERRIDES_ENV, load_tier_overrides

PUBLIC_MANIFEST = {"project": {"slug": "widget"}}
PRIVATE_MANIFEST = {"project": {"slug": "widget"}, "access_control": {"view": "private"}}
AUTHENTICATED_MANIFEST = {"access_control": {"view": "authenticated"}}

ANON = None
ESSENTIALS = {"sub": "u1", "email": "someone@example.com"}
PRO = {"sub": "u2", "email": "pro@example.com", "yantra4d_tier": "pro"}
TOP = {"sub": "u3", "email": "staff@example.com", "yantra4d_tier": "madfam"}
ADMIN = {"sub": "u4", "email": "admin@example.com", "roles": ["admin"]}
ADMIN_SINGULAR = {"sub": "u5", "email": "admin2@example.com", "role": "admin"}
GRANTED = {"sub": "u6", "email": "guest-of-honour@example.com"}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """All three loaders cache per raw value; start every test from unset."""
    for name in (PRIVATE_PROJECTS_ENV, PROJECT_ACCESS_GRANTS_ENV, TIER_OVERRIDES_ENV):
        monkeypatch.delenv(name, raising=False)
    private_project_slugs()
    project_access_grants()
    load_tier_overrides()
    yield


class TestPrivateProjectsEnv:
    def test_unset(self):
        assert private_project_slugs() == frozenset()

    def test_single_slug(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "widget")
        assert private_project_slugs() == frozenset({"widget"})

    def test_comma_separated_with_whitespace(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, " widget , other-thing ,")
        assert private_project_slugs() == frozenset({"widget", "other-thing"})

    def test_case_is_normalized(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "Widget")
        assert private_project_slugs() == frozenset({"widget"})

    def test_malformed_slug_is_dropped(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "widget,../etc/passwd")
        assert private_project_slugs() == frozenset({"widget"})


class TestAccessGrantsEnv:
    def test_unset(self):
        assert project_access_grants() == {}

    def test_invalid_json_fails_closed(self, monkeypatch):
        monkeypatch.setenv(PROJECT_ACCESS_GRANTS_ENV, "{oops")
        assert project_access_grants() == {}

    def test_non_object_fails_closed(self, monkeypatch):
        monkeypatch.setenv(PROJECT_ACCESS_GRANTS_ENV, '["someone@example.com"]')
        assert project_access_grants() == {}

    def test_emails_are_lower_cased(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({"widget": ["  Someone@Example.COM "]}),
        )
        assert project_access_grants() == {"widget": frozenset({"someone@example.com"})}

    def test_bare_string_is_accepted_as_one_email(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV, json.dumps({"widget": "someone@example.com"}),
        )
        assert project_access_grants() == {"widget": frozenset({"someone@example.com"})}

    def test_non_list_entry_is_dropped(self, monkeypatch):
        monkeypatch.setenv(PROJECT_ACCESS_GRANTS_ENV, json.dumps({"widget": 42}))
        assert project_access_grants() == {}


class TestIsPrivateProject:
    def test_public_manifest(self):
        assert is_private_project("widget", PUBLIC_MANIFEST) is False

    def test_no_manifest(self):
        assert is_private_project("widget", None) is False

    def test_manifest_flag(self):
        assert is_private_project("widget", PRIVATE_MANIFEST) is True

    def test_authenticated_is_not_private(self):
        """`authenticated` keeps its existing meaning; only `private` locks."""
        assert is_private_project("widget", AUTHENTICATED_MANIFEST) is False

    def test_env_forces_private_over_a_public_manifest(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "widget")
        assert is_private_project("widget", PUBLIC_MANIFEST) is True

    def test_env_does_not_leak_to_other_slugs(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "widget")
        assert is_private_project("other", PUBLIC_MANIFEST) is False

    def test_accepts_a_manifest_object(self, monkeypatch):
        class FakeManifest:
            _data = PRIVATE_MANIFEST

        assert is_private_project("widget", FakeManifest()) is True


class TestCanViewPublicProject:
    """A public project is unaffected by any of this machinery."""

    @pytest.mark.parametrize("claims", [ANON, ESSENTIALS, PRO, TOP, ADMIN])
    def test_everyone_can_view(self, claims):
        assert can_view_project("widget", PUBLIC_MANIFEST, claims) is True


class TestCanViewPrivateProject:
    def test_anonymous_is_refused(self):
        assert can_view_project("widget", PRIVATE_MANIFEST, ANON) is False

    def test_signed_in_without_entitlement_is_refused(self):
        assert can_view_project("widget", PRIVATE_MANIFEST, ESSENTIALS) is False

    def test_pro_is_not_enough(self):
        """Privacy is not a paywall — a paid tier is still not this project's."""
        assert can_view_project("widget", PRIVATE_MANIFEST, PRO) is False

    def test_top_tier_can_view(self):
        assert can_view_project("widget", PRIVATE_MANIFEST, TOP) is True

    def test_admin_role_can_view(self):
        assert can_view_project("widget", PRIVATE_MANIFEST, ADMIN) is True

    def test_singular_role_claim_can_view(self):
        assert can_view_project("widget", PRIVATE_MANIFEST, ADMIN_SINGULAR) is True

    def test_granted_email_can_view(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({"widget": ["guest-of-honour@example.com"]}),
        )
        assert can_view_project("widget", PRIVATE_MANIFEST, GRANTED) is True

    def test_grant_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV, json.dumps({"widget": ["Guest-Of-Honour@Example.com"]}),
        )
        assert can_view_project("widget", PRIVATE_MANIFEST, GRANTED) is True

    def test_grant_is_scoped_to_its_slug(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({"other-thing": ["guest-of-honour@example.com"]}),
        )
        assert can_view_project("widget", PRIVATE_MANIFEST, GRANTED) is False

    def test_grant_does_not_help_an_anonymous_caller(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({"widget": ["guest-of-honour@example.com"]}),
        )
        assert can_view_project("widget", PRIVATE_MANIFEST, ANON) is False

    def test_tier_override_reaches_a_private_project(self, monkeypatch):
        """The staff identity path: TIER_OVERRIDES seats them at the top tier."""
        monkeypatch.setenv(TIER_OVERRIDES_ENV, json.dumps({"staff@example.com": "madfam"}))
        claims = {"sub": "u9", "email": "staff@example.com"}
        assert can_view_project("widget", PRIVATE_MANIFEST, claims) is True


class TestCanViewEnvForcedPrivateProject:
    """PRIVATE_PROJECTS must hold even when the manifest says public."""

    @pytest.fixture(autouse=True)
    def _force(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "widget")

    @pytest.mark.parametrize("claims", [ANON, ESSENTIALS, PRO])
    def test_unentitled_callers_are_refused(self, claims):
        assert can_view_project("widget", PUBLIC_MANIFEST, claims) is False

    @pytest.mark.parametrize("claims", [TOP, ADMIN])
    def test_entitled_callers_can_view(self, claims):
        assert can_view_project("widget", PUBLIC_MANIFEST, claims) is True

    def test_granted_email_can_view(self, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({"widget": ["guest-of-honour@example.com"]}),
        )
        assert can_view_project("widget", PUBLIC_MANIFEST, GRANTED) is True

    def test_works_without_any_manifest_at_all(self):
        assert can_view_project("widget", None, ESSENTIALS) is False
        assert can_view_project("widget", None, TOP) is True


class TestArtifactSlugCandidates:
    def test_standard_artifact_name(self):
        assert artifact_slug_candidates("widget_preview_body.stl") == ["widget"]

    def test_hyphenated_slug(self):
        assert artifact_slug_candidates("test-project_preview_main.3mf") == ["test-project"]

    def test_unprefixed_legacy_name_is_not_a_project(self):
        assert artifact_slug_candidates("preview_body.stl") == []

    def test_unrelated_file(self):
        assert artifact_slug_candidates("logo.png") == []

    def test_ambiguous_name_yields_every_candidate(self):
        """A slug may itself contain the marker, so the split point is ambiguous
        and every well-formed candidate has to be checked."""
        assert artifact_slug_candidates("abc_preview_def_preview_body.stl") == [
            "abc", "abc_preview_def",
        ]

    def test_directory_prefix_is_ignored(self):
        assert artifact_slug_candidates("nested/widget_preview_body.stl") == ["widget"]

    def test_malformed_slug_is_not_a_candidate(self):
        assert artifact_slug_candidates("A_preview_body.stl") == []


class TestDevUnlock:
    """Auth off alone must NOT unlock a private project; auth off + debug does."""

    def _private(self, monkeypatch):
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, "client-widget")

    def test_auth_off_without_debug_stays_locked(self, monkeypatch):
        from flask import Flask

        from config import Config
        self._private(monkeypatch)
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        app = Flask("t")
        app.debug = False
        with app.app_context():
            assert can_view_project("client-widget", {}, None) is False

    def test_auth_off_with_debug_unlocks(self, monkeypatch):
        from flask import Flask

        from config import Config
        self._private(monkeypatch)
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        app = Flask("t")
        app.debug = True
        with app.app_context():
            assert can_view_project("client-widget", {}, None) is True

    def test_auth_on_ignores_debug(self, monkeypatch):
        from flask import Flask

        from config import Config
        self._private(monkeypatch)
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        app = Flask("t")
        app.debug = True
        with app.app_context():
            assert can_view_project("client-widget", {}, None) is False

    def test_no_app_context_stays_locked(self, monkeypatch):
        from config import Config
        self._private(monkeypatch)
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        assert can_view_project("client-widget", {}, None) is False
