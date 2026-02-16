"""Shared Flask extensions (initialized in app factory)."""
import os

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def tiered_rate_key():
    """Rate limit key: use user ID for authenticated users, IP for anonymous."""
    claims = getattr(request, "auth_claims", None)
    if claims and claims.get("sub"):
        return f"user:{claims['sub']}"
    return f"ip:{get_remote_address()}"

# RATE_LIMIT_STORAGE controls the rate-limiter backend:
#   "memory://"          — per-process (default, not shared across workers)
#   "redis://host:port"  — shared across workers via Redis
_storage_uri = os.environ.get("RATE_LIMIT_STORAGE", os.environ.get("REDIS_URL", "memory://"))

# Disable rate limiting in dev mode (FLASK_DEBUG=true) unless explicitly overridden.
# Production Dockerfile sets FLASK_DEBUG=false, so limits are always active in prod.
_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
_default_enabled = "false" if _debug else "true"
_enabled = os.environ.get("RATE_LIMIT_ENABLED", _default_enabled).lower() not in ("0", "false", "no")

limiter = Limiter(
    key_func=tiered_rate_key,
    default_limits=["500 per hour"],
    storage_uri=_storage_uri,
    enabled=_enabled,
)
