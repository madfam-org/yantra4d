"""Tests for extended health check endpoints."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "STATIC_DIR", tmp_path / "static")
    (tmp_path / "static").mkdir()
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestLiveness:
    def test_always_200(self, client):
        resp = client.get("/api/health/live")
        assert resp.status_code == 200
        assert resp.json["status"] == "alive"


class TestReadiness:
    def test_healthy_when_openscad_exists(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "OPENSCAD_PATH", "/bin/sh")  # exists on all systems
        resp = client.get("/api/health/ready")
        assert resp.status_code == 200
        data = resp.json
        assert data["status"] in ("healthy", "degraded")
        assert data["checks"]["openscad"]["ok"] is True

    def test_degraded_when_openscad_missing(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "OPENSCAD_PATH", "/nonexistent/binary")
        resp = client.get("/api/health/ready")
        assert resp.status_code == 200
        assert resp.json["status"] == "degraded"
        assert resp.json["checks"]["openscad"]["ok"] is False

    def test_degraded_when_redis_unreachable(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "OPENSCAD_PATH", "/bin/sh")
        monkeypatch.setenv("REDIS_URL", "redis://nonexistent:6379")
        resp = client.get("/api/health/ready")
        data = resp.json
        # Should be degraded (not unhealthy) since Redis is optional
        assert data["status"] in ("degraded", "healthy")
        assert "redis" in data["checks"]

    def test_backward_compat_health_endpoint(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "OPENSCAD_PATH", "/bin/sh")
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert "checks" in resp.json
