"""Auth and blast-radius tests for the WebSocket render channel.

Before this fix `/api/ws/render/<session_id>` was registered with no auth
decorator, no scope check and no rate limit, and its `cancel` action called
`render_orchestrator.cancel_active_render()` — a straight alias for
`cancel_all_renders()`. Any anonymous client could therefore terminate every
in-flight render for every user on the single backend replica.

These tests pin the four invariants the fix rests on:

  1. An anonymous `cancel` cancels nothing and is answered with a refusal.
  2. An authenticated `cancel` is refused too — but for the honest reason:
     renders carry no owner, so this channel cannot scope a cancel.
  3. The read-only path (anonymous connect + ping/pong) still works.
  4. No cancel-everything helper is reachable from the WebSocket module.
"""
import json
from unittest.mock import patch

import pytest
from flask import Flask

from routes.core import websocket as ws_mod
from routes.core.websocket import (
    CANCEL_REFUSAL,
    MessageBudget,
    cancel_refusal_reason,
    connection_slot,
    handle_render_message,
    ws_render,
)

HUMAN_CLAIMS = {"sub": "11111111-2222-3333-4444-555555555555", "yantra4d_tier": "pro"}
MACHINE_CLAIMS = {
    "sub": "service-account:fashion-cabinet",
    "token_use": "client_credentials",
    "actor_type": "service_account",
    "client_id": "fashion-cabinet",
    "scope": "yantra4d:render",
}


class FakeWS:
    """Scripted stand-in for a simple_websocket Server connection."""

    def __init__(self, inbound):
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


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.fixture(autouse=True)
def _reset_connection_counts():
    ws_mod._connection_counts.clear()
    yield
    ws_mod._connection_counts.clear()


@pytest.fixture
def no_cancel_calls():
    """Fail loudly if the WS path reaches any orchestrator cancel helper."""
    import services.engine.render_orchestrator as orch

    def _boom(*args, **kwargs):
        raise AssertionError("WebSocket path must never cancel renders")

    with patch.object(orch, "cancel_all_renders", side_effect=_boom) as cancel_all, \
            patch.object(orch, "_cancel_by_engine", side_effect=_boom):
        yield cancel_all


# ──────────────────────────────────────────────
# 1. Anonymous cancel cancels nothing
# ──────────────────────────────────────────────

def test_anonymous_cancel_is_refused_and_cancels_nothing(app, no_cancel_calls):
    ws = FakeWS([json.dumps({"action": "cancel"})])

    with app.test_request_context("/api/ws/render/anything"):
        ws_render(ws, "anything")

    assert ws.replies() == [{
        "type": "error",
        "error": CANCEL_REFUSAL,
        "reason": "authentication_required",
        "message": "Cancel is not available on this channel. Use POST /api/render-cancel.",
    }]
    no_cancel_calls.assert_not_called()


def test_anonymous_cancel_logs_a_warning(app, caplog):
    with app.test_request_context("/api/ws/render/anything"), \
            caplog.at_level("WARNING", logger="routes.core.websocket"):
        reply = handle_render_message({"action": "cancel"}, None)

    assert reply["error"] == CANCEL_REFUSAL
    assert any(
        "cancel refused" in rec.getMessage() and "identity=anonymous" in rec.getMessage()
        for rec in caplog.records
    )


# ──────────────────────────────────────────────
# 2. Authenticated cancel: refused, honestly
# ──────────────────────────────────────────────

@pytest.mark.parametrize("claims", [HUMAN_CLAIMS, MACHINE_CLAIMS])
def test_authenticated_cancel_is_refused_because_renders_have_no_owner(app, claims):
    with app.test_request_context("/api/ws/render/s1"):
        reply = handle_render_message({"action": "cancel"}, claims)

    assert reply["error"] == CANCEL_REFUSAL
    assert reply["reason"] == "render_owner_unknown"
    assert "/api/render-cancel" in reply["message"]


def test_cancel_refusal_reason_distinguishes_anonymous_from_authenticated():
    assert cancel_refusal_reason(None) == "authentication_required"
    assert cancel_refusal_reason({}) == "authentication_required"
    assert cancel_refusal_reason(HUMAN_CLAIMS) == "render_owner_unknown"


