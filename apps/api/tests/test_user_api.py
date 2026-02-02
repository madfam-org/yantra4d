"""Tests for user API routes."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"name": "Test", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestGetTiers:
    def test_returns_tiers(self, client):
        res = client.get("/api/tiers")
        assert res.status_code == 200
        data = res.get_json()
        assert "guest" in data
        assert "pro" in data
        assert "madfam" in data
        assert "renders_per_hour" in data["guest"]


class TestGetMe:
    def test_auth_disabled_returns_madfam(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        res = client.get("/api/me")
        assert res.status_code == 200
        data = res.get_json()
        assert data["tier"] == "madfam"
        assert data["user"] is None

    def test_anonymous_returns_guest(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        res = client.get("/api/me")
        assert res.status_code == 200
        data = res.get_json()
        assert data["tier"] == "guest"
        assert data["user"] is None
        assert "limits" in data
