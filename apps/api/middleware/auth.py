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
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)

JWKS_CACHE_LIFESPAN = 3600  # seconds

# Lazy-initialized JWKS client (created on first use)
_jwk_client = None


def _get_jwk_client():
    global _jwk_client
    if _jwk_client is None:
        # An explicit User-Agent: PyJWKClient's urllib default ("Python-urllib/x.y")
        # is on Cloudflare's Browser Integrity Check banned list at the auth edge —
        # the JWKS fetch 403s (Error 1010), every bearer silently degrades to guest
        # tier, and authed callers hit the guest rate limit. Found 2026-08-22 via
        # the Fashion Cabinet live-body seam; same fix as FC's body_render.py.
        _jwk_client = PyJWKClient(
            Config.JANUA_JWKS_URL,
            cache_keys=True,
            lifespan=JWKS_CACHE_LIFESPAN,
            headers={"User-Agent": "yantra4d-api/1.0 (+https://yantra4d.com)"},
        )
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
        algorithms=Config.JWT_ALGORITHMS or ["RS256"],
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


def _sync_user_from_claims(claims: dict) -> None:
    """Upsert the persistent User record from JWT claims (best-effort, non-blocking).

    Stores the resulting User object on ``request.current_user`` for downstream use.
    Failures are logged but never propagate to the caller.
    """
    try:
        from services.core.user_service import upsert_user_from_claims
        user = upsert_user_from_claims(claims)
        request.current_user = user
    except Exception:
        logger.debug("User upsert failed (non-critical)", exc_info=True)
        request.current_user = None


def require_auth(f):
    """Decorator: reject request with 401 if no valid Bearer token."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not Config.AUTH_ENABLED:
            request.auth_claims = None
            request.current_user = None
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if not token:
            return error_response("Authentication required", 401)

        try:
            claims = decode_token(token)
        except Exception as e:
            logger.warning("JWT validation failed: %s", e)
            return error_response("Invalid or expired token", 401)

        request.auth_claims = claims
        _sync_user_from_claims(claims)
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


def require_tier(min_tier: str):
    """Decorator factory: optional_auth + check tier hierarchy."""
    from services.core.tier_service import has_tier, resolve_tier

    def decorator(f):
        @functools.wraps(f)
        @optional_auth
        def decorated(*args, **kwargs):
            if not Config.AUTH_ENABLED:
                request.user_tier = "madfam"
                return f(*args, **kwargs)
            user_tier = resolve_tier(getattr(request, "auth_claims", None))
            if not has_tier(user_tier, min_tier):
                return error_response(f"Requires {min_tier} tier or above", 403)
            request.user_tier = user_tier
            return f(*args, **kwargs)
        return decorated
    return decorator


def optional_auth(f):
    """Decorator: decode token if present, set request.auth_claims (None if anonymous)."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        request.auth_claims = None
        request.current_user = None

        if not Config.AUTH_ENABLED:
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if token:
            try:
                request.auth_claims = decode_token(token)
                _sync_user_from_claims(request.auth_claims)
            except Exception as e:
                logger.debug("Optional auth token invalid: %s", e)

        return f(*args, **kwargs)

    return decorated


# ──────────────────────────────────────────────
# Machine-token (client_credentials) scope enforcement
# ──────────────────────────────────────────────
#
# Janua mints two shapes of token against this audience:
#
#   HUMAN   (authorization_code / refresh) — a UUID `sub`, no `token_use`,
#           no `actor_type`, no `client_id`. Tier comes from `yantra4d_tier`.
#   MACHINE (client_credentials)           — `token_use: "client_credentials"`,
#           `actor_type: "service_account"`, `sub: "service-account:{client_id}"`,
#           a space-delimited `scope`, and a `<product>_tier` claim synthesised
#           from each product-namespaced scope on the client.
#
# See janua apps/api/app/routers/v1/oauth_provider.py::_get_client_credentials_claims
# and ::_handle_client_credentials_grant for the authoritative shapes.
#
# Because the `yantra4d_tier: "madfam"` claim is DERIVED from the `yantra4d:`
# scope namespace, a machine client that never asks for `yantra4d:render` can
# still present a token this API happily accepts — the scope Janua mints is
# decorative unless the resource server checks it. That is what this enforces.
#
# Anonymous and human traffic is deliberately untouched: those paths stay
# tier/rate-limit driven exactly as before.

RENDER_SCOPE = "yantra4d:render"

_TRUTHY = ("1", "true", "yes", "on")


