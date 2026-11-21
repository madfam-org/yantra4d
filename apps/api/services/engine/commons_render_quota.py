"""Free-tier quota for re-rendering Commons cartridges with the B-Rep engines.

Owner decision 2026-11-20: guest and essentials may re-render a **Commons**
cartridge whose mode needs the CadQuery or graph engine, under a quota, so the
landing's "customise any cartridge for free" is true. 484 of the 512 Commons
cartridges need one of those engines for every mode; before this, a free
visitor saw only the prerendered default.

What is opened, and nothing more:

- the ``cadquery`` and ``graph`` engines, for a cartridge in the public Commons
  root (``Config.PROJECTS_DIR``) that is neither user-authored nor private —
  never a private cartridge (configured or ``access_control.view: private``),
  a fork, an import or anything else in the user-projects root;
- only through ``/api/render`` and ``/api/render-stream``, the routes that
  re-render a cartridge with the caller's parameters. Every other caller of
  ``resolve_engine_config`` (HEAD renders, animation flipbooks) still answers
  403, and the export-format gate still runs first, so STEP stays Pro.

The tiers.json key is ``commons_brep_renders_per_day``. A tier that has the
engine flag (pro, premium) never reaches this module. ``0`` or a missing key
keeps the old 403.

Bounds. The counters and the lease live in the render Redis (the store the
render queue already needs; a free render cannot run without it), as small
fixed-window counters updated by Lua so a charge and its expiry are atomic and
a charge can be refunded:

1. **Per identity, per day** — ``commons_brep_renders_per_day`` from the tier,
   keyed by user id when signed in and by ``utils.client_ip`` otherwise
   (IPv6 by /64; a visitor holding many prefixes gets one quota per prefix,
   and it is the global budget in (2) that bounds them). One
   unit is one render request with at least one part to compute. A request
   whose parts are all static or already in the render cache is served without
   touching the quota. Only a failure of OUR infrastructure is refunded: no
   live worker to hand a part to, or one of ``INFRA_EXCEPTIONS`` (OSError, a
   Redis error) during the render. A timeout, a script error or a partial
   render is not: the visitor's own parameters can cause those. Some charged
   outcomes are ours, and are deliberately NOT refunded rather than guessed
   at from heartbeats: a worker that crashes mid-part, and time spent queued
   behind Pro renders, both surface as a timeout; an operator's cancel-all
   surfaces as a cancellation; gunicorn killing a slow request (SystemExit)
   is a failed render. Outcomes come from the render loop's structured
   ``RenderStatus``, never from log text, which echoes the visitor's
   parameters.
2. **Worker time for all free tiers together, per hour** —
   ``COMMONS_FREE_RENDER_PARTS_PER_HOUR`` (default 30) cold PARTS, charged per
   part the worker will compute, so a many-part mode costs what it uses. Never
   refunded: it measures worker time spent, and failed work spent it too.
3. **At most N at once** — ``COMMONS_FREE_RENDER_MAX_CONCURRENT`` (default 1)
   leases. A live lease lasts ``LIVE_LEASE_SECONDS`` (60) and the render wait
   loops refresh it (compare-and-swap) as they tick, so a lease whose API
   process died frees itself within a minute. A metered render never waits
   longer than ``METERED_MAX_WAIT_SECONDS`` (270, below gunicorn's 300 s
   timeout) in total. A free render holds its lease while the API waits on it, and then,
   if it ended early (timeout, disconnect, error), its jobs are cancelled — the
   queued ones removed, the running one told to stop through the per-job
   cancel key the worker polls — and the lease is held in a *draining* state
   until the worker no longer holds any job of that request (checked on the
   next admission) or the job lease (``ACTIVE_JOB_META_TTL``) runs out. So a
   free render's worker time is bounded by the worker's own timeout, and the
   next free render does not start until the last one has stopped.

Before charging anything, admission checks that the render worker is up; a
render that could only fail is answered 503 ``render_worker_unavailable``
without spending the quota. A request refused by (2) or (3) is not counted
against (1).

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
- 30 cold parts/hour across all free tiers — at a one-minute average part that
  is at most half of the worker's hour, leaving the rest for paying users.
- 1 at a time — the API runs 4 gunicorn sync workers and a streaming render
  holds one for its whole wait; free renders may hold at most one of them.

Enforcement follows the rate limiter's own switch (``RATE_LIMIT_ENABLED``,
off under ``FLASK_DEBUG``): with rate limiting off nothing here is enforced,
exactly as the hourly render bucket is not.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import redis
from flask import Response, g, has_request_context, request

from config import Config
from services.core.tier_service import check_feature, get_tier_limits, is_unlimited
from utils.client_ip import client_ip
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)

#: tiers.json key: B-Rep re-renders of Commons cartridges per identity per day.
QUOTA_KEY = "commons_brep_renders_per_day"

#: Per-identity window. Tests shorten it to watch a reset happen.
QUOTA_WINDOW_SECONDS = 86400
QUOTA_WINDOW_NAME = "day"
GLOBAL_WINDOW_SECONDS = 3600

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
WORKER_UNAVAILABLE_CODE = "render_worker_unavailable"

GLOBAL_PARTS_ENV = "COMMONS_FREE_RENDER_PARTS_PER_HOUR"
DEFAULT_GLOBAL_PARTS = 30
MAX_CONCURRENT_ENV = "COMMONS_FREE_RENDER_MAX_CONCURRENT"
DEFAULT_MAX_CONCURRENT = 1

QUOTA_KEY_PREFIX = "yantra_commons_quota:"
GLOBAL_KEY = "yantra_commons_free_parts:global"
SLOT_KEY_PREFIX = "yantra_commons_free_render_slot:"
#: What a "busy" answer tells the client to wait. Not a promise, a pacing hint.
BUSY_RETRY_AFTER_SECONDS = 30
#: A live lease expires this long after its owner's last refresh, so a lease
#: whose API process died (pod roll, OOM kill) frees itself within a minute.
LIVE_LEASE_SECONDS = 60
#: How often the render wait loops refresh a live lease (they tick every
#: 0.2-1 s; one CAS per this many seconds is plenty).
LEASE_REFRESH_SECONDS = 10
#: Longest a metered render may wait on the worker, in total. Below gunicorn's
#: `--timeout 300` (apps/api/Dockerfile), so a slow free render is stopped and
#: settled by us — its job cancelled, its lease released — instead of its
#: gunicorn worker being killed mid-request.
METERED_MAX_WAIT_SECONDS = 270

#: Exceptions that mean OUR infrastructure failed, and so are refunded. Anything
#: else raised during a render — a bug, or gunicorn's SystemExit on its worker
#: timeout — settles as a failed render, not refunded.
INFRA_EXCEPTIONS = (OSError, redis.RedisError)

#: How a metered render ended, settled by `MeteredRender.finish`.
OUTCOME_OK = "ok"                # every part delivered
OUTCOME_INFRA = "infra_failure"  # our infrastructure failed (worker lost, OSError, Redis): refunded
OUTCOME_FAILED = "failed"        # the render itself failed or timed out: NOT refunded
OUTCOME_ABORTED = "aborted"      # cancelled or abandoned by the visitor: NOT refunded

# Charge ``cost`` against a fixed window unless it would pass ``limit``.
# Returns {admitted 0|1, used, ttl}. The expiry is set in the same step as the
# first increment, so a counter can never be left without one.
CHARGE_SCRIPT = """
local cost = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local window = tonumber(ARGV[3])
local used = tonumber(redis.call('GET', KEYS[1]) or '0')
local ttl = redis.call('TTL', KEYS[1])
if used + cost > limit then
  if ttl < 0 then ttl = window end
  return {0, used, ttl}
