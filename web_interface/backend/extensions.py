"""Shared Flask extensions (initialized in app factory)."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# NOTE: "memory://" storage is per-process — limits are not shared across
# gunicorn workers. For accurate multi-worker rate limiting, switch to a
# shared backend, e.g. storage_uri="redis://localhost:6379".
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour"],
    storage_uri="memory://",
)