def is_machine_token(claims: dict | None) -> bool:
    """Whether these claims came from a client_credentials (machine) grant.

    Keyed on the claims Janua emits for machine tokens only. Any one of them
    is sufficient — they are emitted together, and matching on the union means
    a partial claim set still fails toward "this is a machine" rather than
    silently slipping through the human path.

    Human tokens carry none of these, so this never mis-classifies a browser
    session or an anonymous (claims=None) request.
    """
    if not claims:
        return False
    if claims.get("token_use") == "client_credentials":
        return True
    if claims.get("actor_type") == "service_account":
        return True
    sub = claims.get("sub")
    return isinstance(sub, str) and sub.startswith("service-account:")


def machine_client_id(claims: dict | None) -> str:
    """Best-effort per-client identity for logs. Never echoes the token."""
    if not claims:
        return "<unknown>"
    client_id = claims.get("client_id")
    if client_id:
        return str(client_id)
    sub = claims.get("sub")
    if isinstance(sub, str) and sub.startswith("service-account:"):
        return sub.removeprefix("service-account:")
    return str(sub) if sub else "<unknown>"


def token_scopes(claims: dict | None) -> set[str]:
    """Parse the space-delimited OAuth `scope` claim into a set.

    Tolerates the list form some issuers use, and the `scp` alias, so a
    conformant client is never rejected over claim spelling.
    """
    if not claims:
        return set()
    raw = claims.get("scope")
    if raw is None:
        raw = claims.get("scp")
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {s for s in raw.split() if s}
    if isinstance(raw, (list, tuple, set)):
        return {str(s).strip() for s in raw if str(s).strip()}
    return set()


def render_scope_enforcement_mode() -> str:
    """Read RENDER_SCOPE_ENFORCEMENT at call time so env changes take effect.

    Returns "enforce" or "log". Default (and any unrecognised value) is "log":
    this rolls out behind an observation window exactly like
    RENDER_STRICT_PAYLOAD, so a non-conformant machine client shows up in the
    logs before it starts getting 403s.
    """
    import os

    raw = os.getenv("RENDER_SCOPE_ENFORCEMENT", "").strip().lower()
    if raw == "enforce" or raw in _TRUTHY:
        return "enforce"
    if raw and raw != "log":
        logger.warning(
            "Unrecognised RENDER_SCOPE_ENFORCEMENT value %r — defaulting to 'log'. "
            "Valid values: 'log', 'enforce'.",
            raw,
        )
    return "log"


def require_scope_for_machine_tokens(scope: str):
    """Decorator factory: require `scope` on MACHINE tokens only.

    Layered on top of `@optional_auth`, which must already have populated
    `request.auth_claims`. Apply it BELOW `@optional_auth` in the decorator
    stack so claims exist by the time this runs.

    Semantics, by caller:

      anonymous (no token)      -> untouched; proceeds on the guest tier.
      human token               -> untouched; proceeds on its `yantra4d_tier`.
      machine token WITH scope  -> untouched; proceeds on its `yantra4d_tier`.
      machine token WITHOUT     -> log mode: structured warning, then ALLOWED.
                                   enforce mode: 403.

    The tier claim is never re-derived here — a conformant machine token
    resolves its tier through exactly the same `resolve_tier` path as before,
    so the live FC → Yantra4D MTM render seam is unaffected.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not Config.AUTH_ENABLED:
                return f(*args, **kwargs)

            claims = getattr(request, "auth_claims", None)
            if not is_machine_token(claims):
                # Anonymous and human callers: unchanged behaviour, by design.
                return f(*args, **kwargs)

            if scope in token_scopes(claims):
                return f(*args, **kwargs)

            mode = render_scope_enforcement_mode()
            client_id = machine_client_id(claims)
            present = sorted(token_scopes(claims))
            logger.warning(
                "render.scope_missing client_id=%s missing_scope=%s "
                "present_scopes=%s path=%s mode=%s outcome=%s",
                client_id,
                scope,
                ",".join(present) or "<none>",
                request.path,
                mode,
                "denied" if mode == "enforce" else "allowed",
            )
            if mode == "enforce":
                return error_response(
                    f"This endpoint requires the '{scope}' scope. The presented "
                    "machine token does not carry it — re-mint the client_credentials "
                    f"token requesting scope '{scope}'.",
                    403,
                    error_code="missing_scope",
                )
            return f(*args, **kwargs)

        return decorated
    return decorator


def require_render_scope(f):
    """Convenience decorator for the render routes: require `yantra4d:render`."""
    return require_scope_for_machine_tokens(RENDER_SCOPE)(f)