end
used = redis.call('INCRBY', KEYS[1], cost)
if ttl < 0 then
  redis.call('EXPIRE', KEYS[1], window)
  ttl = window
end
return {1, used, ttl}
"""

# Give back ``cost`` within the same window; never creates a counter.
REFUND_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
local left = redis.call('DECRBY', KEYS[1], tonumber(ARGV[1]))
if left <= 0 then redis.call('DEL', KEYS[1]) end
return left
"""

# Delete the lease only if it is still ours.
RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""

# Replace the lease value only if it is still what we read.
SWAP_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('SET', KEYS[1], ARGV[2], 'EX', tonumber(ARGV[3]))
  return 1
end
return 0
"""


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
    """Whether ``manifest`` is a public cartridge of the Commons.

    Under ``Config.PROJECTS_DIR``; not under the private or user roots (which
    could be configured inside it, or AT it); not user-authored (a
    ``fork``/``github`` source); and not private — neither listed as private
    by configuration nor marked ``access_control.view: private``. Anything
    unknown is not Commons: the stricter answer.
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
        if bool(getattr(manifest, "user_authored", True)):
            return False
        from services.core.project_access import is_private_project
        slug = getattr(manifest, "slug", None) or resolved.name
        return not is_private_project(slug, manifest)
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

def quota_identity() -> str:
    claims = getattr(request, "auth_claims", None)
    if isinstance(claims, dict) and claims.get("sub"):
        return f"user:{claims['sub']}"
    return f"ip:{client_ip()}"


