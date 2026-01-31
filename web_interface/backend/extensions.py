"""Shared Flask extensions (initialized in app factory)."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour"],
    storage_uri="memory://",
)
