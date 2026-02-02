"""
In-memory per-session conversation store. Auto-expires after 1 hour.
Not persisted across restarts.
"""
import time
import uuid
import logging

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}

MAX_AGE = 3600  # 1 hour


def cleanup_expired(max_age: int = MAX_AGE) -> None:
    """Remove sessions older than max_age seconds."""
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s["created_at"] > max_age]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.debug("Cleaned up %d expired AI sessions", len(expired))


def create_session(project_slug: str, mode: str) -> str:
    """Create a new chat session. Returns session_id (UUID)."""
    cleanup_expired()
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "project_slug": project_slug,
        "mode": mode,
        "messages": [],
        "created_at": time.time(),
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    """Get session dict or None if expired/missing."""
    session = _sessions.get(session_id)
    if session and time.time() - session["created_at"] > MAX_AGE:
        del _sessions[session_id]
        return None
    return session


def append_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history."""
    session = get_session(session_id)
    if session:
        session["messages"].append({"role": role, "content": content})


def get_messages(session_id: str) -> list[dict]:
    """Return message history for the session."""
    session = get_session(session_id)
    if not session:
        return []
    return session["messages"]
