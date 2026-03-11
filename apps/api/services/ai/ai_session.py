"""
In-memory or Redis-backed per-session conversation store.
Auto-expires after 1 hour. Includes circuit breaker for Redis resilience.
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

# Redis Client with circuit breaker
redis_client = None
_redis_failure_count = 0
_redis_circuit_open_until = 0.0
_REDIS_CIRCUIT_THRESHOLD = 3    # failures before opening circuit
_REDIS_CIRCUIT_COOLDOWN = 60.0  # seconds to wait before retrying

if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL)
        logger.info("Connected to Redis for AI sessions at %s", REDIS_URL)
    except Exception as e:
        logger.warning("Failed to connect to Redis: %s", e)
else:
    _debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    if not _debug:
        logger.warning(
            "REDIS_URL not set: AI sessions will be lost on pod restart. "
            "Set REDIS_URL for production."
        )

# In-memory fallback
_sessions: dict[str, dict] = {}


def _redis_available() -> bool:
    """Check if Redis should be attempted (circuit breaker check)."""
    global _redis_failure_count, _redis_circuit_open_until
    if not redis_client:
        return False
    if time.time() < _redis_circuit_open_until:
        return False
    return True


def _redis_success() -> None:
    """Record a successful Redis operation — reset circuit breaker."""
    global _redis_failure_count, _redis_circuit_open_until
    _redis_failure_count = 0
    _redis_circuit_open_until = 0.0


def _redis_failure(operation: str, error: Exception) -> None:
    """Record a Redis failure — open circuit after threshold."""
    global _redis_failure_count, _redis_circuit_open_until
    _redis_failure_count += 1
    logger.warning("Redis %s failed (%d/%d): %s",
                   operation, _redis_failure_count, _REDIS_CIRCUIT_THRESHOLD, error)
    if _redis_failure_count >= _REDIS_CIRCUIT_THRESHOLD:
        _redis_circuit_open_until = time.time() + _REDIS_CIRCUIT_COOLDOWN
        logger.error("Redis circuit breaker OPEN — falling back to in-memory for %ds",
                     int(_REDIS_CIRCUIT_COOLDOWN))


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


def create_session(project_slug: str, mode: str, session_id: str | None = None) -> str:
    """Create a new chat session. Returns session_id (UUID).

    Args:
        project_slug: The project this session belongs to.
        mode: Session mode (configurator, code-editor, synthesizer).
        session_id: Optional pre-generated session ID. If None, a new UUID is generated.
    """
    session_id = session_id or str(uuid.uuid4())
    session_data = {
        "project_slug": project_slug,
        "mode": mode,
        "messages": [],
        "created_at": time.time(),
    }

    if _redis_available():
        try:
            redis_client.setex(
                f"ai_session:{session_id}",
                MAX_AGE,
                json.dumps(session_data)
            )
            _redis_success()
            return session_id
        except redis.RedisError as e:
            _redis_failure("create_session", e)

    cleanup_expired()
    _sessions[session_id] = session_data
    return session_id


def get_session_data(session_id: str) -> dict | None:
    """Retrieve session data from Redis or memory."""
    if _redis_available():
        try:
            data = redis_client.get(f"ai_session:{session_id}")
            if data:
                _redis_success()
                return json.loads(data)
            _redis_success()
            return None
        except redis.RedisError as e:
            _redis_failure("get_session", e)
    
    # In-memory retrieval
    session = _sessions.get(session_id)
    if session and time.time() - session["created_at"] > MAX_AGE:
        del _sessions[session_id]
        return None
    return session


def update_session_data(session_id: str, data: dict) -> None:
    """Update session data in Redis or memory."""
    if _redis_available():
        try:
            # Reset expiry on update
            redis_client.setex(
                f"ai_session:{session_id}",
                MAX_AGE,
                json.dumps(data)
            )
            _redis_success()
            return
        except redis.RedisError as e:
            _redis_failure("update_session", e)

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
