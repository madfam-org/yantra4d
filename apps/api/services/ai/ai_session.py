"""
In-memory or Redis-backed per-session conversation store.
Auto-expires after 1 hour. Includes circuit breaker for Redis resilience,
schema validation, distributed locking, and per-user session limits.
"""
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field

import redis

logger = logging.getLogger(__name__)

# Configuration
MAX_AGE = 3600  # 1 hour
MAX_SESSIONS_PER_USER = 5
LOCK_TTL_SECONDS = 5

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


# ---------------------------------------------------------------------------
# Session Data Schema
# ---------------------------------------------------------------------------

@dataclass
class SessionData:
    """Validated session data structure."""
    project_slug: str
    mode: str  # configurator | code-editor | synthesizer
    messages: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    user_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData | None":
        """Parse and validate session data. Returns None if invalid."""
        try:
            if not isinstance(data, dict):
                return None
            project_slug = data.get("project_slug")
            mode = data.get("mode")
            if not project_slug or not isinstance(project_slug, str):
                return None
            if mode not in ("configurator", "code-editor", "synthesizer"):
                return None
            messages = data.get("messages", [])
            if not isinstance(messages, list):
                return None
            created_at = data.get("created_at", time.time())
            if not isinstance(created_at, (int, float)):
                return None
            user_id = data.get("user_id")
            return cls(
                project_slug=project_slug,
                mode=mode,
                messages=messages,
                created_at=float(created_at),
                user_id=user_id,
            )
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

def _redis_available() -> bool:
    """Check if Redis should be attempted (circuit breaker check)."""
    if not redis_client:
        return False
    # Circuit is closed (Redis usable) once the cooldown window has elapsed.
    return time.time() >= _redis_circuit_open_until


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


# ---------------------------------------------------------------------------
# Distributed Locking (Redis only)
# ---------------------------------------------------------------------------

def _acquire_lock(session_id: str) -> bool:
    """Acquire a distributed lock for session updates. Returns True if acquired."""
    if not _redis_available():
        return True  # No locking needed for in-memory
    try:
        lock_key = f"ai_session_lock:{session_id}"
        acquired = redis_client.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS)
        if acquired:
            _redis_success()
        return bool(acquired)
    except redis.RedisError as e:
        _redis_failure("acquire_lock", e)
        return True  # Fall through to in-memory (no lock needed)


def _release_lock(session_id: str) -> None:
    """Release a distributed lock for session updates."""
    if not _redis_available():
        return
    try:
        redis_client.delete(f"ai_session_lock:{session_id}")
        _redis_success()
    except redis.RedisError as e:
        _redis_failure("release_lock", e)


# ---------------------------------------------------------------------------
# Per-User Session Limits
# ---------------------------------------------------------------------------

def _check_user_session_limit(user_id: str | None) -> bool:
    """Check if user has reached the max session limit. Returns True if allowed."""
    if not user_id:
        return True  # No limit for anonymous users

    if _redis_available():
        try:
            set_key = f"ai_sessions:user:{user_id}"
            count = redis_client.scard(set_key)
            _redis_success()
            return count < MAX_SESSIONS_PER_USER
        except redis.RedisError as e:
            _redis_failure("check_user_limit", e)

    # In-memory fallback: count sessions belonging to this user
    user_count = sum(
        1 for s in _sessions.values()
        if s.get("user_id") == user_id
    )
    return user_count < MAX_SESSIONS_PER_USER


def _register_user_session(user_id: str | None, session_id: str) -> None:
    """Register a session in the user's session set."""
    if not user_id:
        return

    if _redis_available():
        try:
            set_key = f"ai_sessions:user:{user_id}"
            redis_client.sadd(set_key, session_id)
            redis_client.expire(set_key, MAX_AGE)
            _redis_success()
        except redis.RedisError as e:
            _redis_failure("register_user_session", e)


def _unregister_user_session(user_id: str | None, session_id: str) -> None:
    """Remove a session from the user's session set."""
    if not user_id:
        return

    if _redis_available():
        try:
            set_key = f"ai_sessions:user:{user_id}"
            redis_client.srem(set_key, session_id)
            _redis_success()
        except redis.RedisError as e:
            _redis_failure("unregister_user_session", e)


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def cleanup_expired(max_age: int = MAX_AGE) -> None:
    """Remove sessions older than max_age seconds (only for in-memory)."""
    if redis_client:
        return  # Redis handles expiry automatically
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s.get("created_at", 0) > max_age]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.debug("Cleaned up %d expired AI sessions", len(expired))


def create_session(
    project_slug: str,
    mode: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> str | None:
    """Create a new chat session. Returns session_id (UUID) or None if limit reached.

    Args:
        project_slug: The project this session belongs to.
        mode: Session mode (configurator, code-editor, synthesizer).
        session_id: Optional pre-generated session ID. If None, a new UUID is generated.
        user_id: Optional user ID for per-user session limits.
    """
    # Check per-user session limit
    if not _check_user_session_limit(user_id):
        logger.warning("User %s reached max session limit (%d)", user_id, MAX_SESSIONS_PER_USER)
        return None

    session_id = session_id or str(uuid.uuid4())
    session = SessionData(
        project_slug=project_slug,
        mode=mode,
        messages=[],
        created_at=time.time(),
        user_id=user_id,
    )
    session_data = session.to_dict()

    if _redis_available():
        try:
            redis_client.setex(
                f"ai_session:{session_id}",
                MAX_AGE,
                json.dumps(session_data)
            )
            _redis_success()
            _register_user_session(user_id, session_id)
            return session_id
        except redis.RedisError as e:
            _redis_failure("create_session", e)

    cleanup_expired()
    _sessions[session_id] = session_data
    return session_id


def get_session_data(session_id: str) -> dict | None:
    """Retrieve and validate session data from Redis or memory."""
    if _redis_available():
        try:
            data = redis_client.get(f"ai_session:{session_id}")
            if data:
                _redis_success()
                parsed = json.loads(data)
                # Validate schema
                validated = SessionData.from_dict(parsed)
                if validated is None:
                    logger.warning("Session %s has invalid data, treating as expired", session_id)
                    return None
                return validated.to_dict()
            _redis_success()
            return None
        except redis.RedisError as e:
            _redis_failure("get_session", e)

    # In-memory retrieval
    session = _sessions.get(session_id)
    if session and time.time() - session.get("created_at", 0) > MAX_AGE:
        del _sessions[session_id]
        return None
    if session:
        # Validate in-memory data too
        validated = SessionData.from_dict(session)
        if validated is None:
            del _sessions[session_id]
            return None
    return session


def update_session_data(session_id: str, data: dict) -> None:
    """Update session data in Redis or memory with distributed locking."""
    if _redis_available():
        if not _acquire_lock(session_id):
            logger.warning("Could not acquire lock for session %s, retrying without lock", session_id)

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
        finally:
            _release_lock(session_id)

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
