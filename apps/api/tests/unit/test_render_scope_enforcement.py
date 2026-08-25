"""Tests for yantra4d:render scope enforcement on MACHINE (client_credentials) tokens.

Ruled 2026-08-25: the scope Janua mints for FC was decorative server-side. These
tests pin the two invariants that ruling rests on:

  1. Anonymous and human traffic behave EXACTLY as before — this enforcement is
     scoped to machine tokens only.
  2. A conformant machine token (FC's exact shape) keeps resolving its
     `yantra4d_tier` claim untouched, so the live FC -> Yantra4D MTM render
     seam does not regress.

Claim shapes mirror janua apps/api/app/routers/v1/oauth_provider.py
::_get_client_credentials_claims and ::_handle_client_credentials_grant.
"""
import logging
from unittest.mock import patch

import pytest
from flask import Flask, jsonify, request

from middleware.auth import (
    RENDER_SCOPE,
    is_machine_token,
    machine_client_id,
    optional_auth,
    render_scope_enforcement_mode,
    require_render_scope,
    token_scopes,
)
from services.core.tier_service import resolve_tier


@pytest.fixture(autouse=True)
def _enable_auth(monkeypatch):
    """Scope enforcement is a no-op when AUTH_ENABLED is off (conftest disables it)."""
    from config import Config
    monkeypatch.setattr(Config, "AUTH_ENABLED", True)


@pytest.fixture(autouse=True)
def _default_log_mode(monkeypatch):
    """Every test states its own mode; default the env to unset (=> log)."""
    monkeypatch.delenv("RENDER_SCOPE_ENFORCEMENT", raising=False)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/api/render", methods=["POST"])
    @optional_auth
    @require_render_scope
    def render():
        claims = getattr(request, "auth_claims", None)
        return jsonify({"ok": True, "tier": resolve_tier(claims)})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ── Token fixtures ────────────────────────────────────────────────────────────

# A human browser session: UUID sub, no token_use / actor_type / client_id / scope.
HUMAN_CLAIMS = {
    "sub": "6f1c9a10-3e4b-4c8a-9d2f-77b1e0a4c531",
    "email": "aldo@madfam.io",
    "iss": "https://auth.madfam.io",
    "aud": "yantra4d-api",
    "roles": ["user"],
    "yantra4d_tier": "pro",
    "exp": 9999999999,
}

# Fashion Cabinet's EXACT machine-token shape: what Janua returns for a
# confidential client requesting scope "yantra4d:render" against audience
# "yantra4d-api". The yantra4d_tier=madfam claim is DERIVED by Janua from the
# "yantra4d:" scope namespace — this is the claim the live MTM seam depends on.
FC_MACHINE_CLAIMS = {
    "sub": "service-account:fc-render-client",
    "email": "fashion-cabinet@service.auth.madfam.io",
    "iss": "https://auth.madfam.io",
    "aud": "yantra4d-api",
    "client_id": "fc-render-client",
    "scope": "yantra4d:render",
    "token_use": "client_credentials",
    "actor_type": "service_account",
    "roles": ["service_account"],
    "is_admin": False,
    "tier": "community",
    "sub_status": "active",
    "yantra4d_tier": "madfam",
    "exp": 9999999999,
}

# A machine client provisioned for some OTHER product namespace. It authenticates
# fine against this audience but never asked for yantra4d:render.
MACHINE_NO_SCOPE_CLAIMS = {
    "sub": "service-account:other-client",
    "email": "other@service.auth.madfam.io",
    "iss": "https://auth.madfam.io",
    "aud": "yantra4d-api",
    "client_id": "other-client",
    "scope": "forgesight:read dhanam:write",
    "token_use": "client_credentials",
    "actor_type": "service_account",
    "roles": ["service_account"],
    "tier": "community",
    "exp": 9999999999,
}


def _post(client, claims):
    """POST /api/render with `claims` as the decoded token (None => anonymous)."""
    if claims is None:
        return client.post("/api/render", json={})
    with patch("middleware.auth.decode_token", return_value=claims):
        return client.post(
            "/api/render", json={}, headers={"Authorization": "Bearer t"}
        )


# ── Machine-token detection ───────────────────────────────────────────────────

class TestMachineTokenDetection:
    def test_anonymous_is_not_machine(self):
        assert is_machine_token(None) is False

    def test_human_token_is_not_machine(self):
        assert is_machine_token(HUMAN_CLAIMS) is False

    def test_fc_token_is_machine(self):
        assert is_machine_token(FC_MACHINE_CLAIMS) is True

    @pytest.mark.parametrize(
        "claims",
        [
            {"token_use": "client_credentials"},
            {"actor_type": "service_account"},
            {"sub": "service-account:abc"},
        ],
        ids=["token_use", "actor_type", "service-account-sub"],
    )
    def test_any_single_machine_marker_suffices(self, claims):
        """Detection fails toward 'machine' on a partial claim set."""
        assert is_machine_token(claims) is True

    def test_client_id_prefers_claim_then_falls_back_to_sub(self):
        assert machine_client_id(FC_MACHINE_CLAIMS) == "fc-render-client"
        assert machine_client_id({"sub": "service-account:abc"}) == "abc"

    @pytest.mark.parametrize(
        "claims,expected",
        [
            ({"scope": "a b  c"}, {"a", "b", "c"}),
            ({"scope": ["a", "b"]}, {"a", "b"}),
            ({"scp": "a b"}, {"a", "b"}),
            ({}, set()),
            (None, set()),
        ],
    )
    def test_scope_parsing(self, claims, expected):
        assert token_scopes(claims) == expected


# ── Enforcement-mode resolution ───────────────────────────────────────────────

