"""
WebSocket Blueprint — real-time channels alongside the existing SSE endpoints.

- /api/ws/render/<session_id>    — render control channel (ping/pong; `cancel` refused)
- /api/ws/printer/<printer_id>   — read-only printer status broadcast
- /api/ws/telemetry/<slug>       — read-only MQTT→WS telemetry broadcast

Auth posture (mirrored in docs/AUTH.md § WebSocket channels):

  * These channels are anonymous-readable by design. They carry no private
    per-user data: the render channel only answers ping/pong, and the printer
    and telemetry channels are one-way broadcasts of shop-floor status.
  * Nothing on a WebSocket may MUTATE server state. The `cancel` action used to
    call the orchestrator's cancel-everything helper with no identity check at
    all; it is now always refused (see `cancel_refusal_reason`), and the helper
    is deliberately not imported in this module.
  * `@require_auth` / `@optional_auth` cannot decorate these handlers: both may
    return a Flask response (a 401 body), which is meaningless once the socket
    has been upgraded. `middleware.auth.resolve_ws_claims()` is the WS-shaped
    equivalent — it resolves an identity and never returns a response.

All WS endpoints fall back gracefully — existing SSE code is untouched.
"""
import json
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import contextmanager

from flask import Blueprint, request

from middleware.auth import is_machine_token, machine_client_id, resolve_ws_claims

logger = logging.getLogger(__name__)

ws_bp = Blueprint("websocket", __name__)

try:
    from flask_sock import Sock
    sock = Sock()
    _WS_AVAILABLE = True
except ImportError:
    sock = None
    _WS_AVAILABLE = False
    logger.info("flask-sock not installed; WebSocket endpoints disabled")


# ──────────────────────────────────────────────
# Connection and message limits
# ──────────────────────────────────────────────
#
# flask-limiter cannot guard these routes. It decorates request/response views
# and counts one hit per request; a flask-sock handler is a single "request"
# that lives for the whole life of the socket, so a limiter decorator would see
# one hit at connect and nothing for the thousands of frames that follow. The
# two guards below cover what it cannot: a per-IP concurrent connection cap and
# a per-connection inbound message budget.
#
# Both are in-process. That is sufficient here — the backend runs a single
# replica (k8s/production/yantra4d-backend-deployment.yaml) — but the counters
# are per-replica, so they must never be the only thing standing between a
# caller and a privileged action. They are not: the render channel performs no
# privileged action at all.

WS_MAX_CONNECTIONS_PER_IP = int(os.getenv("WS_MAX_CONNECTIONS_PER_IP", "8"))
WS_MAX_MESSAGES_PER_MINUTE = int(os.getenv("WS_MAX_MESSAGES_PER_MINUTE", "120"))
WS_RATE_WINDOW_SECONDS = 60.0

_connection_counts: dict[str, int] = defaultdict(int)
_connection_lock = threading.Lock()


class MessageBudget:
    """Fixed-window inbound message allowance for one connection.

    The limit is read at construction from the module global so tests (and a
    redeploy with a different env value) can change it without reimporting.
    """

    def __init__(self, limit: int | None = None, window: float | None = None):
        self.limit = WS_MAX_MESSAGES_PER_MINUTE if limit is None else limit
        self.window = WS_RATE_WINDOW_SECONDS if window is None else window
        self._window_start = time.monotonic()
        self._count = 0

    def allow(self) -> bool:
        """Count one inbound message; False once the window's budget is spent."""
        now = time.monotonic()
        if now - self._window_start >= self.window:
            self._window_start = now
            self._count = 0
        self._count += 1
        return self._count <= self.limit


@contextmanager
def connection_slot(channel: str):
    """Reserve a per-IP connection slot. Yields False when the cap is reached."""
    remote = request.remote_addr or "unknown"
    key = f"{channel}:{remote}"
    with _connection_lock:
        current = _connection_counts[key]
        if current >= WS_MAX_CONNECTIONS_PER_IP:
            logger.warning(
                "WS connection cap reached (channel=%s ip=%s cap=%d)",
                channel, remote, WS_MAX_CONNECTIONS_PER_IP,
            )
            yield False
            return
        _connection_counts[key] = current + 1
    try:
        yield True
    finally:
        with _connection_lock:
            remaining = _connection_counts.get(key, 1) - 1
            if remaining <= 0:
                _connection_counts.pop(key, None)
            else:
                _connection_counts[key] = remaining