def test_authenticated_cancel_over_the_socket_cancels_nothing(app, monkeypatch, no_cancel_calls):
    """End-to-end through the handler with a valid bearer on the upgrade request."""
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr("middleware.auth.decode_token", lambda token: HUMAN_CLAIMS)
    monkeypatch.setattr("middleware.auth._sync_user_from_claims", lambda claims: None)

    ws = FakeWS([json.dumps({"action": "cancel"})])
    with app.test_request_context(
        "/api/ws/render/s1", headers={"Authorization": "Bearer good-token"}
    ):
        ws_render(ws, "s1")

    assert ws.replies()[0]["reason"] == "render_owner_unknown"
    no_cancel_calls.assert_not_called()


def test_machine_token_identity_is_labelled_without_leaking_the_subject(app, caplog):
    with app.test_request_context("/api/ws/render/s1"), \
            caplog.at_level("WARNING", logger="routes.core.websocket"):
        handle_render_message({"action": "cancel"}, MACHINE_CLAIMS)

    messages = " ".join(rec.getMessage() for rec in caplog.records)
    assert "identity=machine:fashion-cabinet" in messages
    assert HUMAN_CLAIMS["sub"] not in messages


# ──────────────────────────────────────────────
# 3. Read-only path still open to anonymous callers
# ──────────────────────────────────────────────

def test_anonymous_connection_is_accepted_and_ping_still_works(app):
    ws = FakeWS([json.dumps({"action": "ping"}), json.dumps({"action": "ping"})])

    with app.test_request_context("/api/ws/render/anon-session"):
        ws_render(ws, "anon-session")

    assert [r["type"] for r in ws.replies()] == ["pong", "pong"]
    assert all("timestamp" in r for r in ws.replies())


def test_invalid_token_degrades_to_anonymous_rather_than_closing(app, monkeypatch):
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)

    def _reject(token):
        raise ValueError("bad signature")

    monkeypatch.setattr("middleware.auth.decode_token", _reject)

    ws = FakeWS([json.dumps({"action": "ping"}), json.dumps({"action": "cancel"})])
    with app.test_request_context("/api/ws/render/s1?token=forged"):
        ws_render(ws, "s1")

    assert ws.replies()[0]["type"] == "pong"
    assert ws.replies()[1]["reason"] == "authentication_required"


def test_malformed_and_unknown_frames_do_not_echo_client_input(app):
    ws = FakeWS(["not json", json.dumps({"action": "<script>"}), json.dumps([1, 2, 3])])

    with app.test_request_context("/api/ws/render/s1"):
        ws_render(ws, "s1")

    assert [r["message"] for r in ws.replies()] == [
        "Invalid JSON", "Unknown action", "Unknown action",
    ]


# ──────────────────────────────────────────────
# 4. Cancel-everything is unreachable from the WS module
# ──────────────────────────────────────────────

def test_websocket_module_does_not_reference_any_cancel_helper():
    from pathlib import Path

    source = Path(ws_mod.__file__).read_text()
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    for banned in ("cancel_all_renders(", "cancel_active_render(", "_cancel_by_engine("):
        assert banned not in code, f"{banned} must not be callable from the WS module"


def test_cancel_active_render_alias_is_gone():
    import services.engine.render_orchestrator as orch

    assert not hasattr(orch, "cancel_active_render"), (
        "the websocket-only cancel-everything alias must stay removed"
    )
    # The HTTP cancel path is untouched.
    assert callable(orch.cancel_all_renders)


# ──────────────────────────────────────────────
# Rate limiting / connection cap
# ──────────────────────────────────────────────

def test_message_budget_allows_up_to_the_limit_then_refuses():
    budget = MessageBudget(limit=3, window=3600)
    assert [budget.allow() for _ in range(5)] == [True, True, True, False, False]


def test_message_budget_resets_after_the_window():
    budget = MessageBudget(limit=1, window=0.0)
    assert budget.allow() is True
    assert budget.allow() is True  # window elapsed, counter reset


def test_render_socket_closes_when_the_message_budget_is_spent(app, monkeypatch):
    monkeypatch.setattr(ws_mod, "WS_MAX_MESSAGES_PER_MINUTE", 2)
    ws = FakeWS([json.dumps({"action": "ping"})] * 5)

    with app.test_request_context("/api/ws/render/s1"):
        ws_render(ws, "s1")

    types = [r["type"] for r in ws.replies()]
    assert types == ["pong", "pong", "error"]
    assert ws.replies()[-1]["message"] == "Message rate limit exceeded"


