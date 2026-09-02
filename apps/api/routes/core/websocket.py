"""
WebSocket Blueprint — real-time channels alongside the existing SSE endpoints.

- /api/ws/render/<session_id>    — render control channel (ping/pong; `cancel` refused)
- /api/ws/printer/<printer_id>   — read-only printer status broadcast
- /api/ws/telemetry/<slug>       — read-only MQTT→WS telemetry broadcast

Auth posture (mirrored in docs/AUTH.md § WebSocket channels):

  * Every channel resolves an identity on the upgrade
    (`middleware.auth.resolve_ws_claims`) and then decides, per channel, what
    that identity may READ. A socket is not a lesser door: an anonymous reader
    gets exactly what an anonymous HTTP caller gets and nothing more.
  * Nothing on a WebSocket may MUTATE server state. The `cancel` action used to
    call the orchestrator's cancel-everything helper with no identity check at
    all; it is now always refused (see `cancel_refusal_reason`), and the helper
    is deliberately not imported in this module.
  * `@require_auth` / `@optional_auth` / `@require_tier` cannot decorate these
    handlers: all may return a Flask response (a 401/403 body), which is
    meaningless once the socket has been upgraded. `resolve_ws_claims()` is the
    WS-shaped identity resolver, and the `*_read_denial` helpers below are the
    WS-shaped gates — each returns a reason, never a response.

Read authorisation, and why each channel has the gate it has:

  * render     — anonymous. It answers `ping` with `pong` and refuses `cancel`
                 to everyone, so it discloses nothing an anonymous HTTP caller
                 could not already learn from `GET /api/health`.
  * printer    — `pro` tier, mirroring `GET /api/printers/<id>/status`
                 (`@require_tier("pro")` in routes/integrations/printer.py).
                 The socket forwards the same shop-floor status that route
                 proxies, so leaving it open was a straight tier bypass: connect
                 to the socket instead of calling the route and the gate is
                 gone.
  * telemetry  — authenticated, plus the private-project gate. MQTT sensor
                 streams are not "public project status": they are live
                 shop-floor data for one project, and for a private cartridge
                 they are exactly the events `PRIVATE_PROJECTS` exists to
                 withhold. There is no anonymous HTTP surface that serves them,
                 so there is no anonymous WS surface either.

Anonymous gained nothing here; two channels lost what they should never have
had. A refused connection is answered with one `{"type": "error", ...}` frame
naming the reason, then closed — the socket never sees a payload it may not
read.

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

from config import Config
from middleware.auth import is_machine_token, machine_client_id, resolve_ws_claims
from services.core.project_access import project_view_denied_reason
from services.core.tier_service import has_tier, resolve_tier
from utils.validators import validate_project_slug

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
# Read authorisation
# ──────────────────────────────────────────────
#
# One shape for every channel gate: `(reason, message)` when the caller may not
# read this channel, `None` when it may. A reason — never a response — because
# the connection is already upgraded by the time these run; `_refuse` turns one
# into the single frame the client sees before the socket closes.
#
# `Config.AUTH_ENABLED` off short-circuits to "allowed", exactly as
# `@require_tier` and `@require_auth` do on the HTTP routes. That keeps local
# development and the test suite (conftest sets AUTH_ENABLED=False) behaving as
# they do for the equivalent HTTP endpoint, and it is the same escape hatch —
# not a wider one.

#: Mirrors `@require_tier("pro")` on `GET /api/printers/<id>/status`. The socket
#: forwards the same status that route proxies, so the two gates must agree; if
#: the HTTP tier ever moves, move this with it.
PRINTER_MIN_TIER = "pro"

WS_UNAUTHORISED = "read not permitted"


def _refuse(ws, reason: str, message: str) -> None:
    """Send the one refusal frame a denied reader gets, then let the caller close."""
    _send(ws, {
        "type": "error",
        "error": WS_UNAUTHORISED,
        "reason": reason,
        "message": message,
    })


def printer_read_denial(claims: dict | None) -> tuple[str, str] | None:
    """Why this caller may not read the printer status channel, or None.

    The gate is the tier gate on `GET /api/printers/<id>/status`, not a new
    policy: printer status is `pro`, and reading it over a socket instead of
    over HTTP must not be the cheaper door. Anonymous resolves to the guest
    tier, so it is refused by the same comparison rather than by a special case
    — but it gets the reason that tells the Studio to offer sign-in rather than
    an upgrade, mirroring `auth_required` on the private-project refusal.
    """
    if not Config.AUTH_ENABLED:
        return None
    if has_tier(resolve_tier(claims), PRINTER_MIN_TIER):
        return None
    if not claims:
        return (
            "authentication_required",
            (
                "Printer status requires a signed-in Pro identity. "
                "Present a bearer token on the upgrade request "
                "(Authorization header, or ?token= from a browser)."
            ),
        )
    return (
        "insufficient_tier",
        f"Printer status requires {PRINTER_MIN_TIER} tier or above.",
    )


def telemetry_read_denial(project_slug: str, claims: dict | None) -> tuple[str, str] | None:
    """Why this caller may not read `project_slug`'s telemetry stream, or None.

    Two gates, in order:

      1. an identity. Telemetry is live shop-floor sensor data for one project.
         No HTTP route serves it anonymously — no route serves it at all — so
         there is nothing an anonymous caller could already read here, and
         "read-only" is not on its own a reason to publish it.
      2. the private-project gate, reusing the very check the HTTP routes use
         (`services.core.project_access`). A private cartridge's telemetry is
         precisely the class of event `PRIVATE_PROJECTS` exists to withhold, and
         a second implementation of "may this identity see this slug?" is how
         the two answers drift apart.

    The slug is attacker-chosen path input, so it is validated before it reaches
    the manifest lookup — same as `@require_valid_slug` on the HTTP routes.
    """
    if not Config.AUTH_ENABLED:
        return None

    if validate_project_slug(project_slug) is not None:
        return ("invalid_project", "Invalid project slug.")

    if not claims:
        return (
            "authentication_required",
            (
                "Project telemetry requires a signed-in identity. Present a "
                "bearer token on the upgrade request (Authorization header, "
                "or ?token= from a browser)."
            ),
        )

    denied = project_view_denied_reason(project_slug, claims)
    if denied is not None:
        return (denied, "This project is private.")
    return None


def _deny(ws, channel: str, subject: str, claims: dict | None,
          denial: tuple[str, str] | None) -> bool:
    """Refuse and log when `denial` is set. True when the connection was refused.

    Logged at WARNING with the coarse identity label only: never the token,
    never the caller's `sub`.
    """
    if denial is None:
        return False
    reason, message = denial
    logger.warning(
        "WS %s read refused (subject=%s identity=%s reason=%s ip=%s)",
        channel, subject, _identity_label(claims), reason, request.remote_addr,
    )
    _refuse(ws, reason, message)
    return True


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
    """Live printer status WebSocket. READ-ONLY, `pro` tier and above.

    Read-only is not the same as public. This forwards the shop-floor status
    that `GET /api/printers/<printer_id>/status` proxies, and that route is
    `@require_tier("pro")` — so an ungated socket was a tier bypass with a
    different scheme, not a harmless dashboard feed. `printer_read_denial`
    holds the gate and mirrors that route's tier.

    The only client frame understood is `ping`; no action mutates server state,
    starts or stops a print, or reaches a printer. Any future action that writes
    anything needs its own check on top of this one — this gate authorises
    *reading*.

    Server → Client: {"type": "heartbeat", ...} | {"type": "pong", ...}
    """
    claims = resolve_ws_claims()
    logger.info(
        "WS printer connection: printer=%s identity=%s",
        printer_id, _identity_label(claims),
    )
    if _deny(ws, "printer", printer_id, claims, printer_read_denial(claims)):
        return

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
    """MQTT → WebSocket bridge for project telemetry. READ-ONLY, signed-in only.

    Forwards MQTT messages from yantra4d/{slug}/telemetry/# to WebSocket
    clients. `ping` is the only client frame understood and no action mutates
    server state — but a live sensor stream for one project is not public
    project status, and for a private cartridge it is exactly what the
    private-project gate exists to withhold. `telemetry_read_denial` requires an
    identity and then reuses that gate.

    Server → Client: {"type": "telemetry", "topic": "...", "payload": {...}}
    """
    claims = resolve_ws_claims()
    logger.info(
        "WS telemetry connection: project=%s identity=%s",
        project_slug, _identity_label(claims),
    )
    if _deny(ws, "telemetry", project_slug, claims,
             telemetry_read_denial(project_slug, claims)):
        return

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
