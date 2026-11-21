"""Free-tier quota for re-rendering Commons cartridges with the B-Rep engines.

Owner decision 2026-11-20: guest and essentials may re-render a **Commons**
cartridge whose mode needs the CadQuery or graph engine, under a quota, so the
landing's "customise any cartridge for free" is true. 484 of the 512 Commons
cartridges need one of those engines for every mode; before this, a free
visitor saw only the prerendered default.

What is opened, and nothing more:

- the ``cadquery`` and ``graph`` engines, for a cartridge in the public Commons
  root (``Config.PROJECTS_DIR``) that is not user-authored — never a private
  cartridge, a fork, an import or anything else in the user-projects root;
- only through ``/api/render`` and ``/api/render-stream``, the routes that
  re-render a cartridge with the caller's parameters. Every other caller of
  ``resolve_engine_config`` (HEAD renders, animation flipbooks) still answers
  403, and the export-format gate still runs first, so STEP stays Pro.

The tiers.json key is ``commons_brep_renders_per_day``. A tier that has the
engine flag (pro, premium) never reaches this module. ``0`` or a missing key
keeps the old 403.

Three bounds, all in the store the rate limiter already uses (flask-limiter's
``limits`` strategy over ``RATE_LIMIT_STORAGE``, Redis in production) plus the
render Redis for the concurrency slot:

1. **Per identity, per day** — ``commons_brep_renders_per_day`` from the tier,
   keyed by user id when signed in and by client IP otherwise. One unit is one
   render request that has at least one part to compute. A request every part
   of which is already in the render cache (or a static part) is served without
   touching the quota.
2. **All free tiers together, per hour** — ``COMMONS_FREE_RENDERS_PER_HOUR``
   (default 30), so anonymous traffic from many addresses cannot take the
   single render worker for the whole hour.
3. **At most N at once** — ``COMMONS_FREE_RENDER_MAX_CONCURRENT`` (default 1)
   leases in Redis. A free B-Rep render holds a gunicorn worker for as long as
   it waits on the render worker, and the API runs four; this keeps free
   traffic to one of them.

A request refused by (2) or (3) is not counted against (1).

Why these numbers (tiers.json cannot carry comments, so the reasons live here
and in docs/guides/rate-limiting.md):

- guest 3/day — anonymous and keyed only by address. Production runs ONE
  render worker container with a 1-CPU limit; a cold CadQuery part takes from
  seconds to a few minutes (RENDER_TIMEOUT_S 300 is the ceiling). Three is
  enough to see that "customise" is real, and small enough that the next step
  is a free account.
- essentials 10/day — a signed-in account, keyed by user id, so it is not
  multiplied by changing address. Enough for one real customisation session;
  Pro's 150 renders/hour with the engine outright stays the paid path.
- pro, premium -1 — they hold the engine flag and never reach this module;
  -1 only states that no quota applies.
- 30/hour across all free tiers — at a one-minute average render that is at
  most half of the worker's hour, leaving the rest for paying users.
- 1 at a time — the API runs 4 gunicorn sync workers and a streaming render
  holds one for its whole wait; free renders may hold at most one of them.

Enforcement follows the rate limiter's own switch (``RATE_LIMIT_ENABLED``,
off under ``FLASK_DEBUG``): with rate limiting off nothing here is enforced,
exactly as the hourly render bucket is not.
"""
from __future__ import annotations

import logging
import math
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from flask import Response, request
from limits import parse as parse_limit

from config import Config
from services.core.tier_service import check_feature, get_tier_limits, is_unlimited
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)

#: tiers.json key: B-Rep re-renders of Commons cartridges per identity per day.
QUOTA_KEY = "commons_brep_renders_per_day"

#: Window of the per-identity quota. A `limits` granularity string; tests
#: shorten it to watch a reset happen.
QUOTA_WINDOW = "1 day"
QUOTA_WINDOW_NAME = "day"

#: Engine -> the tiers.json feature flag that grants it outright.
METERED_ENGINES = {"cadquery": "cadquery_engine", "graph": "graph_engine"}
ENGINE_LABELS = {"cadquery": "CadQuery", "graph": "graph"}

