"""
Analytics Blueprint
Privacy-respecting aggregate analytics: render counts, preset usage, export counts.
Uses SQLAlchemy (PostgreSQL in production, SQLite fallback in development).
"""
import json
import logging
import time

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import func

from extensions import db
from models.analytics import AnalyticsEvent
from utils.route_helpers import error_response
from utils.validators import require_valid_slug

analytics_bp = Blueprint("analytics", __name__)
logger = logging.getLogger(__name__)


@analytics_bp.route("/api/analytics/track", methods=["POST"])
def track_event() -> tuple[Response, int]:
    """Record an analytics event. No PII collected."""
    data = request.get_json(silent=True) or {}
    project = data.get("project", "unknown")
    event_type = data.get("event")
    event_data = data.get("data")

    if not event_type:
        return error_response("Missing event type", 400, error_code="missing_event_type")

    allowed_events = {"render", "export", "preset_apply", "mode_switch", "share", "verify"}
    if event_type not in allowed_events:
        return error_response(f"Unknown event type: {event_type}", 400, error_code="unknown_event_type")

    # Sanitize event_data: whitelist known keys, limit size
    ALLOWED_DATA_KEYS = {"mode", "preset", "format", "parts", "project", "duration_ms", "params"}
    if event_data:
        if not isinstance(event_data, dict):
            return error_response("event data must be an object", 400, error_code="invalid_event_data")
        event_data = {k: v for k, v in event_data.items() if k in ALLOWED_DATA_KEYS}
        # Ensure string values are bounded
        for k, v in event_data.items():
            if isinstance(v, str) and len(v) > 200:
                event_data[k] = v[:200]

    event = AnalyticsEvent(
        project=project,
        event_type=event_type,
        event_data=json.dumps(event_data) if event_data else None,
        created_at=time.time(),
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({"ok": True}), 201


@analytics_bp.route("/api/analytics/<slug>/summary", methods=["GET"])
@require_valid_slug
def get_summary(slug: str) -> Response:
    """Return aggregate analytics for a project."""
    days = int(request.args.get("days", 30))
    since = time.time() - (days * 86400)

    # Event counts by type
    count_rows = (
        db.session.query(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.project == slug, AnalyticsEvent.created_at > since)
        .group_by(AnalyticsEvent.event_type)
        .all()
    )
    counts = {row[0]: row[1] for row in count_rows}

    # Mode distribution (extract from JSON event_data)
    # Use database-agnostic approach: fetch render events and parse in Python
    render_events = (
        db.session.query(AnalyticsEvent.event_data)
        .filter(
            AnalyticsEvent.project == slug,
            AnalyticsEvent.event_type == "render",
            AnalyticsEvent.created_at > since,
            AnalyticsEvent.event_data.isnot(None),
        )
        .all()
    )
    mode_counts: dict[str, int] = {}
    for (raw,) in render_events:
        try:
            parsed = json.loads(raw) if raw else {}
            mode = parsed.get("mode")
            if mode:
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    # Daily render counts — database-agnostic date extraction
    daily_rows = (
        db.session.query(AnalyticsEvent.created_at)
        .filter(
            AnalyticsEvent.project == slug,
            AnalyticsEvent.event_type == "render",
            AnalyticsEvent.created_at > since,
        )
        .all()
    )
    daily_counts: dict[str, int] = {}
    for (ts,) in daily_rows:
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        daily_counts[day] = daily_counts.get(day, 0) + 1
    daily = sorted(
        [{"date": d, "renders": c} for d, c in daily_counts.items()],
        key=lambda x: x["date"],
    )

    return jsonify({
        "project": slug,
        "period_days": days,
        "event_counts": counts,
        "mode_distribution": mode_counts,
        "daily_renders": daily,
    })