def test_connection_slot_caps_concurrent_connections_per_ip(app, monkeypatch):
    monkeypatch.setattr(ws_mod, "WS_MAX_CONNECTIONS_PER_IP", 2)

    with app.test_request_context("/api/ws/render/s1", environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        with connection_slot("render") as first, connection_slot("render") as second:
            assert first is True
            assert second is True
            with connection_slot("render") as third:
                assert third is False
        # Slots are released on exit.
        with connection_slot("render") as after:
            assert after is True


def test_connection_cap_is_per_ip_and_per_channel(app, monkeypatch):
    monkeypatch.setattr(ws_mod, "WS_MAX_CONNECTIONS_PER_IP", 1)

    with app.test_request_context("/api/ws/render/s1", environ_base={"REMOTE_ADDR": "10.0.0.1"}), \
            connection_slot("render") as held, \
            connection_slot("telemetry") as other_channel:
        # The cap is 1 per (channel, IP): a second render slot for this IP would
        # be refused, but a different channel for the same IP is unaffected.
        assert held is True
        assert other_channel is True

    with app.test_request_context("/api/ws/render/s1", environ_base={"REMOTE_ADDR": "10.0.0.2"}), \
            connection_slot("render") as other_ip:
        assert other_ip is True


def test_render_socket_rejects_a_connection_over_the_cap(app, monkeypatch):
    monkeypatch.setattr(ws_mod, "WS_MAX_CONNECTIONS_PER_IP", 0)
    ws = FakeWS([json.dumps({"action": "ping"})])

    with app.test_request_context("/api/ws/render/s1"):
        ws_render(ws, "s1")

    assert ws.replies() == [{"type": "error", "message": "Too many connections"}]


# ──────────────────────────────────────────────
# resolve_ws_claims: the WS-shaped auth entry point
# ──────────────────────────────────────────────

@pytest.fixture
def _auth_on(monkeypatch):
    from config import Config

    monkeypatch.setattr(Config, "AUTH_ENABLED", True)
    monkeypatch.setattr("middleware.auth._sync_user_from_claims", lambda claims: None)


def test_resolve_ws_claims_reads_the_authorization_header(app, monkeypatch, _auth_on):
    from middleware.auth import resolve_ws_claims

    seen = {}

    def _decode(token):
        seen["token"] = token
        return HUMAN_CLAIMS

    monkeypatch.setattr("middleware.auth.decode_token", _decode)

    with app.test_request_context(
        "/api/ws/render/s1", headers={"Authorization": "Bearer header-token"}
    ):
        assert resolve_ws_claims() == HUMAN_CLAIMS
    assert seen["token"] == "header-token"


@pytest.mark.parametrize("param", ["token", "access_token"])
def test_resolve_ws_claims_accepts_the_query_parameter_browsers_must_use(
    app, monkeypatch, _auth_on, param
):
    """Browsers cannot set headers on a WebSocket handshake."""
    from middleware.auth import resolve_ws_claims

    monkeypatch.setattr("middleware.auth.decode_token", lambda token: HUMAN_CLAIMS)

    with app.test_request_context(f"/api/ws/render/s1?{param}=query-token"):
        assert resolve_ws_claims() == HUMAN_CLAIMS


def test_resolve_ws_claims_is_anonymous_without_a_token(app, _auth_on):
    from flask import request

    from middleware.auth import resolve_ws_claims

    with app.test_request_context("/api/ws/render/s1"):
        assert resolve_ws_claims() is None
        assert request.auth_claims is None


def test_resolve_ws_claims_never_returns_a_flask_response(app, monkeypatch, _auth_on):
    """A 401 body is meaningless after the upgrade — this must degrade, not respond."""
    from middleware.auth import resolve_ws_claims

    def _reject(token):
        raise ValueError("expired")

    monkeypatch.setattr("middleware.auth.decode_token", _reject)

    with app.test_request_context("/api/ws/render/s1?token=expired"):
        assert resolve_ws_claims() is None


# ──────────────────────────────────────────────
# Route registration
# ──────────────────────────────────────────────

def test_websocket_routes_are_registered_as_websocket_rules():
    from app import create_app

    flask_app = create_app()
    ws_rules = {
        rule.rule for rule in flask_app.url_map.iter_rules()
        if getattr(rule, "websocket", False)
    }
    assert "/api/ws/render/<session_id>" in ws_rules
    assert "/api/ws/printer/<printer_id>" in ws_rules
    assert "/api/ws/telemetry/<project_slug>" in ws_rules