#: Set on the render payload by `resolve_engine_config` when the render may go
#: ahead only under this quota.
METERED_FLAG = "commons_quota_metered"

#: Stable error codes the Studio branches on. Do not rename.
QUOTA_EXHAUSTED_CODE = "commons_render_quota_exhausted"
CAPACITY_EXHAUSTED_CODE = "commons_render_capacity_exhausted"
BUSY_CODE = "commons_render_busy"

GLOBAL_HOURLY_ENV = "COMMONS_FREE_RENDERS_PER_HOUR"
DEFAULT_GLOBAL_HOURLY = 30
MAX_CONCURRENT_ENV = "COMMONS_FREE_RENDER_MAX_CONCURRENT"
DEFAULT_MAX_CONCURRENT = 1

SLOT_KEY_PREFIX = "yantra_commons_free_render_slot:"
#: What a "busy" answer tells the client to wait. Not a promise, a pacing hint.
BUSY_RETRY_AFTER_SECONDS = 30
#: Lease slack on top of the per-part wait ceilings, so a lease outlives the
#: render it covers and expires on its own if the API process dies mid-render.
SLOT_LEASE_GRACE_SECONDS = 60

_NAMESPACE = "commons_brep"


# ──────────────────────────────────────────────
# Which renders are metered
# ──────────────────────────────────────────────

def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is not an integer; using %d", name, raw, default)
        return default
    return value if value >= 0 else default


