"""Read authorisation on the non-render WebSocket channels.

PR #83 gave the WebSocket module an identity (`resolve_ws_claims`) and closed
the render channel's mutating `cancel`. It left the two broadcast channels
anonymous-readable on the reasoning that a read-only stream discloses nothing.
That reasoning does not survive contact with the HTTP routes:

  * `/api/ws/printer/<id>` forwards the same shop-floor status that
    `GET /api/printers/<id>/status` proxies, and that route is
    `@require_tier("pro")`. Connecting to the socket instead of calling the
    route skipped the tier gate entirely — a bypass, not a dashboard feed.
  * `/api/ws/telemetry/<slug>` streams live MQTT sensor data for one project,
    including projects the private-project gate (#78) exists to withhold. No
    HTTP route serves that anonymously, so nothing here was "already public".

These tests pin the resulting matrix (docs/AUTH.md § WebSocket channels):

  1. printer  — refused anonymously and below `pro`; served at `pro` and above.
  2. telemetry — refused anonymously; refused for a private project the caller
     may not view; served for a public project to a signed-in caller and for a
     private one to an entitled caller.
  3. render   — still anonymous-readable (ping/pong), unchanged by this file.
  4. A refused connection is answered with exactly one error frame and no
     payload: no heartbeat, no telemetry, no queue read.

They live in tests/unit alongside tests/unit/test_ws_render_channel_auth.py
rather than tests/e2e: a flask-sock handler is not reachable through Flask's
test client (it never returns a response), so the handler is driven directly
inside a request context, exactly as that file does. The private-project
cartridge fixtures follow tests/e2e/test_private_projects_api.py.

Every address here is an example.com address. The production grant map is a
Kubernetes secret and never repository content.
"""
import json
from unittest.mock import patch

import pytest
from flask import Flask

from routes.core import websocket as ws_mod
from routes.core.websocket import (
    WS_UNAUTHORISED,
    printer_read_denial,
    telemetry_read_denial,
    ws_printer,
    ws_render,
    ws_telemetry,
)
from services.core.project_access import (
    PRIVATE_PROJECTS_ENV,
    PROJECT_ACCESS_GRANTS_ENV,
    private_project_slugs,
    project_access_grants,
)
from services.core.tier_service import TIER_OVERRIDES_ENV, load_tier_overrides

PUBLIC_SLUG = "open-widget"
PRIVATE_SLUG = "secret-widget"

GUEST_CLAIMS = {"sub": "u1", "email": "someone@example.com"}
PRO_CLAIMS = {"sub": "u2", "email": "pro@example.com", "yantra4d_tier": "pro"}
TOP_CLAIMS = {"sub": "u3", "email": "boss@example.com", "yantra4d_tier": "madfam"}
ADMIN_CLAIMS = {"sub": "u4", "email": "admin@example.com", "roles": ["admin"]}
# Fashion Cabinet's exact machine-token shape. Janua synthesises
# `yantra4d_tier: "madfam"` for any machine client holding a `yantra4d:`-
# namespaced scope (docs/AUTH.md § Machine tokens), which is what seats this
# token above the printer gate — through `resolve_tier`, like every other
# caller, not by being a machine.
MACHINE_CLAIMS = {
    "sub": "service-account:fashion-cabinet",
    "token_use": "client_credentials",
    "actor_type": "service_account",
    "client_id": "fashion-cabinet",
    "scope": "yantra4d:render",
    "yantra4d_tier": "madfam",
}

TOKENS = {
    "tok-guest": GUEST_CLAIMS,
    "tok-pro": PRO_CLAIMS,
    "tok-top": TOP_CLAIMS,
    "tok-admin": ADMIN_CLAIMS,
}