def enforcement_enabled() -> bool:
    from extensions import limiter
    return bool(limiter.enabled)


def _redis():
    from services.engine import render_orchestrator
    return render_orchestrator.r


def _peek(key: str) -> tuple[int, int | None]:
    """(used, seconds_left or None) of a counter, without charging it."""
    r = _redis()
    used = int(r.get(key) or 0)
    ttl = r.ttl(key)
    return used, (ttl if isinstance(ttl, int) and ttl > 0 else None)


def _charge(key: str, cost: int, limit: int, window: int) -> tuple[bool, int, int]:
    admitted, used, ttl = _redis().eval(CHARGE_SCRIPT, 1, key, cost, limit, window)
    return bool(int(admitted)), int(used), int(ttl)


def _refund(key: str, cost: int) -> None:
    try:
        _redis().eval(REFUND_SCRIPT, 1, key, cost)
    except Exception:
        logger.warning("Could not refund %d unit(s) on %s", cost, key, exc_info=True)


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(int(epoch), tz=UTC).isoformat().replace("+00:00", "Z")


def _refusal(message: str, status: int, code: str, retry_after: int, extra: dict):
    body, status = error_response(message, status, error_code=code,
                                  extra={**extra, "retry_after_seconds": retry_after})
    body.headers["Retry-After"] = str(retry_after)
    return body, status


def _quota_body(limit: int, used: int, seconds_left: int) -> dict:
    return {
        "scope": "commons_brep",
        "limit": limit,
        "remaining": max(0, limit - used),
        "window": QUOTA_WINDOW_NAME,
        "reset_at": _iso(time.time() + seconds_left),
    }


def _exhausted(tier, engine, limit, used, seconds_left):
    label = ENGINE_LABELS.get(engine, engine)
    reset = _iso(time.time() + seconds_left)
    return _refusal(
        f"You have used all {limit} free {label} re-renders of Commons cartridges "
        f"for today. The quota resets at {reset}. Pro renders with the {label} "
        "engine without this quota.",
        429, QUOTA_EXHAUSTED_CODE, max(1, seconds_left),
        {"quota": _quota_body(limit, used, seconds_left), "tier": tier, "engine": engine},
    )


def _capacity(tier, engine, seconds_left):
    label = ENGINE_LABELS.get(engine, engine)
    return _refusal(
        f"Free {label} rendering has used its server time for this hour. Try again "
        f"after {_iso(time.time() + seconds_left)}. Nothing was counted against your quota.",
        503, CAPACITY_EXHAUSTED_CODE, max(1, seconds_left), {"tier": tier, "engine": engine},
    )


def _busy(tier, engine):
    label = ENGINE_LABELS.get(engine, engine)
    return _refusal(
        f"Another free {label} render is running. Try again in about "
        f"{BUSY_RETRY_AFTER_SECONDS} seconds. Nothing was counted against your quota.",
        503, BUSY_CODE, BUSY_RETRY_AFTER_SECONDS, {"tier": tier, "engine": engine},
    )


# ──────────────────────────────────────────────
# The lease
# ──────────────────────────────────────────────

def _lease_value(state: str, token: str, request_id: str) -> str:
    return f"{state}:{token}:{request_id}"


def _acquire_slot(payload: dict) -> tuple[str, str] | None:
    """Take a free-render lease, or None when every one is held.

    A lease left *draining* by an earlier render is taken over once the worker
    holds no job of that render any more.
    """
    from services.engine.render_orchestrator import request_has_pending_work

    slots = _int_env(MAX_CONCURRENT_ENV, DEFAULT_MAX_CONCURRENT) or DEFAULT_MAX_CONCURRENT
    value = _lease_value("live", uuid.uuid4().hex, str(payload.get("request_id") or ""))
    ttl = LIVE_LEASE_SECONDS
    r = _redis()
    for index in range(slots):
        key = f"{SLOT_KEY_PREFIX}{index}"
        if r.set(key, value, nx=True, ex=ttl):
            return key, value
        current = r.get(key)
        if isinstance(current, str) and current.startswith("drain:"):
            drained_request = current.split(":", 2)[2]
            if not request_has_pending_work(drained_request) and \
                    r.eval(SWAP_SCRIPT, 1, key, current, value, ttl):
                return key, value
    return None


