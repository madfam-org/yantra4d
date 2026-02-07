"""
AI Chat Blueprint — session creation and SSE streaming chat.
"""
import json
import logging

from flask import Blueprint, request, jsonify, Response

from config import Config
from extensions import limiter
import rate_limits
from middleware.auth import require_tier
from services.route_helpers import error_response, require_json_body
from services.tier_service import resolve_tier, get_tier_limits
from services.ai_session import create_session, get_session
from services.ai_configurator import stream_response as stream_configurator
from services.ai_code_editor import stream_response as stream_code_editor

logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__)


def _get_ai_rate_limit() -> str:
    """Dynamic rate limit based on user tier's ai_requests_per_hour."""
    claims = getattr(request, "auth_claims", None)
    tier = resolve_tier(claims)
    limits = get_tier_limits(tier)
    return f"{limits.get('ai_requests_per_hour', 0)}/hour"


@ai_bp.route("/api/ai/session", methods=["POST"])
@require_tier("basic")
@limiter.limit(rate_limits.AI_SESSION)
@require_json_body
def create_ai_session():
    """Create a new AI chat session."""
    if not Config.AI_API_KEY:
        return error_response("AI features are not configured", 503)

    data = request.json
    project_slug = data.get("project")
    mode = data.get("mode")

    if not project_slug or mode not in ("configurator", "code-editor"):
        return error_response("project and mode (configurator|code-editor) are required", 400)

    # Code editor requires pro+
    if mode == "code-editor":
        user_tier = getattr(request, "user_tier", "guest")
        limits = get_tier_limits(user_tier)
        if not limits.get("ai_code_editor"):
            return error_response("AI Code Editor requires pro tier or above", 403)

    session_id = create_session(project_slug, mode)
    return jsonify({"session_id": session_id})


@ai_bp.route("/api/ai/chat-stream", methods=["POST"])
@require_tier("basic")
@limiter.limit(_get_ai_rate_limit)
@require_json_body
def chat_stream():
    """SSE streaming chat endpoint. Dispatches to configurator or code-editor."""
    if not Config.AI_API_KEY:
        return error_response("AI features are not configured", 503)

    data = request.json
    session_id = data.get("session_id")
    message = data.get("message", "").strip()

    if not session_id or not message:
        return error_response("session_id and message are required", 400)
    if len(message) > 5000:
        return error_response("Message must be 5000 characters or less", 400)

    session = get_session(session_id)
    if not session:
        return error_response("Session not found or expired", 404)

    # Code editor requires pro+
    if session["mode"] == "code-editor":
        user_tier = getattr(request, "user_tier", "guest")
        limits = get_tier_limits(user_tier)
        if not limits.get("ai_code_editor"):
            return error_response("AI Code Editor requires pro tier or above", 403)

    # Load manifest for context
    from manifest import get_manifest
    try:
        manifest_obj = get_manifest(session["project_slug"])
        manifest = manifest_obj.as_json()
    except Exception:
        return error_response("Project manifest not found", 404)

    def generate():
        try:
            if session["mode"] == "configurator":
                current_params = data.get("current_params") or {}
                events = stream_configurator(session_id, message, manifest, current_params)
            else:
                file_contents = data.get("file_contents") or {}
                events = stream_code_editor(session_id, message, manifest, file_contents)

            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error("AI stream error: %s", e)
            yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")
