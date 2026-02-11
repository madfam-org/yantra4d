"""
In-memory or Redis-backed per-session conversation store.
Auto-expires after 1 hour.
"""
import time
import uuid
import logging
import os
import json
import redis


logger = logging.getLogger(__name__)

# Configuration
MAX_AGE = 3600  # 1 hour
REDIS_URL = os.getenv("REDIS_URL")

# Redis Client
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL)
        logger.info("Connected to Redis for AI sessions at %s", REDIS_URL)
    except Exception as e:
        logger.warning("Failed to connect to Redis: %s", e)

# In-memory fallback
_sessions: dict[str, dict] = {}


def cleanup_expired(max_age: int = MAX_AGE) -> None:
    """Remove sessions older than max_age seconds (only for in-memory)."""
    if redis_client:
        return  # Redis handles expiry automatically
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s["created_at"] > max_age]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.debug("Cleaned up %d expired AI sessions", len(expired))


def create_session(project_slug: str, mode: str) -> str:
    """Create a new chat session. Returns session_id (UUID)."""
    session_id = str(uuid.uuid4())
    session_data = {
        "project_slug": project_slug,
        "mode": mode,
        "messages": [],
        "created_at": time.time(),
    }

    if redis_client:
        try:
            redis_client.setex(
                f"ai_session:{session_id}",
                MAX_AGE,
                json.dumps(session_data)
            )
            return session_id
        except redis.RedisError as e:
            logger.error("Redis error on create_session: %s", e)
            # Fallback to memory? or explicit failure?
            # Fallback is safer for reliability if Redis flaps
            pass

    cleanup_expired()
    _sessions[session_id] = session_data
    return session_id


def get_session_data(session_id: str) -> dict | None:
    """Retrieve session data from Redis or memory."""
    if redis_client:
        try:
            data = redis_client.get(f"ai_session:{session_id}")
            if data:
                return json.loads(data)
            return None
        except redis.RedisError as e:
            logger.error("Redis error on get_session: %s", e)
            # Fallback check memory?
            pass
    
    # In-memory retrieval
    session = _sessions.get(session_id)
    if session and time.time() - session["created_at"] > MAX_AGE:
        del _sessions[session_id]
        return None
    return session


def update_session_data(session_id: str, data: dict) -> None:
    """Update session data in Redis or memory."""
    if redis_client:
        try:
            # Reset expiry on update
            redis_client.setex(
                f"ai_session:{session_id}",
                MAX_AGE,
                json.dumps(data)
            )
            return
        except redis.RedisError as e:
            logger.error("Redis error on update_session: %s", e)
            pass

    _sessions[session_id] = data


def get_session(session_id: str) -> dict | None:
    """Get session dict or None if expired/missing."""
    return get_session_data(session_id)


def append_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history."""
    session = get_session_data(session_id)
    if session:
        session["messages"].append({"role": role, "content": content})
        update_session_data(session_id, session)


def get_messages(session_id: str) -> list[dict]:
    """Return message history for the session."""
    session = get_session_data(session_id)
    if not session:
        return []
    return session["messages"]