# ──────────────────────────────────────────────
# Admission and settlement
# ──────────────────────────────────────────────

def outcome_of(status) -> str:
    """Settle from the render loop's own record (orchestrator.RenderStatus).

    Only a failure of OUR infrastructure is refunded. A timeout or a script
    error can be caused by the visitor's own parameters, and refunding those
    would let one visitor keep the free worker busy at no cost.
    """
    if status.worker_lost:
        return OUTCOME_INFRA
    if status.cancelled:
        return OUTCOME_ABORTED
    if status.timed_out or status.errored_parts or not status.finished:
        return OUTCOME_FAILED
    return OUTCOME_OK


class MeteredRender:
    """An admitted metered render, settled exactly once by ``finish``.

    The routes hand ``status``, ``refresh`` and ``deadline`` to the render
    loop: it records what happened in ``status``, calls ``refresh`` on every
    wait tick (keeping the live lease alive), and never waits past
    ``deadline``.
    """

    def __init__(self, *, slot_key: str | None = None, lease: str | None = None,
                 request_id: str | None = None, identity_key: str | None = None,
                 headers: dict | None = None):
        from services.engine.render_orchestrator import RenderStatus

        self.slot_key = slot_key
        self.lease = lease
        self.request_id = request_id
        self.identity_key = identity_key
        self.headers = headers or {}
        self.status = RenderStatus()
        started = getattr(g, "request_started_at", None) if has_request_context() else None
        # Measured from when the request ARRIVED (middleware/request_id.py),
        # since gunicorn's timeout counts from there too.
        self.deadline = (started or time.time()) + METERED_MAX_WAIT_SECONDS
        self._last_refresh = time.time()
        self._finished = False

    def refresh(self) -> None:
        """Extend the live lease (compare-and-swap); called from the wait loops."""
        if self.slot_key is None or self._finished:
            return
        now = time.time()
        if now - self._last_refresh < LEASE_REFRESH_SECONDS:
            return
        self._last_refresh = now
        try:
            if not _redis().eval(SWAP_SCRIPT, 1, self.slot_key, self.lease, self.lease, LIVE_LEASE_SECONDS):
                logger.warning("Free render lease %s was lost while rendering", self.slot_key)
        except Exception:
            logger.warning("Could not refresh free render lease %s", self.slot_key, exc_info=True)

    def finish(self, outcome: str) -> None:
        """Settle the render: refund, cancel leftover jobs, release or drain the lease."""
        if self._finished:
            return
        self._finished = True
        if self.slot_key is None:
            return  # nothing was charged or leased (cache hit, enforcement off)
        from services.engine.render_orchestrator import (
            ACTIVE_JOB_META_TTL,
            cancel_request,
            request_has_pending_work,
        )

        if outcome != OUTCOME_OK and self.request_id:
            try:
                # Queued parts are removed; the running one gets the per-job
                # cancel key the worker polls; unqueued parts never start.
                cancel_request(self.request_id)
            except Exception:
                logger.warning("Could not cancel leftover jobs of %s", self.request_id, exc_info=True)
        if outcome == OUTCOME_INFRA and self.identity_key:
            _refund(self.identity_key, 1)

        try:
            r = _redis()
            if outcome != OUTCOME_OK and request_has_pending_work(self.request_id):
                # The worker is still stopping: keep the next free render out
                # until it has, or until the job lease would have expired.
                draining = "drain:" + self.lease.split(":", 1)[1]
                r.eval(SWAP_SCRIPT, 1, self.slot_key, self.lease, draining, ACTIVE_JOB_META_TTL)
            else:
                r.eval(RELEASE_SCRIPT, 1, self.slot_key, self.lease)
        except Exception:
            # The lease expires on its own; a missed release only delays the
            # next free render by at most the lease.
            logger.warning("Could not release free render lease %s", self.slot_key, exc_info=True)

    def apply_headers(self, response) -> None:
        for key, value in self.headers.items():
            response.headers[key] = value

    def wrap_stream(self, events):
        """Yield ``events``; settle from ``status`` when they end.

        A client that goes away (GeneratorExit) is an abort; one of OUR
        exceptions (``INFRA_EXCEPTIONS``) is an infrastructure failure; any
        other exception, or SystemExit/KeyboardInterrupt (gunicorn's worker
        timeout), is a failed render and is not refunded.
        """
        outcome = OUTCOME_ABORTED
        try:
            yield from events
            outcome = outcome_of(self.status)
        except GeneratorExit:
            outcome = OUTCOME_ABORTED
            raise
        except INFRA_EXCEPTIONS:
            outcome = OUTCOME_INFRA
            raise
        except BaseException:
            outcome = OUTCOME_FAILED
            raise
        finally:
            self.finish(outcome)