def quota_limit(tier: str) -> int:
    """The tier's daily Commons B-Rep quota (-1 unlimited, 0 none)."""
    value = get_tier_limits(tier).get(QUOTA_KEY, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _within(path: Path, root) -> bool:
    if root is None:
        return False
    try:
        root = Path(root).resolve()
    except OSError:
        return False
    return path == root or root in path.parents


def is_commons_cartridge(manifest) -> bool:
    """Whether ``manifest`` is a cartridge of the public Commons.

    Under ``Config.PROJECTS_DIR``, not under the private or user roots (which
    could be configured inside it), and not user-authored (a ``fork``/``github``
    source). Anything unknown — no ``project_dir``, an unreadable path — is not
    Commons: the stricter answer.
    """
    project_dir = getattr(manifest, "project_dir", None)
    if project_dir is None:
        return False
    try:
        resolved = Path(project_dir).resolve()
        if not _within(resolved, Config.PROJECTS_DIR):
            return False
        commons_root = Path(Config.PROJECTS_DIR).resolve()
        for other in (getattr(Config, "PRIVATE_PROJECTS_DIR", None),
                      getattr(Config, "USER_PROJECTS_DIR", None)):
            if other is None:
                continue
            # A deployment that points another root AT the commons cannot tell
            # them apart: nothing there is treated as Commons.
            if Path(other).resolve() == commons_root or _within(resolved, other):
                return False
        return not bool(getattr(manifest, "user_authored", True))
    except Exception:  # pragma: no cover - defensive: unknown is not Commons
        logger.debug("Commons check failed for %r", project_dir, exc_info=True)
        return False


def metered_access(tier: str, engine: str, manifest) -> bool:
    """True when ``tier`` may run ``engine`` on ``manifest`` only under this quota."""
    feature = METERED_ENGINES.get(engine)
    if feature is None or check_feature(tier, feature):
        return False
    return quota_limit(tier) != 0 and is_commons_cartridge(manifest)


# ──────────────────────────────────────────────
# Identity and storage
# ──────────────────────────────────────────────

def client_ip() -> str:
    """The visitor's address for the guest quota.

    Public traffic reaches the API through the Cloudflare tunnel, so
    ``remote_addr`` is the tunnel's address for every visitor; Cloudflare's
    ``CF-Connecting-IP`` is the visitor. Cloudflare overwrites that header at
    the edge, so a visitor cannot choose it; only an in-cluster caller (which
    is trusted anyway) could. Without it — local, tests, in-cluster — the
    socket address is used.
    """
    forwarded = (request.headers.get("CF-Connecting-IP") or "").strip()
    return forwarded or (request.remote_addr or "unknown")


def quota_identity() -> str:
    claims = getattr(request, "auth_claims", None)
    if isinstance(claims, dict) and claims.get("sub"):
        return f"user:{claims['sub']}"
    return f"ip:{client_ip()}"


def enforcement_enabled() -> bool:
    from extensions import limiter
    return bool(limiter.enabled)


def _strategy():
    """The rate limiter's own strategy object, over its configured storage."""
    from extensions import limiter
    return limiter.limiter


def _redis():
    from services.engine import render_orchestrator
    return render_orchestrator.r


def _quota_item(limit: int):
    return parse_limit(f"{limit} per {QUOTA_WINDOW}")


def _global_item():
    hourly = _int_env(GLOBAL_HOURLY_ENV, DEFAULT_GLOBAL_HOURLY)
    return parse_limit(f"{hourly} per 1 hour") if hourly > 0 else None


def _window(item, *identifiers) -> tuple[int, int]:
    """(remaining, reset_epoch_seconds) for ``item`` under ``identifiers``."""
    stats = _strategy().get_window_stats(item, *identifiers)
    return int(stats.remaining), math.ceil(stats.reset_time)


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


def _retry_after(reset_epoch: int) -> int:
    return max(1, int(reset_epoch - time.time()))


def _refusal(message: str, status: int, code: str, retry_after: int, extra: dict):
    body, status = error_response(message, status, error_code=code,
                                  extra={**extra, "retry_after_seconds": retry_after})
    body.headers["Retry-After"] = str(retry_after)
    return body, status


def _quota_body(limit: int, remaining: int, reset_epoch: int) -> dict:
    return {
        "scope": "commons_brep",
        "limit": limit,
        "remaining": max(0, remaining),
        "window": QUOTA_WINDOW_NAME,
        "reset_at": _iso(reset_epoch),
    }


# ──────────────────────────────────────────────
# Admission
# ──────────────────────────────────────────────

class MeteredRender:
    """An admitted metered render: holds its concurrency lease until released."""

    def __init__(self, slot_key: str | None = None, token: str | None = None,
                 headers: dict | None = None):
        self.slot_key = slot_key
        self.token = token
        self.headers = headers or {}
        self._released = False

    def release(self) -> None:
        if self._released or not self.slot_key:
            self._released = True
            return
        self._released = True
        try:
            r = _redis()
            if r.get(self.slot_key) == self.token:
                r.delete(self.slot_key)
        except Exception:
            # The lease expires on its own; a missed release only delays the
            # next free render by at most the lease.
            logger.warning("Could not release free render slot %s", self.slot_key, exc_info=True)

    def apply_headers(self, response) -> None:
        for key, value in self.headers.items():
            response.headers[key] = value

    def wrap_stream(self, events):
        """Yield ``events`` and release the lease when the stream ends or is dropped."""
        try:
            yield from events
        finally:
            self.release()


def _slot_lease_seconds(payload: dict) -> int:
    from services.engine.render_orchestrator import (
        RENDER_PART_WAIT_TIMEOUT_SECONDS,
        RENDER_STREAM_PART_TIMEOUT_SECONDS,
    )
    parts = max(1, len(payload.get("parts") or []))
    per_part = max(RENDER_PART_WAIT_TIMEOUT_SECONDS, RENDER_STREAM_PART_TIMEOUT_SECONDS)
    return parts * per_part + SLOT_LEASE_GRACE_SECONDS


def _acquire_slot(payload: dict) -> tuple[str, str] | None:
    """Take one of the free-render leases, or None when all are held."""
    slots = _int_env(MAX_CONCURRENT_ENV, DEFAULT_MAX_CONCURRENT) or DEFAULT_MAX_CONCURRENT
    token = uuid.uuid4().hex
    ttl = _slot_lease_seconds(payload)
    r = _redis()
    for index in range(slots):
        key = f"{SLOT_KEY_PREFIX}{index}"
        if r.set(key, token, nx=True, ex=ttl):
            return key, token
    return None


def admit_metered_render(tier: str, engine: str, payload: dict):
    """Decide whether a metered render may run now.

    Returns ``(MeteredRender, None)`` to go ahead — call ``release()`` when the
    render is over — or ``(None, response)`` to answer with.
    """
    from services.engine.render_orchestrator import all_parts_served_without_render

    if not enforcement_enabled():
        return MeteredRender(), None

    if all_parts_served_without_render(payload):
        # The cache already holds every part: nothing is computed, so nothing
        # is counted and no lease is needed.
        return MeteredRender(headers={"X-Commons-Render-Cache": "HIT"}), None

    label = ENGINE_LABELS.get(engine, engine)
    limit = quota_limit(tier)
    identity = quota_identity()
    item = None if is_unlimited(limit) else _quota_item(limit)
    strategy = _strategy()

    if item is not None and not strategy.test(item, _NAMESPACE, identity):
        _remaining, reset = _window(item, _NAMESPACE, identity)
        retry = _retry_after(reset)
        return None, _refusal(
            f"You have used all {limit} free {label} re-renders of Commons cartridges "
            f"for today. The quota resets at {_iso(reset)}. Pro renders with the "
            f"{label} engine without this quota.",
            429, QUOTA_EXHAUSTED_CODE, retry,
            {"quota": _quota_body(limit, 0, reset), "tier": tier, "engine": engine},
        )

    global_item = _global_item()
    if global_item is not None and not strategy.test(global_item, _NAMESPACE, "global"):
        _remaining, reset = _window(global_item, _NAMESPACE, "global")
        retry = _retry_after(reset)
        return None, _refusal(
            f"Free {label} rendering has reached its capacity for this hour. Try again "
            f"after {_iso(reset)}. Nothing was counted against your quota.",
            503, CAPACITY_EXHAUSTED_CODE, retry, {"tier": tier, "engine": engine},
        )

    try:
        slot = _acquire_slot(payload)
    except Exception:
        logger.warning("Free render slot store unavailable; refusing the free render", exc_info=True)
        slot = None
    if slot is None:
        return None, _refusal(
            f"Another free {label} render is running. Try again in about "
            f"{BUSY_RETRY_AFTER_SECONDS} seconds. Nothing was counted against your quota.",
            503, BUSY_CODE, BUSY_RETRY_AFTER_SECONDS, {"tier": tier, "engine": engine},
        )

    grant = MeteredRender(*slot)
    # Under the lease, so concurrent free renders cannot both pass `test` and
    # overshoot; a lost race is answered like an exhausted quota.
    if global_item is not None:
        strategy.hit(global_item, _NAMESPACE, "global")
    if item is None:
        grant.headers = {"X-Commons-Render-Limit": "unlimited"}
        return grant, None
    if not strategy.hit(item, _NAMESPACE, identity):
        grant.release()
        _remaining, reset = _window(item, _NAMESPACE, identity)
        retry = _retry_after(reset)
        return None, _refusal(
            f"You have used all {limit} free {label} re-renders of Commons cartridges "
            f"for today. The quota resets at {_iso(reset)}.",
            429, QUOTA_EXHAUSTED_CODE, retry,
            {"quota": _quota_body(limit, 0, reset), "tier": tier, "engine": engine},
        )
    remaining, reset = _window(item, _NAMESPACE, identity)
    grant.headers = {
        "X-Commons-Render-Limit": str(limit),
        "X-Commons-Render-Remaining": str(max(0, remaining)),
        "X-Commons-Render-Reset": str(reset),
    }
    return grant, None


def streaming_response(grant: MeteredRender | None, events, **kwargs) -> Response:
    """An SSE ``Response`` that releases ``grant`` when the stream ends."""
    body = grant.wrap_stream(events) if grant is not None else events
    resp = Response(body, **kwargs)
    if grant is not None:
        grant.apply_headers(resp)
    return resp
