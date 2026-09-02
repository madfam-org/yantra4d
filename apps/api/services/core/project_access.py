"""
Private project access control.

A project is *private* when it must render only for identities that are
explicitly entitled to it. Everything else — anonymous visitors, signed-in
users on any other tier — gets a single machine-readable refusal so the Studio
can show the right call to action rather than guessing from a bare 403.

Two independent sources declare privacy:

  ``access_control.view == "private"`` in the project manifest
      The cartridge's own statement. Travels with the project.

  ``PRIVATE_PROJECTS`` (env)
      A comma-separated list of slugs forced private regardless of what their
      manifest says. This is the fail-closed defence for client cartridges: if
      a manifest is edited, regenerated, or replaced by an upstream submodule
      bump, the deployment still refuses the project. Configuration wins.

Entitlement comes from three places, checked in this order:

  1. the top tier (``resolve_tier`` — which includes ``TIER_OVERRIDES``, so a
     staff identity configured there reaches every private project);
  2. the ``admin`` role on the token;
  3. ``PROJECT_ACCESS_GRANTS`` (env), a per-slug list of email addresses.

No identity is ever committed to this repository. Both env vars are deployment
configuration (a Kubernetes secret) and both are read at call time, so rolling
the secret takes effect without a rebuild.

Env var shapes::

    PRIVATE_PROJECTS="acme-bracket,client-widget"
    PROJECT_ACCESS_GRANTS='{"acme-bracket": ["someone@example.com"]}'
"""
import functools
import json
import logging
import os

from flask import current_app, has_app_context, jsonify

from config import Config
from middleware.auth import claim_roles, ensure_optional_auth
from services.core.tier_service import TOP_TIER, resolve_tier
from utils.route_helpers import error_response
from utils.validators import validate_project_slug

logger = logging.getLogger(__name__)

PRIVATE_PROJECTS_ENV = "PRIVATE_PROJECTS"
PROJECT_ACCESS_GRANTS_ENV = "PROJECT_ACCESS_GRANTS"

#: ``access_control.view`` value that marks a project private.
PRIVATE = "private"

#: Error code the Studio branches on. Stable API surface — do not rename.
LOCKED_ERROR_CODE = "project_locked"


# ──────────────────────────────────────────────
# Configuration loaders (call-time, cached per raw value)
# ──────────────────────────────────────────────
#
# Same shape as tier_service's override loader: read os.getenv on every call so
# a rolled secret and a monkeypatching test both take effect, but only re-parse
# when the raw value actually changed.

_private_slugs: frozenset[str] | None = None
_private_slugs_raw: str | None = None

_grants: dict[str, frozenset[str]] | None = None
_grants_raw: str | None = None


def _parse_private_projects(raw: str) -> frozenset[str]:
    """Parse the comma-separated PRIVATE_PROJECTS list."""
    slugs = set()
    for chunk in (raw or "").split(","):
        slug = chunk.strip().lower()
        if not slug:
            continue
        if validate_project_slug(slug) is not None:
            logger.warning("%s entry ignored: %r is not a valid project slug.",
                           PRIVATE_PROJECTS_ENV, slug)
            continue
        slugs.add(slug)
    if slugs:
        # Slugs are not identities, so naming them is safe and useful: an
        # operator needs to be able to confirm the list actually took.
        logger.info("%s: %d project(s) forced private: %s",
                    PRIVATE_PROJECTS_ENV, len(slugs), ", ".join(sorted(slugs)))
    return frozenset(slugs)


def private_project_slugs() -> frozenset[str]:
    """Slugs forced private by configuration, regardless of their manifest."""
    global _private_slugs, _private_slugs_raw
    raw = os.getenv(PRIVATE_PROJECTS_ENV, "") or ""
    if _private_slugs is None or raw != _private_slugs_raw:
        _private_slugs = _parse_private_projects(raw)
        _private_slugs_raw = raw
    return _private_slugs


