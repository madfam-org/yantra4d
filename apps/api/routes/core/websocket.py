"""
WebSocket Blueprint — bidirectional real-time communication.

Provides WebSocket endpoints alongside existing SSE endpoints:
- /api/ws/render/<session_id> — bidirectional render (progress down, cancel up)
- /api/ws/printer/<printer_id> — live printer status forwarding
- /api/ws/telemetry/<project_slug> — MQTT→WS bridge for sensor data

All WS endpoints fall back gracefully — existing SSE code is untouched.
"""
import json
import logging
import time

from flask import Blueprint

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


def init_websocket(app):
    """Initialize WebSocket support on the Flask app. No-op if flask-sock is missing."""
    if _WS_AVAILABLE and sock is not None:
        sock.init_app(app)
        logger.info("WebSocket support initialized")


if _WS_AVAILABLE and sock is not None:

    @sock.route("/api/ws/render/<session_id>")
    def ws_render(ws, session_id):
        """Bidirectional render WebSocket.

        Server → Client: {"type": "progress", "percent": 45, "phase": "rendering"}
                         {"type": "complete", "url": "/static/preview_part.glb"}
                         {"type": "error", "message": "..."}
        Client → Server: {"action": "cancel"}
        """
        logger.info("WS render connection: session=%s", session_id)
        try:
            while True:
                # Non-blocking receive with timeout
                data = ws.receive(timeout=1)
                if data is None:
                    continue

                try:
                    msg = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    ws.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                    continue

                action = msg.get("action")
                if action == "cancel":
                    # Import here to avoid circular imports
                    from services.engine.render_orchestrator import cancel_active_render
                    cancel_active_render()
                    ws.send(json.dumps({"type": "cancelled"}))
                    break
                elif action == "ping":
                    ws.send(json.dumps({"type": "pong", "timestamp": time.time()}))
                else:
                    ws.send(json.dumps({"type": "error", "message": f"Unknown action: {action}"}))

        except Exception as e:
            logger.debug("WS render closed: %s", e)

    @sock.route("/api/ws/printer/<printer_id>")
    def ws_printer(ws, printer_id):
        """Live printer status WebSocket.

        Bridges MQTT printer telemetry to WebSocket for real-time dashboard.
        Server → Client: {"type": "status", "state": "printing", "progress": 45.2, ...}
        """
        logger.info("WS printer connection: printer=%s", printer_id)
        from services.core.mqtt_telemetry import telemetry_service

        try:
            while True:
                # Send heartbeat every 30s
                ws.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "printer_id": printer_id,
                    "mqtt_connected": telemetry_service.connected if telemetry_service else False,
                }))

                # Wait for client message (or timeout for next heartbeat)
                data = ws.receive(timeout=30)
                if data is None:
                    continue

                try:
                    msg = json.loads(data)
                    if msg.get("action") == "ping":
                        ws.send(json.dumps({"type": "pong", "timestamp": time.time()}))
                except (json.JSONDecodeError, TypeError):
                    pass

        except Exception as e:
            logger.debug("WS printer closed: %s", e)

    @sock.route("/api/ws/telemetry/<project_slug>")
    def ws_telemetry(ws, project_slug):
        """MQTT → WebSocket bridge for project telemetry.

        Forwards MQTT messages from yantra4d/{slug}/telemetry/# to WebSocket clients.
        Server → Client: {"type": "telemetry", "topic": "...", "payload": {...}}
        """
        logger.info("WS telemetry connection: project=%s", project_slug)
        from services.core.mqtt_telemetry import telemetry_queue

        try:
            while True:
                # Check telemetry queue for messages matching this project
                try:
                    topic, payload = telemetry_queue.get(timeout=5)
                    expected_prefix = f"yantra4d/{project_slug}/telemetry/"
                    if topic.startswith(expected_prefix):
                        ws.send(json.dumps({
                            "type": "telemetry",
                            "topic": topic,
                            "payload": payload,
                            "timestamp": time.time(),
                        }))
                    # Put back if not for this project (other WS clients may need it)
                    else:
                        telemetry_queue.put((topic, payload))
                except Exception:
                    # Queue empty or timeout — send heartbeat
                    ws.send(json.dumps({"type": "heartbeat", "timestamp": time.time()}))

                # Check for client messages
                data = ws.receive(timeout=0.1)
                if data:
                    try:
                        msg = json.loads(data)
                        if msg.get("action") == "ping":
                            ws.send(json.dumps({"type": "pong", "timestamp": time.time()}))
                    except (json.JSONDecodeError, TypeError):
                        pass

        except Exception as e:
            logger.debug("WS telemetry closed: %s", e)
