"""Tests for AI session store."""
import time
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ai_session import (
    create_session, get_session, append_message, get_messages, cleanup_expired, _sessions,
)


@pytest.fixture(autouse=True)
def _clear_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


class TestAiSession:
    def test_create_and_get(self):
        sid = create_session("my-project", "configurator")
        session = get_session(sid)
        assert session is not None
        assert session["project_slug"] == "my-project"
        assert session["mode"] == "configurator"
        assert session["messages"] == []

    def test_get_nonexistent(self):
        assert get_session("no-such-id") is None

    def test_append_and_get_messages(self):
        sid = create_session("proj", "code-editor")
        append_message(sid, "user", "hello")
        append_message(sid, "assistant", "hi")
        msgs = get_messages(sid)
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "hello"}
        assert msgs[1] == {"role": "assistant", "content": "hi"}

    def test_expired_session_returns_none(self, monkeypatch):
        sid = create_session("proj", "configurator")
        # Fake the creation time to be 2 hours ago
        _sessions[sid]["created_at"] = time.time() - 7200
        assert get_session(sid) is None

    def test_cleanup_expired(self, monkeypatch):
        sid1 = create_session("a", "configurator")
        sid2 = create_session("b", "configurator")
        _sessions[sid1]["created_at"] = time.time() - 7200
        cleanup_expired()
        assert get_session(sid1) is None
        assert get_session(sid2) is not None

    def test_get_messages_expired(self):
        sid = create_session("p", "configurator")
        _sessions[sid]["created_at"] = time.time() - 7200
        assert get_messages(sid) == []
