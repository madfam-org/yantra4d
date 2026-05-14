"""Shared Flask extensions (initialized in app factory)."""
import os
import logging

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Database
db = SQLAlchemy()
migrate = Migrate()
logger = logging.getLogger(__name__)


def tiered_rate_key():
    """Rate limit key: use user ID for authenticated users, IP for anonymous."""
    claims = getattr(request, "auth_claims", None)
    if claims and claims.get("sub"):
        return f"user:{claims['sub']}"
    return f"ip:{get_remote_address()}"

# RATE_LIMIT_STORAGE controls the rate-limiter backend.
# If not explicitly set:
#   - debug mode defaults to memory://
#   - non-debug mode defaults to REDIS_URL, with safety fallback and warning.
_debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
_storage_env = os.environ.get("RATE_LIMIT_STORAGE")
if _storage_env:
    _storage_uri = _storage_env
elif _debug:
    _storage_uri = "memory://"
else:
    _storage_uri = os.environ.get("REDIS_URL", "memory://")

if not _debug and _storage_uri.startswith("memory://"):
    logger.warning(
        "Rate limiting storage is in-memory in non-debug mode. This is not safe for multi-worker deployments."
    )

# Disable rate limiting in dev mode (FLASK_DEBUG=true) unless explicitly overridden.
# Production Dockerfile sets FLASK_DEBUG=false, so limits are always active in prod.
_default_enabled = "false" if _debug else "true"
_enabled = os.environ.get("RATE_LIMIT_ENABLED", _default_enabled).lower() not in ("0", "false", "no")

limiter = Limiter(
    key_func=tiered_rate_key,
    default_limits=["500 per hour"],
    storage_uri=_storage_uri,
    enabled=_enabled,
    headers_enabled=True,
)
