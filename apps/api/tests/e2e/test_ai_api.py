"""Tests for AI API routes (session creation, tier gating)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path):
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test Project", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "default", "scad_file": "main.scad", "label": {"en": "Default"}, "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"}, "default_color": "#ffffff"}],
        "parameters": [{"id": "width", "type": "number", "default": 50, "min": 10, "max": 100, "step": 5, "label": {"en": "Width"}}],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube($width);")

    from config import Config
    Config.AI_API_KEY = "test-key"

    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestAiSessionEndpoint:
    def test_create_configurator_session(self, client):
        res = client.post("/api/ai/session", json={"project": "test-project", "mode": "configurator"})
        assert res.status_code == 200
        data = res.get_json()
        assert "session_id" in data

    def test_create_code_editor_session(self, client):
        """Code editor also works when auth is disabled (conftest sets AUTH_ENABLED=False → madfam)."""
        res = client.post("/api/ai/session", json={"project": "test-project", "mode": "code-editor"})
        assert res.status_code == 200

    def test_missing_fields(self, client):
        res = client.post("/api/ai/session", json={"project": "test-project"})
        assert res.status_code == 400

    def test_invalid_mode(self, client):
        res = client.post("/api/ai/session", json={"project": "test-project", "mode": "invalid"})
        assert res.status_code == 400

    def test_no_api_key_returns_503(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "AI_API_KEY", "")
        res = client.post("/api/ai/session", json={"project": "test-project", "mode": "configurator"})
        assert res.status_code == 503


class TestChatStreamEndpoint:
    def test_missing_session_id(self, client):
        res = client.post("/api/ai/chat-stream", json={"message": "hello"})
        assert res.status_code == 400

    def test_missing_message(self, client):
        # Create a session first
        res = client.post("/api/ai/session", json={"project": "test-project", "mode": "configurator"})
        sid = res.get_json()["session_id"]
        res = client.post("/api/ai/chat-stream", json={"session_id": sid})
        assert res.status_code == 400

    def test_expired_session(self, client):
        res = client.post("/api/ai/chat-stream", json={"session_id": "nonexistent", "message": "hello"})
        assert res.status_code == 404

    def test_no_api_key_returns_503(self, client, monkeypatch):
        """chat-stream with no API key configured returns 503."""
        from config import Config
        monkeypatch.setattr(Config, "AI_API_KEY", "")
        res = client.post("/api/ai/chat-stream", json={"session_id": "x", "message": "hello"})
        assert res.status_code == 503
        assert "not configured" in res.get_json()["error"]

    def test_message_too_long(self, client):
        """Message exceeding MAX_AI_MESSAGE_CHARS is rejected."""
        # Create a session first
        res = client.post("/api/ai/session", json={"project": "test-project", "mode": "configurator"})
        sid = res.get_json()["session_id"]
        long_msg = "x" * 5001
        res = client.post("/api/ai/chat-stream", json={"session_id": sid, "message": long_msg})
        assert res.status_code == 400
        assert "characters or less" in res.get_json()["error"]

    def test_empty_message_rejected(self, client):
        """Empty/whitespace-only message is rejected as missing."""
        res = client.post("/api/ai/chat-stream", json={"session_id": "any", "message": "   "})
        assert res.status_code == 400


class TestAiSessionValidation:
    def test_missing_project_slug(self, client):
        """Session creation without project slug returns 400."""
        res = client.post("/api/ai/session", json={"mode": "configurator"})
        assert res.status_code == 400

    def test_session_missing_both_fields(self, client):
        """Session creation with empty body returns 400."""
        res = client.post("/api/ai/session", json={})
        assert res.status_code == 400


class TestSynthesizeEndpoint:
    def test_missing_prompt(self, client):
        """Synthesize without prompt returns 400."""
        res = client.post("/api/ai/synthesize", json={"prompt": ""})
        assert res.status_code == 400
        assert "prompt is required" in res.get_json()["error"]

    def test_no_api_key_returns_503(self, client, monkeypatch):
        """Synthesize with no API key returns 503."""
        from config import Config
        monkeypatch.setattr(Config, "AI_API_KEY", "")
        res = client.post("/api/ai/synthesize", json={"prompt": "make a box"})
        assert res.status_code == 503