def _send(ws, payload: dict) -> None:
    """Serialize and send one frame. Send errors propagate and close the loop."""
    ws.send(json.dumps(payload))


def _identity_label(claims: dict | None) -> str:
    """Coarse identity for logs. Never the token, never a user's `sub`."""
    if not claims:
        return "anonymous"
    if is_machine_token(claims):
        return f"machine:{machine_client_id(claims)}"
    return "human"


# ──────────────────────────────────────────────
# Render channel
# ──────────────────────────────────────────────

CANCEL_REFUSAL = "cancel not permitted"


def cancel_refusal_reason(claims: dict | None) -> str:
    """Why a `cancel` over the render channel is refused for this caller.

    It is refused for *every* caller, and the reason is the honest one:

      anonymous     -> "authentication_required"
      authenticated -> "render_owner_unknown"

    Renders carry no owner. `apps/worker/render_worker.py::_set_active_job`
    records job_id/part/engine/project/mode/request_id and nothing that
    identifies the caller, the active-job set is global, and the job_id is
    never published to the client — so this channel cannot determine which
    renders belong to the connected caller. The only cancel it could perform
    is "cancel everything, for everyone", which is precisely the blast radius
    being removed. `POST /api/render-cancel` remains the supported cancel path.

    If per-owner render tracking is added later, this is the single place to
    relax, and a scoped cancel must (a) act only on the caller's own jobs and
    (b) require the `yantra4d:render` scope on machine tokens, matching
    `middleware.auth.require_render_scope` on the HTTP render routes.
    """
    return "authentication_required" if not claims else "render_owner_unknown"


def handle_render_message(msg: object, claims: dict | None) -> dict:
    """Map one decoded client frame to the reply frame. Pure apart from logging."""
    action = msg.get("action") if isinstance(msg, dict) else None

    if action == "cancel":
        reason = cancel_refusal_reason(claims)
        logger.warning(
            "WS render cancel refused (identity=%s reason=%s ip=%s)",
            _identity_label(claims), reason, request.remote_addr,
        )
        return {
            "type": "error",
            "error": CANCEL_REFUSAL,
            "reason": reason,
            "message": "Cancel is not available on this channel. Use POST /api/render-cancel.",
        }

    if action == "ping":
        return {"type": "pong", "timestamp": time.time()}

    # The action is echoed back nowhere: it is attacker-controlled text.
    return {"type": "error", "message": "Unknown action"}


def ws_render(ws, session_id):
    """Render control channel.

    Server → Client: {"type": "pong", ...} | {"type": "error", ...}
    Client → Server: {"action": "ping"} | {"action": "cancel"} (always refused)

    `session_id` is an opaque, client-chosen label kept for log correlation. It
    is NOT an authorisation subject — it is unauthenticated and attacker-chosen,
    so no capability may be granted on the strength of it.
    """
    claims = resolve_ws_claims()
    logger.info(
        "WS render connection: session=%s identity=%s",
        session_id, _identity_label(claims),
    )
    budget = MessageBudget()

    with connection_slot("render") as admitted:
        if not admitted:
            _send(ws, {"type": "error", "message": "Too many connections"})
            return

        try:
            while True:
                # Non-blocking receive with timeout
                data = ws.receive(timeout=1)
                if data is None:
                    continue

                if not budget.allow():
                    logger.warning(
                        "WS render message rate limit exceeded (ip=%s limit=%d)",
                        request.remote_addr, budget.limit,
                    )
                    _send(ws, {"type": "error", "message": "Message rate limit exceeded"})
                    break

                try:
                    msg = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    _send(ws, {"type": "error", "message": "Invalid JSON"})
                    continue

                _send(ws, handle_render_message(msg, claims))

        except Exception as e:
            logger.debug("WS render closed: %s", e)


# ──────────────────────────────────────────────
# Printer channel
# ──────────────────────────────────────────────