class TestEnforcementMode:
    def test_defaults_to_log_when_unset(self):
        assert render_scope_enforcement_mode() == "log"

    @pytest.mark.parametrize("value", ["enforce", "ENFORCE", "1", "true", "yes", "on"])
    def test_enforce_values(self, monkeypatch, value):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", value)
        assert render_scope_enforcement_mode() == "enforce"

    @pytest.mark.parametrize("value", ["log", "LOG", "", "  "])
    def test_log_values(self, monkeypatch, value):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", value)
        assert render_scope_enforcement_mode() == "log"

    def test_unrecognised_value_falls_back_to_log(self, monkeypatch, caplog):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "banana")
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            assert render_scope_enforcement_mode() == "log"
        assert "Unrecognised RENDER_SCOPE_ENFORCEMENT" in caplog.text


# ── The matrix: both modes x every caller shape ───────────────────────────────

class TestUnaffectedCallers:
    """Anonymous and human access must be EXACTLY as before, in both modes."""

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_anonymous_unchanged(self, client, monkeypatch, mode):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        resp = _post(client, None)
        assert resp.status_code == 200
        assert resp.get_json()["tier"] == "guest"

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_human_token_unchanged(self, client, monkeypatch, mode):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        resp = _post(client, HUMAN_CLAIMS)
        assert resp.status_code == 200
        assert resp.get_json()["tier"] == "pro"

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_human_token_without_scope_claim_is_never_denied(
        self, client, monkeypatch, mode
    ):
        """A human token carries no `scope` claim at all — that must not read as
        'machine token missing the scope'."""
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        assert "scope" not in HUMAN_CLAIMS
        resp = _post(client, HUMAN_CLAIMS)
        assert resp.status_code == 200

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_no_warning_emitted_for_unaffected_callers(
        self, client, monkeypatch, mode, caplog
    ):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            _post(client, None)
            _post(client, HUMAN_CLAIMS)
        assert "render.scope_missing" not in caplog.text


class TestMachineTokenWithScope:
    """FC's conformance proof — the live MTM seam."""

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_fc_token_allowed_and_keeps_madfam_tier(self, client, monkeypatch, mode):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        resp = _post(client, FC_MACHINE_CLAIMS)
        assert resp.status_code == 200
        # The tier claim must resolve exactly as it does today. Regressing this
        # breaks the live FC -> Yantra4D MTM body render.
        assert resp.get_json()["tier"] == "madfam"

    def test_fc_token_carries_the_render_scope(self):
        assert RENDER_SCOPE in token_scopes(FC_MACHINE_CLAIMS)

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_no_warning_for_conformant_machine_token(
        self, client, monkeypatch, mode, caplog
    ):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            _post(client, FC_MACHINE_CLAIMS)
        assert "render.scope_missing" not in caplog.text

    @pytest.mark.parametrize("mode", ["log", "enforce"])
    def test_extra_scopes_alongside_render_still_pass(
        self, client, monkeypatch, mode
    ):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", mode)
        claims = {**FC_MACHINE_CLAIMS, "scope": "yantra4d:render yantra4d:catalog"}
        assert _post(client, claims).status_code == 200


class TestMachineTokenWithoutScope:
    def test_log_mode_warns_and_allows(self, client, monkeypatch, caplog):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "log")
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            resp = _post(client, MACHINE_NO_SCOPE_CLAIMS)
        assert resp.status_code == 200, "log mode must not deny"
        assert "render.scope_missing" in caplog.text

    def test_log_mode_warning_is_structured(self, client, monkeypatch, caplog):
        """Structured fields an operator greps during the observation window."""
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "log")
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            _post(client, MACHINE_NO_SCOPE_CLAIMS)
        text = caplog.text
        assert "render.scope_missing" in text
        assert "client_id=other-client" in text
        assert "missing_scope=yantra4d:render" in text
        assert "present_scopes=dhanam:write,forgesight:read" in text
        assert "path=/api/render" in text
        assert "mode=log" in text
        assert "outcome=allowed" in text

    def test_default_env_is_log_mode(self, client, caplog):
        """No env set at all => warn-and-allow. Rollout is opt-in."""
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            resp = _post(client, MACHINE_NO_SCOPE_CLAIMS)
        assert resp.status_code == 200
        assert "mode=log" in caplog.text

    def test_enforce_mode_returns_403(self, client, monkeypatch):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "enforce")
        resp = _post(client, MACHINE_NO_SCOPE_CLAIMS)
        assert resp.status_code == 403
        body = resp.get_json()
        assert body["error_code"] == "missing_scope"
        assert RENDER_SCOPE in body["error"]

    def test_enforce_mode_warning_records_denial(self, client, monkeypatch, caplog):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "enforce")
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            _post(client, MACHINE_NO_SCOPE_CLAIMS)
        assert "mode=enforce" in caplog.text
        assert "outcome=denied" in caplog.text

    def test_machine_token_with_no_scope_claim_at_all(self, client, monkeypatch):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "enforce")
        claims = {k: v for k, v in MACHINE_NO_SCOPE_CLAIMS.items() if k != "scope"}
        assert _post(client, claims).status_code == 403

    def test_never_echoes_the_token(self, client, monkeypatch, caplog):
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "enforce")
        with caplog.at_level(logging.WARNING, logger="middleware.auth"):
            _post(client, MACHINE_NO_SCOPE_CLAIMS)
        assert "Bearer" not in caplog.text


class TestAuthDisabled:
    """AUTH_ENABLED=false (local dev / CI) short-circuits everything, as before."""

    def test_enforce_mode_is_noop_when_auth_disabled(
        self, client, monkeypatch
    ):
        from config import Config
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setenv("RENDER_SCOPE_ENFORCEMENT", "enforce")
        assert client.post("/api/render", json={}).status_code == 200