def _parse_access_grants(raw: str) -> dict[str, frozenset[str]]:
    """Parse the PROJECT_ACCESS_GRANTS JSON object, tolerating anything broken.

    A malformed grant map must fail closed — to *no* grants — rather than take
    the API down or, worse, be read loosely enough to grant something it did
    not mean to.
    """
    raw = (raw or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as e:
        logger.warning(
            "%s is not valid JSON (%s) — no per-identity project grants are active.",
            PROJECT_ACCESS_GRANTS_ENV, e,
        )
        return {}

    if not isinstance(parsed, dict):
        logger.warning(
            "%s must be a JSON object mapping slug to a list of emails, got %s — "
            "no per-identity project grants are active.",
            PROJECT_ACCESS_GRANTS_ENV, type(parsed).__name__,
        )
        return {}

    grants: dict[str, frozenset[str]] = {}
    for slug, emails in parsed.items():
        if not isinstance(slug, str):
            continue
        slug = slug.strip().lower()
        if not slug:
            continue
        if isinstance(emails, str):
            emails = [emails]
        if not isinstance(emails, (list, tuple, set)):
            logger.warning("%s: entry for %r is not a list of emails — ignored.",
                           PROJECT_ACCESS_GRANTS_ENV, slug)
            continue
        allowed = {
            e.strip().lower()
            for e in emails
            if isinstance(e, str) and e.strip()
        }
        if allowed:
            grants[slug] = frozenset(allowed)

    # Counts only: the addresses themselves are identities.
    logger.info("%s: grants loaded for %d project(s)",
                PROJECT_ACCESS_GRANTS_ENV, len(grants))
    logger.debug("%s: %s", PROJECT_ACCESS_GRANTS_ENV,
                 {slug: sorted(e) for slug, e in grants.items()})
    return grants


def project_access_grants() -> dict[str, frozenset[str]]:
    """Per-slug sets of lower-cased email addresses granted private access."""
    global _grants, _grants_raw
    raw = os.getenv(PROJECT_ACCESS_GRANTS_ENV, "") or ""
    if _grants is None or raw != _grants_raw:
        _grants = _parse_access_grants(raw)
        _grants_raw = raw
    return _grants


# ──────────────────────────────────────────────
# Privacy and entitlement
# ──────────────────────────────────────────────


def _manifest_dict(manifest) -> dict:
    """Raw manifest data from a ProjectManifest, a plain dict, or None."""
    if manifest is None:
        return {}
    if isinstance(manifest, dict):
        return manifest
    data = getattr(manifest, "_data", None)
    if isinstance(data, dict):
        return data
    as_json = getattr(manifest, "as_json", None)
    if callable(as_json):
        try:
            data = as_json()
        except Exception:
            return {}
        if isinstance(data, dict):
            return data
    return {}


def _claim_email(claims: dict | None) -> str | None:
    """Lower-cased email from the token, or None."""
    if not isinstance(claims, dict):
        return None
    email = claims.get("email")
    if not isinstance(email, str):
        return None
    return email.strip().lower() or None


def is_private_project(slug: str | None, manifest=None) -> bool:
    """Whether ``slug`` is private, by configuration or by its own manifest."""
    if slug and slug.strip().lower() in private_project_slugs():
        return True
    access_control = _manifest_dict(manifest).get("access_control") or {}
    if not isinstance(access_control, dict):
        return False
    return access_control.get("view") == PRIVATE


def _dev_unlock_active() -> bool:
    """Local-development escape hatch: auth OFF **and** the Flask debugger ON.

    Mirrors ``routes/engine/render.py::_effective_tier`` (the #48 fix): the
    conjunct matters. Auth is also off in CI and in the test suite, and an
    auth-off-only unlock would make every private cartridge public exactly
    where nobody is watching. With the debugger on, a developer running
    ``FLASK_DEBUG=true`` against a checkout that contains a private cartridge
    can open it; app startup already shouts when auth is off outside debug.
    """
    if Config.AUTH_ENABLED:
        return False
    return has_app_context() and bool(current_app.debug)


def can_view_project(slug: str | None, manifest=None, claims: dict | None = None) -> bool:
    """Whether this caller may see a project at all.

    A public project is viewable by everyone, so this is only interesting for
    private ones. Anonymous callers never qualify: there is no identity to
    check against, and a private project must not be reachable without one.
    """
    if not is_private_project(slug, manifest):
        return True
    if _dev_unlock_active():
        return True
    if claims is None:
        return False

    # The top tier covers staff seated there by TIER_OVERRIDES, which is how a
    # named identity reaches every private project without a per-slug grant.
    if resolve_tier(claims) == TOP_TIER:
        return True

    if "admin" in claim_roles(claims):
        return True

    email = _claim_email(claims)
    if email and slug:
        return email in project_access_grants().get(slug.strip().lower(), frozenset())
    return False


# ──────────────────────────────────────────────
# Refusal
# ──────────────────────────────────────────────


def project_locked_response(slug: str, claims: dict | None = None):
    """The one refusal every gated endpoint returns: 403 ``project_locked``.

    ``auth_required`` tells the Studio which call to action to show without it
    having to infer intent from the status code: True means "nobody is signed
    in — offer sign-in", False means "you are signed in and still not on the
    list — offer request-access". The ``request_id`` from ``error_response`` is
    preserved so a refusal stays traceable in the logs.
    """
    logger.debug("project_access.denied slug=%s authenticated=%s",
                 slug, claims is not None)
    response, status = error_response(
        "This project is private", 403, error_code=LOCKED_ERROR_CODE,
    )
    payload = response.get_json()
    payload["auth_required"] = claims is None
    return jsonify(payload), status


# ──────────────────────────────────────────────
# Route entry points
# ──────────────────────────────────────────────


def _private_and_manifest(slug: str):
    """``(is_private, manifest)`` for a slug, reading the manifest only if needed.

    A slug forced private by configuration never touches the filesystem, which
    is what makes the check safe even when a manifest is missing or unreadable.
    A slug that cannot be resolved at all is reported public: discovery and the
    route's own 404 handle that case, and inventing privacy here would only
    change which error the caller sees.
    """
    if slug.strip().lower() in private_project_slugs():
        return True, None
    from manifest import get_manifest
    try:
        manifest = get_manifest(slug)
    except Exception:
        return False, None
    return is_private_project(slug, manifest), manifest


def check_project_access(slug: str | None):
    """Return the locked response when the caller may not view ``slug``, else None.

    For routes that take the slug in the request body. The public path does no
    extra work beyond the manifest lookup routes already perform: privacy is
    settled before the token is ever decoded.

    An unknown slug returns None on purpose — this never invents a 404, so each
    route keeps producing its own not-found shape.
    """
    if not slug or not isinstance(slug, str):
        return None

    private, manifest = _private_and_manifest(slug)
    if not private:
        return None

    claims = ensure_optional_auth()
    if can_view_project(slug, manifest, claims):
        return None
    return project_locked_response(slug, claims)


def project_view_denied_reason(slug: str | None, claims: dict | None) -> str | None:
    """``LOCKED_ERROR_CODE`` when this caller may not view ``slug``, else None.

    The response-free sibling of :func:`check_project_access`, for callers that
    cannot answer with one: the WebSocket channels in
    ``routes/core/websocket.py`` run after the connection has been upgraded, so
    a Flask 403 has nowhere to go. Claims are passed in rather than resolved
    here because those callers resolve identity their own way
    (``middleware.auth.resolve_ws_claims`` reads the ``?token=`` query parameter
    a browser must use on a handshake).

    It resolves privacy through exactly the same ``_private_and_manifest`` +
    :func:`can_view_project` path the HTTP gate uses, so the two cannot answer
    differently for the same slug and identity. An unknown slug is reported
    viewable, matching :func:`check_project_access`: privacy is not where a
    not-found is invented.
    """
    if not slug or not isinstance(slug, str):
        return None

    private, manifest = _private_and_manifest(slug)
    if not private:
        return None
    if can_view_project(slug, manifest, claims):
        return None
    return LOCKED_ERROR_CODE


def require_project_access(fn):
    """Decorator for routes with a ``<slug>`` path parameter.

    Apply it closest to the view function, below any auth decorator the route
    already has, so the claims those populate are reused rather than the token
    being decoded twice::

        @bp.route("/api/projects/<slug>/thing")
        @require_valid_slug
        @require_tier("pro")
        @require_project_access
        def thing(slug):
            ...
    """
    @functools.wraps(fn)
    def wrapper(*args, slug: str, **kwargs):
        denied = check_project_access(slug)
        if denied is not None:
            return denied
        return fn(*args, slug=slug, **kwargs)
    return wrapper


def filter_visible_projects(projects: list[dict]) -> tuple[list[dict], bool]:
    """Drop private projects this caller may not view.

    Returns ``(visible, any_private)``. The flag matters as much as the list:
    once the response depends on who is asking it must not sit in a shared
    cache, and the discovery route's ``public, max-age=300`` would do exactly
    that.
    """
    visible: list[dict] = []
    any_private = False
    claims_loaded = False
    claims = None

    for project in projects:
        slug = project.get("slug", "")
        if not slug:
            visible.append(project)
            continue

        private, manifest = _private_and_manifest(slug)
        if not private:
            visible.append(project)
            continue

        any_private = True
        if not claims_loaded:
            claims = ensure_optional_auth()
            claims_loaded = True
        if can_view_project(slug, manifest, claims):
            visible.append(project)

    return visible, any_private


# ──────────────────────────────────────────────
# Render artifacts served from /static
# ──────────────────────────────────────────────


def artifact_slug_candidates(filename: str) -> list[str]:
    """Every project slug a render artifact filename could belong to.

    Artifacts are named ``<slug>_preview_<part>.<fmt>`` (see
    ``render_orchestrator`` and ``Config.STL_PREFIX``). A slug may itself
    contain the ``_preview_`` marker, and so may a part id, so the split point
    is genuinely ambiguous — every candidate that is a well-formed slug is
    returned and the caller checks them all. Guessing one and getting it wrong
    would serve a private project's geometry.

    A name with no usable marker yields nothing, which keeps unrelated static
    files behaving exactly as they do today.
    """
    name = filename.rsplit("/", 1)[-1]
    marker = f"_{Config.STL_PREFIX}"
    candidates: list[str] = []
    idx = name.find(marker)
    while idx > 0:
        candidate = name[:idx]
        if validate_project_slug(candidate) is None:
            candidates.append(candidate)
        idx = name.find(marker, idx + 1)
    return candidates


def is_private_artifact(filename: str) -> bool:
    """Whether this static file is a render artifact of a private project.

    Drives cache headers: a public project's preview stays browser-cacheable
    exactly as before, while a private one must never be stored.
    """
    return any(
        _private_and_manifest(slug)[0]
        for slug in artifact_slug_candidates(filename)
    )


def check_static_artifact_access(filename: str):
    """Locked response when ``filename`` is a private project's render artifact.

    ``/static`` serves rendered geometry under a name that carries the slug, so
    gating the render endpoint alone would leave the output of the last render
    readable by anyone who could guess the file name.
    """
    for slug in artifact_slug_candidates(filename):
        denied = check_project_access(slug)
        if denied is not None:
            return denied
    return None