class FakeWS:
    """Scripted stand-in for a simple_websocket Server connection."""

    def __init__(self, inbound=()):
        self._inbound = list(inbound)
        self.sent = []

    def receive(self, timeout=None):
        if not self._inbound:
            # Mirrors simple_websocket closing the socket: the handler's broad
            # `except Exception` catches it and the loop ends.
            raise ConnectionResetError("client went away")
        return self._inbound.pop(0)

    def send(self, data):
        self.sent.append(json.loads(data))

    def replies(self):
        return self.sent


@pytest.fixture(autouse=True)
def _reset_connection_counts():
    ws_mod._connection_counts.clear()
    yield
    ws_mod._connection_counts.clear()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Reset the call-time config loaders between tests."""
    for name in (PRIVATE_PROJECTS_ENV, PROJECT_ACCESS_GRANTS_ENV, TIER_OVERRIDES_ENV):
        monkeypatch.delenv(name, raising=False)
    private_project_slugs()
    project_access_grants()
    load_tier_overrides()
    yield


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


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A minimal app plus two cartridges — one public, one private — auth ON.

    Auth is genuinely enabled here (the shared conftest turns it off globally),
    so the gates run the same comparison they run in production. `decode_token`
    is patched the way tests/e2e/test_private_projects_api.py patches it, so a
    handshake carrying a Bearer travels the real `resolve_ws_claims` path.
    """
    from config import Config

    for slug, private in ((PUBLIC_SLUG, False), (PRIVATE_SLUG, True)):
        project_dir = tmp_path / slug
        project_dir.mkdir()
        (project_dir / "project.json").write_text(json.dumps(_manifest(slug, private)))
        (project_dir / "main.scad").write_text("cube(10);")

    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])
    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr("middleware.auth._sync_user_from_claims", lambda claims: None)

    def fake_decode(token):
        if token in TOKENS:
            return TOKENS[token]
        raise ValueError("invalid token")

    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    with patch("middleware.auth.decode_token", side_effect=fake_decode):
        yield flask_app


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _refusal(replies):
    """The single refusal frame a denied reader must get, and nothing else."""
    assert len(replies) == 1, f"a refused reader must see one frame, got {replies}"
    frame = replies[0]
    assert frame["type"] == "error"
    assert frame["error"] == WS_UNAUTHORISED
    return frame


# ──────────────────────────────────────────────
# 1. Printer channel — mirrors @require_tier("pro")
# ──────────────────────────────────────────────

class TestPrinterChannel:
    def test_anonymous_is_refused_and_sees_no_status(self, app):
        ws = FakeWS()
        with app.test_request_context("/api/ws/printer/ender3"):
            ws_printer(ws, "ender3")

        frame = _refusal(ws.replies())
        assert frame["reason"] == "authentication_required"
        # The heartbeat carries mqtt_connected and the printer id: a refused
        # reader must never reach it.
        assert all(r["type"] != "heartbeat" for r in ws.replies())

    def test_signed_in_below_pro_is_refused_with_the_tier_reason(self, app):
        ws = FakeWS()
        with app.test_request_context("/api/ws/printer/ender3",
                                      headers=bearer("tok-guest")):
            ws_printer(ws, "ender3")

        frame = _refusal(ws.replies())
        assert frame["reason"] == "insufficient_tier"
        assert "pro" in frame["message"]

    @pytest.mark.parametrize("token", ["tok-pro", "tok-top"])
    def test_pro_and_above_are_served(self, app, token):
        ws = FakeWS()
        with app.test_request_context("/api/ws/printer/ender3",
                                      headers=bearer(token)):
            ws_printer(ws, "ender3")

        assert ws.replies(), "an entitled reader must receive the stream"
        assert ws.replies()[0]["type"] == "heartbeat"
        assert ws.replies()[0]["printer_id"] == "ender3"

    def test_an_invalid_token_is_treated_as_anonymous(self, app):
        """A bearer that fails validation must not be a way in."""
        ws = FakeWS()
        with app.test_request_context("/api/ws/printer/ender3",
                                      headers=bearer("tok-forged")):
            ws_printer(ws, "ender3")

        assert _refusal(ws.replies())["reason"] == "authentication_required"

    def test_gate_matches_the_http_route_tier(self):
        """The socket's tier and the HTTP route's tier are the same constant.

        `GET /api/printers/<id>/status` is `@require_tier("pro")`. If that ever
        moves, this fails rather than leaving the socket on the old tier.
        """
        import inspect

        from routes.integrations import printer as printer_routes

        source = inspect.getsource(printer_routes.get_printer_status)
        assert f'@require_tier("{ws_mod.PRINTER_MIN_TIER}")' in source

    def test_denial_helper_is_pure(self, app):
        with app.test_request_context("/"):
            assert printer_read_denial(None)[0] == "authentication_required"
            assert printer_read_denial(GUEST_CLAIMS)[0] == "insufficient_tier"
            assert printer_read_denial(PRO_CLAIMS) is None
            assert printer_read_denial(TOP_CLAIMS) is None


