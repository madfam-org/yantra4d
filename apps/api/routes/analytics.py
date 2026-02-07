"""
Analytics Blueprint
Privacy-respecting aggregate analytics: render counts, preset usage, export counts.
Uses SQLite for zero-dependency storage.
"""
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager

from flask import Blueprint, request, jsonify, Response

from config import Config

analytics_bp = Blueprint("analytics", __name__)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(Config.PROJECTS_DIR, ".analytics.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                created_at REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON events(project)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")


_init_db()


@analytics_bp.route("/api/analytics/track", methods=["POST"])
def track_event() -> tuple[Response, int]:
    """Record an analytics event. No PII collected."""
    data = request.get_json(silent=True) or {}
    project = data.get("project", "unknown")
    event_type = data.get("event")
    event_data = data.get("data")

    if not event_type:
        return jsonify({"status": "error", "error": "Missing event type"}), 400

    allowed_events = {"render", "export", "preset_apply", "mode_switch", "share", "verify"}
    if event_type not in allowed_events:
        return jsonify({"status": "error", "error": f"Unknown event type: {event_type}"}), 400

    # Sanitize event_data: whitelist known keys, limit size
    ALLOWED_DATA_KEYS = {"mode", "preset", "format", "parts", "project", "duration_ms", "params"}
    if event_data:
        if not isinstance(event_data, dict):
            return jsonify({"status": "error", "error": "event data must be an object"}), 400
        event_data = {k: v for k, v in event_data.items() if k in ALLOWED_DATA_KEYS}
        # Ensure string values are bounded
        for k, v in event_data.items():
            if isinstance(v, str) and len(v) > 200:
                event_data[k] = v[:200]

    with get_db() as conn:
        conn.execute(
            "INSERT INTO events (project, event_type, event_data, created_at) VALUES (?, ?, ?, ?)",
            (project, event_type, json.dumps(event_data) if event_data else None, time.time()),
        )

    return jsonify({"ok": True}), 201


@analytics_bp.route("/api/analytics/<slug>/summary", methods=["GET"])
def get_summary(slug: str) -> Response:
    """Return aggregate analytics for a project."""
    days = int(request.args.get("days", 30))
    since = time.time() - (days * 86400)

    with get_db() as conn:
        # Event counts by type
        rows = conn.execute(
            "SELECT event_type, COUNT(*) as count FROM events WHERE project = ? AND created_at > ? GROUP BY event_type",
            (slug, since),
        ).fetchall()
        counts = {row["event_type"]: row["count"] for row in rows}

        # Mode distribution
        mode_rows = conn.execute(
            "SELECT json_extract(event_data, '$.mode') as mode, COUNT(*) as count "
            "FROM events WHERE project = ? AND event_type = 'render' AND created_at > ? AND event_data IS NOT NULL "
            "GROUP BY mode",
            (slug, since),
        ).fetchall()
        modes = {row["mode"]: row["count"] for row in mode_rows if row["mode"]}

        # Daily render counts (last N days)
        daily_rows = conn.execute(
            "SELECT date(created_at, 'unixepoch') as day, COUNT(*) as count "
            "FROM events WHERE project = ? AND event_type = 'render' AND created_at > ? "
            "GROUP BY day ORDER BY day",
            (slug, since),
        ).fetchall()
        daily = [{"date": row["day"], "renders": row["count"]} for row in daily_rows]

    return jsonify({
        "project": slug,
        "period_days": days,
        "event_counts": counts,
        "mode_distribution": modes,
        "daily_renders": daily,
    })
