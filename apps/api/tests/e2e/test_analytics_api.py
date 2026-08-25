"""Tests for analytics API routes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

    # Use temp SQLite for analytics DB via SQLAlchemy
    db_uri = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", db_uri)

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True

    with flask_app.app_context():
        from extensions import db
        db.create_all()

    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestTrackEvent:
    def test_track_render(self, client):
        res = client.post("/api/analytics/track", json={
            "project": "test-project",
            "event": "render",
            "data": {"mode": "default"},
        })
        assert res.status_code == 201
        assert res.get_json()["ok"] is True

    def test_track_export(self, client):
        res = client.post("/api/analytics/track", json={
            "project": "test-project",
            "event": "export",
        })
        assert res.status_code == 201

    def test_track_missing_event(self, client):
        res = client.post("/api/analytics/track", json={"project": "test-project"})
        assert res.status_code == 400

    def test_track_unknown_event(self, client):
        res = client.post("/api/analytics/track", json={
            "project": "test-project",
            "event": "hack",
        })
        assert res.status_code == 400

    def test_track_all_allowed_events(self, client):
        for evt in ["render", "export", "preset_apply", "mode_switch", "share", "verify"]:
            res = client.post("/api/analytics/track", json={"project": "p", "event": evt})
            assert res.status_code == 201


class TestSummary:
    def test_summary_empty(self, client):
        res = client.get("/api/analytics/test-project/summary")
        assert res.status_code == 200
        data = res.get_json()
        assert data["project"] == "test-project"
        assert data["event_counts"] == {}

    def test_summary_with_events(self, client):
        client.post("/api/analytics/track", json={"project": "test-project", "event": "render", "data": {"mode": "default"}})
        client.post("/api/analytics/track", json={"project": "test-project", "event": "render"})
        client.post("/api/analytics/track", json={"project": "test-project", "event": "export"})

        res = client.get("/api/analytics/test-project/summary")
        data = res.get_json()
        assert data["event_counts"]["render"] == 2
        assert data["event_counts"]["export"] == 1

    def test_summary_days_param(self, client):
        res = client.get("/api/analytics/test-project/summary?days=7")
        assert res.status_code == 200
        data = res.get_json()
        assert data["period_days"] == 7


def _enable_rate_limits(app):
    """Re-init the limiter with limits enabled on a freshly built app.

    The autouse conftest fixture disables the limiter before create_app() runs,
    which makes flask-limiter's init_app skip registering its request hooks
    entirely. Re-running init_app (before the app's first request) registers
    them so rate limit headers can be observed.
    """
    from extensions import limiter
    app.config["RATELIMIT_ENABLED"] = True
    limiter.enabled = True
    limiter.init_app(app)


class TestRateLimits:
    """Analytics endpoints stay unauthenticated but must carry rate limits.

    Rate limit headers (headers_enabled=True in extensions.py) prove the
    @limiter.limit decorator is registered with the intended value.
    """

    def test_track_carries_rate_limit(self, app, client):
        from extensions import limiter
        _enable_rate_limits(app)
        try:
            res = client.post("/api/analytics/track", json={"project": "p", "event": "render"})
            assert res.status_code == 201
            assert res.headers.get("X-RateLimit-Limit") == "120"
        finally:
            limiter.enabled = False

    def test_summary_carries_rate_limit(self, app, client):
        from extensions import limiter
        _enable_rate_limits(app)
        try:
            res = client.get("/api/analytics/test-project/summary")
            assert res.status_code == 200
            assert res.headers.get("X-RateLimit-Limit") == "60"
        finally:
            limiter.enabled = False