# ──────────────────────────────────────────────
# 2. Telemetry channel — identity, then the private-project gate
# ──────────────────────────────────────────────

class TestTelemetryChannel:
    def test_anonymous_is_refused_on_a_public_project(self, app):
        """Read-only is not public: no HTTP route hands telemetry to anonymous."""
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PUBLIC_SLUG}"):
            ws_telemetry(ws, PUBLIC_SLUG)

        assert _refusal(ws.replies())["reason"] == "authentication_required"

    def test_signed_in_reader_is_served_a_public_project(self, app):
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PUBLIC_SLUG}",
                                      headers=bearer("tok-guest")):
            ws_telemetry(ws, PUBLIC_SLUG)

        assert ws.replies(), "an entitled reader must receive the stream"
        assert ws.replies()[0]["type"] == "heartbeat"

    def test_private_project_is_refused_to_an_unentitled_identity(self, app):
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PRIVATE_SLUG}",
                                      headers=bearer("tok-guest")):
            ws_telemetry(ws, PRIVATE_SLUG)

        frame = _refusal(ws.replies())
        assert frame["reason"] == "project_locked"
        assert all(r["type"] != "telemetry" for r in ws.replies())

    @pytest.mark.parametrize("token", ["tok-top", "tok-admin"])
    def test_private_project_is_served_to_an_entitled_identity(self, app, token):
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PRIVATE_SLUG}",
                                      headers=bearer(token)):
            ws_telemetry(ws, PRIVATE_SLUG)

        assert ws.replies()[0]["type"] == "heartbeat"

    def test_configuration_can_force_a_public_project_private(self, app, monkeypatch):
        """PRIVATE_PROJECTS wins over the manifest here exactly as it does on HTTP."""
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, PUBLIC_SLUG)
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PUBLIC_SLUG}",
                                      headers=bearer("tok-guest")):
            ws_telemetry(ws, PUBLIC_SLUG)

        assert _refusal(ws.replies())["reason"] == "project_locked"

    def test_a_per_identity_grant_opens_a_private_project(self, app, monkeypatch):
        monkeypatch.setenv(
            PROJECT_ACCESS_GRANTS_ENV,
            json.dumps({PRIVATE_SLUG: [GUEST_CLAIMS["email"]]}),
        )
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PRIVATE_SLUG}",
                                      headers=bearer("tok-guest")):
            ws_telemetry(ws, PRIVATE_SLUG)

        assert ws.replies()[0]["type"] == "heartbeat"

    def test_a_malformed_slug_never_reaches_the_manifest_lookup(self, app):
        ws = FakeWS()
        with patch("services.core.project_access._private_and_manifest") as lookup, \
                app.test_request_context("/api/ws/telemetry/..%2Fetc"):
            ws_telemetry(ws, "../etc")

        assert _refusal(ws.replies())["reason"] == "invalid_project"
        lookup.assert_not_called()

    def test_denial_helper_is_pure(self, app):
        with app.test_request_context("/"):
            assert telemetry_read_denial(PUBLIC_SLUG, None)[0] == "authentication_required"
            assert telemetry_read_denial(PUBLIC_SLUG, GUEST_CLAIMS) is None
            assert telemetry_read_denial(PRIVATE_SLUG, GUEST_CLAIMS)[0] == "project_locked"
            assert telemetry_read_denial(PRIVATE_SLUG, TOP_CLAIMS) is None