def ws_printer(ws, printer_id):
    """Live printer status WebSocket.

    READ-ONLY BROADCAST. The only client frame this understands is `ping`;
    there is no action that mutates server state, starts or stops a print, or
    reaches a printer. It therefore stays anonymous-readable like the SSE
    dashboards it feeds — the auth gate added to the render channel exists
    because that channel had a mutating action, and this one has none. Any
    future action that writes anything must resolve an identity first
    (`middleware.auth.resolve_ws_claims`) rather than inheriting this comment.

    Server → Client: {"type": "heartbeat", ...} | {"type": "pong", ...}
    """
    logger.info("WS printer connection: printer=%s", printer_id)
    from services.core.mqtt_telemetry import telemetry_service

    budget = MessageBudget()

    with connection_slot("printer") as admitted:
        if not admitted:
            _send(ws, {"type": "error", "message": "Too many connections"})
            return

        try:
            while True:
                # Send heartbeat every 30s
                _send(ws, {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "printer_id": printer_id,
                    "mqtt_connected": telemetry_service.connected if telemetry_service else False,
                })

                # Wait for client message (or timeout for next heartbeat)
                data = ws.receive(timeout=30)
                if data is None:
                    continue

                if not budget.allow():
                    logger.warning(
                        "WS printer message rate limit exceeded (ip=%s limit=%d)",
                        request.remote_addr, budget.limit,
                    )
                    _send(ws, {"type": "error", "message": "Message rate limit exceeded"})
                    break

                try:
                    msg = json.loads(data)
                    if isinstance(msg, dict) and msg.get("action") == "ping":
                        _send(ws, {"type": "pong", "timestamp": time.time()})
                except (json.JSONDecodeError, TypeError):
                    pass

        except Exception as e:
            logger.debug("WS printer closed: %s", e)


# ──────────────────────────────────────────────
# Telemetry channel
# ──────────────────────────────────────────────

def ws_telemetry(ws, project_slug):
    """MQTT → WebSocket bridge for project telemetry.

    READ-ONLY BROADCAST. Like the printer channel, `ping` is the only client
    frame it understands and no action mutates server state, so it keeps its
    existing anonymous-readable posture. Forwards MQTT messages from
    yantra4d/{slug}/telemetry/# to WebSocket clients.

    Server → Client: {"type": "telemetry", "topic": "...", "payload": {...}}
    """
    logger.info("WS telemetry connection: project=%s", project_slug)
    from services.core.mqtt_telemetry import telemetry_queue

    budget = MessageBudget()

    with connection_slot("telemetry") as admitted:
        if not admitted:
            _send(ws, {"type": "error", "message": "Too many connections"})
            return

        try:
            while True:
                # Check telemetry queue for messages matching this project.
                # The producer (mqtt_telemetry) enqueues dicts: {"topic": ..., "payload": ...}
                try:
                    message = telemetry_queue.get(timeout=5)
                    topic = message["topic"]
                    payload = message["payload"]
                    expected_prefix = f"yantra4d/{project_slug}/telemetry/"
                    if topic.startswith(expected_prefix):
                        _send(ws, {
                            "type": "telemetry",
                            "topic": topic,
                            "payload": payload,
                            "timestamp": time.time(),
                        })
                    # Put back if not for this project (other WS clients may need it)
                    else:
                        telemetry_queue.put(message)
                except Exception:
                    # Queue empty or timeout — send heartbeat
                    _send(ws, {"type": "heartbeat", "timestamp": time.time()})

                # Check for client messages
                data = ws.receive(timeout=0.1)
                if data:
                    if not budget.allow():
                        logger.warning(
                            "WS telemetry message rate limit exceeded (ip=%s limit=%d)",
                            request.remote_addr, budget.limit,
                        )
                        _send(ws, {"type": "error", "message": "Message rate limit exceeded"})
                        break
                    try:
                        msg = json.loads(data)
                        if isinstance(msg, dict) and msg.get("action") == "ping":
                            _send(ws, {"type": "pong", "timestamp": time.time()})
                    except (json.JSONDecodeError, TypeError):
                        pass

        except Exception as e:
            logger.debug("WS telemetry closed: %s", e)


# Handlers are defined unconditionally (and stay importable for tests);
# only the route registration depends on flask-sock being installed.
# `Sock.route` returns None, so it is applied as a statement, not a decorator —
# binding its result would replace each handler with None.
if _WS_AVAILABLE and sock is not None:
    sock.route("/api/ws/render/<session_id>")(ws_render)
    sock.route("/api/ws/printer/<printer_id>")(ws_printer)
    sock.route("/api/ws/telemetry/<project_slug>")(ws_telemetry)


def init_websocket(app):
    """Initialize WebSocket support on the Flask app. No-op if flask-sock is missing."""
    if _WS_AVAILABLE and sock is not None:
        sock.init_app(app)
        logger.info("WebSocket support initialized")