def admit_metered_render(tier: str, engine: str, payload: dict):
    """Decide whether a metered render may run now.

    Returns ``(MeteredRender, None)`` to go ahead — the route passes the
    grant's ``status``/``refresh``/``deadline`` to the render loop and calls
    ``finish(outcome_of(grant.status))`` when it is over — or
    ``(None, response)``.
    """
    from services.engine.render_orchestrator import cold_part_count, is_render_worker_available

    if not enforcement_enabled():
        return MeteredRender(), None

    cold = cold_part_count(payload)
    if cold == 0:
        # The cache already holds every part: nothing is computed, so nothing
        # is counted and no lease is needed.
        return MeteredRender(headers={"X-Commons-Render-Cache": "HIT"}), None

    if not is_render_worker_available():
        return None, error_response(
            "Render worker unavailable or not healthy", 503, error_code=WORKER_UNAVAILABLE_CODE,
        )

    limit = quota_limit(tier)
    identity_key = None if is_unlimited(limit) else f"{QUOTA_KEY_PREFIX}{quota_identity()}"
    budget = _int_env(GLOBAL_PARTS_ENV, DEFAULT_GLOBAL_PARTS)

    try:
        if identity_key is not None:
            used, left = _peek(identity_key)
            if used >= limit:
                return None, _exhausted(tier, engine, limit, used, left or QUOTA_WINDOW_SECONDS)
        if budget > 0:
            used, left = _peek(GLOBAL_KEY)
            if used + cold > budget:
                return None, _capacity(tier, engine, left or GLOBAL_WINDOW_SECONDS)
        slot = _acquire_slot(payload)
    except Exception:
        logger.warning("Free render store unavailable; refusing the free render", exc_info=True)
        return None, _busy(tier, engine)
    if slot is None:
        return None, _busy(tier, engine)

    grant = MeteredRender(slot_key=slot[0], lease=slot[1],
                          request_id=str(payload.get("request_id") or ""))
    global_charged = 0
    try:
        # Charged under the lease, so concurrent free renders cannot both pass
        # the peeks above and overshoot.
        if budget > 0:
            admitted, _used, left = _charge(GLOBAL_KEY, cold, budget, GLOBAL_WINDOW_SECONDS)
            if not admitted:
                grant.finish(OUTCOME_OK)
                return None, _capacity(tier, engine, left)
            global_charged = cold
        if identity_key is None:
            grant.headers = {"X-Commons-Render-Limit": "unlimited"}
            return grant, None
        admitted, used, left = _charge(identity_key, 1, limit, QUOTA_WINDOW_SECONDS)
        if not admitted:
            if budget > 0:
                _refund(GLOBAL_KEY, cold)  # nothing will be computed after all
            grant.finish(OUTCOME_OK)
            return None, _exhausted(tier, engine, limit, used, left)
    except Exception:
        logger.warning("Free render charge failed; refusing the free render", exc_info=True)
        if global_charged:
            _refund(GLOBAL_KEY, global_charged)  # nothing will be computed
        grant.finish(OUTCOME_OK)
        return None, _busy(tier, engine)

    grant.identity_key = identity_key
    grant.headers = {
        "X-Commons-Render-Limit": str(limit),
        "X-Commons-Render-Remaining": str(max(0, limit - used)),
        "X-Commons-Render-Reset": str(int(time.time() + left)),
    }
    return grant, None


def streaming_response(grant: MeteredRender, events, **kwargs) -> Response:
    """An SSE ``Response`` that settles ``grant`` when the stream ends.

    ``call_on_close`` covers a response that is closed without ever being
    iterated, which never runs the generator's ``finally``.
    """
    resp = Response(grant.wrap_stream(events), **kwargs)
    resp.call_on_close(lambda: grant.finish(OUTCOME_ABORTED))
    grant.apply_headers(resp)
    return resp