# ──────────────────────────────────────────────
# 3. A refused reader touches nothing behind the gate
# ──────────────────────────────────────────────

def test_a_refused_telemetry_reader_never_reads_the_queue(app):
    """The gate runs before the MQTT queue is touched, not after."""
    import services.core.mqtt_telemetry as mqtt

    with patch.object(mqtt.telemetry_queue, "get", side_effect=AssertionError(
        "a refused reader must not consume telemetry"
    )):
        ws = FakeWS()
        with app.test_request_context(f"/api/ws/telemetry/{PUBLIC_SLUG}"):
            ws_telemetry(ws, PUBLIC_SLUG)

    assert _refusal(ws.replies())["reason"] == "authentication_required"


def test_a_refused_reader_does_not_hold_a_connection_slot(app):
    """Refusal releases before the loop, so a denied flood cannot fill the cap."""
    for _ in range(ws_mod.WS_MAX_CONNECTIONS_PER_IP + 3):
        ws = FakeWS()
        with app.test_request_context("/api/ws/printer/ender3"):
            ws_printer(ws, "ender3")
        assert _refusal(ws.replies())["reason"] == "authentication_required"

    assert not ws_mod._connection_counts, (
        "refused connections must not leave slots reserved"
    )


def test_refusal_logs_the_reason_without_the_subject(app, caplog):
    """Logs carry the coarse identity label, never the caller's `sub` or token."""
    with app.test_request_context("/api/ws/printer/ender3",
                                  headers=bearer("tok-guest")), \
            caplog.at_level("WARNING", logger="routes.core.websocket"):
        ws_printer(FakeWS(), "ender3")

    messages = [rec.getMessage() for rec in caplog.records]
    assert any("read refused" in m and "reason=insufficient_tier" in m for m in messages)
    assert not any(GUEST_CLAIMS["sub"] in m or "tok-guest" in m for m in messages)


# ──────────────────────────────────────────────
# 4. The render channel keeps the posture #83 gave it
# ──────────────────────────────────────────────

def test_render_channel_remains_anonymous_readable(app):
    """Unchanged: it answers ping/pong and refuses `cancel` to everyone."""
    ws = FakeWS([json.dumps({"action": "ping"})])
    with app.test_request_context("/api/ws/render/s1"):
        ws_render(ws, "s1")

    assert ws.replies()[0]["type"] == "pong"


def test_machine_tokens_are_gated_by_tier_like_anyone_else(app):
    """A machine token is not a bypass: it is gated on its resolved tier."""
    with app.test_request_context("/"):
        denial = printer_read_denial(MACHINE_CLAIMS)

    # The synthesised top tier is what entitles it — the same comparison every
    # other caller goes through, not a special case for machines.
    assert denial is None
    with app.test_request_context("/"):
        stripped = {k: v for k, v in MACHINE_CLAIMS.items() if k != "yantra4d_tier"}
        assert printer_read_denial(stripped)[0] == "insufficient_tier"


# ──────────────────────────────────────────────
# 5. AUTH_ENABLED off behaves as it does on the HTTP routes
# ──────────────────────────────────────────────

def test_auth_disabled_opens_the_channels_exactly_as_require_tier_does(monkeypatch):
    """Local dev / CI parity — the same escape hatch, not a wider one."""
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", False)
    flask_app = Flask(__name__)
    with flask_app.test_request_context("/"):
        assert printer_read_denial(None) is None
        assert telemetry_read_denial(PRIVATE_SLUG, None) is None
