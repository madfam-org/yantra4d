"""
JWT authentication middleware using Janua JWKS endpoint.
Provides decorators for route-level auth enforcement.
"""
import functools
import logging

import jwt
from flask import request
from jwt import PyJWKClient

from config import Config
from services.route_helpers import error_response

logger = logging.getLogger(__name__)

# Lazy-initialized JWKS client (created on first use)
_jwk_client = None


def _get_jwk_client():
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(Config.JANUA_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwk_client


def decode_token(token: str) -> dict:
    """Decode and validate a JWT using the Janua JWKS endpoint.

    Returns the decoded claims dict.
    Raises jwt.exceptions.PyJWTError on any validation failure.
    """
    jwk_client = _get_jwk_client()
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        issuer=Config.JANUA_ISSUER,
        audience=Config.JANUA_AUDIENCE,
        options={"require": ["exp", "iss", "sub"]},
    )
    return claims


def _extract_bearer_token() -> str | None:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def require_auth(f):
    """Decorator: reject request with 401 if no valid Bearer token."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not Config.AUTH_ENABLED:
            request.auth_claims = None
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if not token:
            return error_response("Authentication required", 401)

        try:
            claims = decode_token(token)
        except Exception as e:
            logger.debug("JWT validation failed: %s", e)
            return error_response("Invalid or expired token", 401)

        request.auth_claims = claims
        return f(*args, **kwargs)

    return decorated


def require_role(role: str):
    """Decorator factory: require_auth + check that claims contain the given role."""
    def decorator(f):
        @functools.wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if not Config.AUTH_ENABLED:
                return f(*args, **kwargs)

            claims = getattr(request, "auth_claims", None)
            if not claims:
                return error_response("Authentication required", 401)

            # Check role in claims — supports both 'role' string and 'roles' array
            user_roles = claims.get("roles", [])
            if isinstance(user_roles, str):
                user_roles = [user_roles]
            user_role = claims.get("role", "")
            if user_role:
                user_roles.append(user_role)

            if role not in user_roles:
                return error_response("Insufficient permissions", 403)

            return f(*args, **kwargs)
        return decorated
    return decorator


def optional_auth(f):
    """Decorator: decode token if present, set request.auth_claims (None if anonymous)."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        request.auth_claims = None

        if not Config.AUTH_ENABLED:
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if token:
            try:
                request.auth_claims = decode_token(token)
            except Exception as e:
                logger.debug("Optional auth token invalid: %s", e)

        return f(*args, **kwargs)

    return decorated
