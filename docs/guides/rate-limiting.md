# Rate Limiting

Yantra4D uses Flask-Limiter to protect API endpoints from abuse. Limits are tiered by user subscription and can use either in-memory or Redis storage backends.

## How It Works

### Key Function

Rate limits are tracked per-user (authenticated) or per-IP (anonymous):

- **Authenticated**: Key is `user:{sub}` from JWT claims
- **Anonymous**: Key is `ip:{client_ip}` — Cloudflare's `CF-Connecting-IP` when valid, else the socket address; IPv6 by /64 (`apps/api/utils/client_ip.py`)

Defined in `apps/api/extensions.py` via `tiered_rate_key()`.

### Storage Backends

| Backend | Env Var | Behavior |
|---------|---------|----------|
| Memory (default) | `RATE_LIMIT_STORAGE=memory://` | Per-process counters. **Not shared across Gunicorn workers.** Adequate for single-worker dev. |
| Redis | `RATE_LIMIT_STORAGE=redis://host:6379` | Shared counters across all workers. **Required for production.** Falls back to `REDIS_URL` if `RATE_LIMIT_STORAGE` is not set. |

### Enable/Disable

- **Dev mode** (`FLASK_DEBUG=true`): Rate limiting is **disabled** by default
- **Production** (`FLASK_DEBUG=false`): Rate limiting is **enabled** by default
- Override: `RATE_LIMIT_ENABLED=true|false`

Response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) are always included when limiting is active.

## Browser renders are never rate limited

Rate limits exist to protect **our** CPU. A render that runs in the visitor's own
browser costs us nothing, so it is never counted, never limited, and never shows
a quota anywhere in the UI.

The studio renders in the browser **by default** (see
[`docs/guides/wasm-mode.md`](wasm-mode.md) for the full precedence table), which
means the common case consumes no quota at all. A render reaches
`/api/render-stream` — and therefore the limiter — only when the placement
decision says the browser cannot do the job, or when the visitor chooses
`Server` in the sidebar's placement control.

Two consequences worth stating plainly:

- The `X-RateLimit-*` headers, the `RateLimitBanner`, and the "N left this hour"
  half of the placement badge all describe **server** renders only. The browser
  badge deliberately carries no number: showing one would teach the visitor that
  everything they do is metered, which is the opposite of the truth.
- When a server render is refused with HTTP 429, the studio falls back to the
  browser automatically (unless the cartridge is hard-pinned to the server by its
  engine or `render.server_only`). Hitting the limit degrades the experience; it
  does not stop the work.

## Per-Tier Render Limits

Backend (server-side) render limits are defined per tier in `apps/api/tiers.json`. Browser (WASM) rendering is always unlimited.

| Tier | Backend Renders/Hour | AI Requests/Hour |
|------|:---:|:---:|
| guest | 10 | 0 |
| essentials | 30 | 20 |
| pro | 150 | 100 |
| premium | unlimited | unlimited |

Render limits are enforced dynamically in the render route via `tier_service.get_render_limit_for_project()`, which reads the user's tier from JWT claims and looks up `backend_renders_per_hour` in `tiers.json`.

### Per-Project Guest Override

Individual projects can declare `guest_render_limit` in their `project.json` manifest to override the guest tier limit. This is useful for client demos or featured projects that need higher render budgets without requiring sign-in.

```json
{
  "project": {
    "name": "My Demo Project",
    "guest_render_limit": 50
  }
}
```

The override only applies to the `guest` tier. Authenticated users always use their tier-based limit. If the override is missing, zero, negative, or non-integer, the standard guest limit (10/hr) applies.

## Free Commons re-renders with CadQuery and graph

Owner decision 2026-11-20: guest and essentials may re-render a **Commons**
cartridge whose mode needs the CadQuery or graph engine, under a daily quota.
484 of the 512 Commons cartridges need one of those engines for every mode, so
without this a free visitor could only look at the prerendered default.
Implementation: `apps/api/services/engine/commons_render_quota.py`.

| Tier | `commons_brep_renders_per_day` | Keyed by | Why |
|------|:---:|---|---|
| guest | 3 | client IP (`CF-Connecting-IP`, else the socket address) | Anonymous; one render worker with a 1-CPU limit, and a cold CadQuery part takes seconds to a few minutes. Enough to see that customising is real; the next step is a free account |
| essentials | 10 | user id | A signed-in account is not multiplied by changing address; enough for one customisation session |
| pro / premium | -1 | -- | They hold `cadquery_engine` / `graph_engine` outright and are never metered |

What counts: one render request (`/api/render` or `/api/render-stream`) that
has at least one part to compute. A request whose parts are all static parts
or render-cache hits (same cartridge, parameters and format) is served without
touching the quota; `ignore_cache: true` makes it a computed render. Only a
failure of **our infrastructure** is refunded: the worker lost mid-render, or
an exception on our side (OSError, Redis). A timeout, a CadQuery/script error
or a partial render is **not** refunded, because the visitor's own parameters
can cause them; neither is a render the visitor cancels or abandons. The
outcome is read from the render loop's structured status, never from the log
(the CadQuery runner echoes the visitor's parameters into it).

A render whose **engine process crashed** is given back too. "Crashed" means
every part that failed died of a crash signal (SIGSEGV, SIGBUS, SIGILL, SIGFPE
or SIGABRT), which the engine reads from the process's exit status and the
worker reports on the part's error event (`crash_signal`, worker to API only;
it is removed before the event reaches a client). A crash is presumed to be
ours: on 2026-11-21 an address-space ceiling set too low for the node made
every free render die with `Render failed with code -11`, and each one used up
one of the visitor's three renders. It is not always ours: a render that grows
past its address-space ceiling (`RENDER_RLIMIT_AS_MB`) usually dies of a crash
signal too, and slider values can cause that. The bound below is what makes
the presumption safe. A kill (SIGKILL: our timeout, a cancel, the OOM killer)
and the CPU-time limit (SIGXCPU) are not crashes and stay charged.

Crash refunds are bounded: at most the tier's daily quota of them per identity
per day (`yantra_commons_crash_refunds:<identity>`, a fixed window of its own
that starts with the first refund, as long as the quota's).
A visitor who finds parameters that crash the kernel therefore gets at most
twice the daily quota in worker runs, not an unmetered loop; without the bound
one address could spend the whole hourly budget below for everyone. The hourly
budget is never given back for a crash, since worker time was spent.

Some charged outcomes are ours, and are charged anyway rather than guessed at
from worker heartbeats: a render worker that crashes in the middle of a part,
and time a free render spends queued behind Pro renders, both show up as a
**timeout** (charged); a platform admin's cancel-all shows up as a
**cancellation** (charged); gunicorn killing a request that ran past
`--timeout` (a `SystemExit`) is a **failed render** (charged). A free render
waits at most 270 s from when its request arrived, and a part is never queued
once that time is up.
Before charging, admission checks the render worker's heartbeat: with no
worker the answer is 503 `render_worker_unavailable` and nothing is charged.
The hourly `backend_renders_per_hour` bucket still applies on top. The window
is fixed and starts at the first counted render, so it resets 24 hours later.

What is NOT opened: forks, GitHub imports, onboarded or AI-synthesised
cartridges (the user-projects root), private cartridges (the private root, the
configured private list, or `access_control.view: private`), HEAD renders,
animation flipbooks, STEP and every other format outside the tier's
`export_formats`, verification and geometry analysis, print dispatch. Those
still answer 403 exactly as before.

Burst bounds for free B-Rep renders, on top of the existing render timeout
(`RENDER_TIMEOUT_S`, 300 s per part), the per-render CPU/memory rlimits and the
single serial render worker:

| Bound | Default | Env | Refusal |
|---|:---:|---|---|
| Renders per identity per day | tier value | `tiers.json` | 429 `commons_render_quota_exhausted` |
| Computed PARTS across ALL free visitors per hour | 30 | `COMMONS_FREE_RENDER_PARTS_PER_HOUR` (0 disables) | 503 `commons_render_capacity_exhausted` |
| Free B-Rep renders in flight at once | 1 | `COMMONS_FREE_RENDER_MAX_CONCURRENT` | 503 `commons_render_busy` |

The hourly budget is charged per part the worker will compute (cache hits and
static parts excluded), so a six-part mode costs six; it is never refunded,
because it measures worker time and failed work spent it too.

The concurrency bound is a lease in the render Redis
(`yantra_commons_free_render_slot:<n>`). A live lease lasts 60 s and the render
wait loops refresh it (compare-and-swap) every 10 s, so a lease whose API
process died (pod roll, OOM kill) frees itself within a minute. A metered
render waits at most 270 s in total, below gunicorn's `--timeout 300`, so a
slow free render is stopped and settled by us rather than by gunicorn killing
its worker; a mode too slow to finish in that window completes over repeated
requests, because each finished part is cached. When a free render ends
early — a part times out, the visitor disconnects (the stream is closed or
never read), or the render errors — its jobs are cancelled (queued parts
removed, the running part told to stop through the per-job cancel key the
worker polls, a metered sync render stops queueing after its first timeout),
and if the worker still holds one of them the lease is kept in a *draining*
state until it does not (checked on the next admission) or until the job lease
(`ACTIVE_JOB_META_TTL`) runs out. The next free render therefore never starts
while a previous one is still using the worker. If the store is unreachable the
free render is refused (fail closed). A 503 refusal is not counted against the
daily quota.

The counters and the lease live in the render Redis (the store the render
queue already needs), as fixed-window counters updated by Lua so a charge and
its expiry are atomic and a charge can be refunded. They follow the rate
limiter's switch: with rate limiting off (`RATE_LIMIT_ENABLED=false`, or
`FLASK_DEBUG=true`) none of this is enforced.

**Anonymous keys.** Public traffic reaches the API through the Cloudflare
tunnel, so the socket address is the tunnel's for every visitor. Since this
change every anonymous key — the app-wide limiter (`extensions.tiered_rate_key`),
the hourly render bucket and this quota — uses `utils/client_ip.py`: the
`CF-Connecting-IP` header when it holds a valid address (Cloudflare overwrites
it at the edge), else the socket address; IPv6 is keyed by its /64 (one
subscriber normally holds a whole /64). A visitor with many IPv6 prefixes, or
many addresses, still gets one daily quota per prefix or address: what bounds
them is the global hourly budget of computed parts, shared by every free
visitor. Before it,
all anonymous visitors shared one bucket per limit. Trust boundary: an
in-cluster caller can set the header to anything; accepted because those
callers are our own services.

Error shape (429 shown; the 503s carry the same `error_code`,
`retry_after_seconds`, `tier` and `engine`, and no `quota`):

```json
{
  "status": "error",
  "error": "You have used all 3 free CadQuery re-renders of Commons cartridges for today. The quota resets at 2026-11-21T18:00:00Z. ...",
  "error_code": "commons_render_quota_exhausted",
  "quota": {"scope": "commons_brep", "limit": 3, "remaining": 0, "window": "day", "reset_at": "2026-11-21T18:00:00Z"},
  "retry_after_seconds": 7200,
  "tier": "guest",
  "engine": "cadquery",
  "request_id": "..."
}
```

Every refusal sets `Retry-After`; flask-limiter then rewrites that header to
the later of it and the route's own hourly window, so the body's
`retry_after_seconds` is the exact figure (the Studio reads the body). A counted render answers with
`X-Commons-Render-Limit`, `X-Commons-Render-Remaining` and
`X-Commons-Render-Reset` (epoch seconds); a render served from cache with
`X-Commons-Render-Cache: HIT`.

The Studio (`src/lib/engineGate.ts`, `src/lib/commonsQuota.ts`,
`useRender`) lets a metered mode through to an explicit Generate, never spends
the quota on an automatic render (it says "press Generate" instead). Confirming
the long-render dialog skips only the estimate and keeps the caches; only an
explicit Force regenerate sends `ignore_cache`. A 429 opens the upgrade dialog with a notice that says the quota is spent and
when more are available. A 503 is a notice only.

## Per-Endpoint Limits

All endpoint limits are centralized in `apps/api/rate_limits.py`:

| Category | Endpoint | Limit |
|----------|----------|-------|
| **General** | Default (all endpoints) | 500/hour |
| **Render** | `/api/render`, `/api/render-stream` | Per-tier (see above) |
| **Estimate** | `/api/estimate` | 200/hour |
| **Verify** | `/api/verify` | 50/hour |
| **AI session** | `/api/ai/session` | 30/hour |
| **AI chat** | `/api/ai/chat-stream`, `/api/ai/synthesize` | Per-tier (20-300/hour) |
| **Editor** | Read/Write SCAD files | 120/hour |
| **Editor** | Create/Delete files | 30/hour |
| **Git** | Status/diff/log | 60/hour |
| **Git** | Commit/push/pull | 20-30/hour |
| **GitHub** | Import | 10/hour |
| **Projects** | Analyze/create/fork | 10-20/hour |
| **Analysis** | Thickness/overhang | 20/hour |
| **Pricing** | `/api/pricing/benchmark`, `/api/pricing/materials` | 60/hour |

Health endpoints are exempt from rate limiting (K8s probes).

## Client-Side Behavior (429 -> browser)

A 429 can only reach a render the placement decision had already sent to the
server (see "Browser renders are never rate limited" above). When one comes
back:

1. **Soft server placements**: `renderService.ts` catches the 429 and re-runs the
   render in the browser. The user sees a log line naming the rate limit, not an
   error.
2. **Hard server pins**: there is no browser path to fall back to, so the user
   sees the upgrade/wait message instead. A pin is hard only when the MODE's
   engine is `cadquery`, `graph` or `implicit`, when the manifest sets
   `render.server_only: true`, or when the wasm bundle is unavailable or names
   `unsupported` / `unresolved` entries.

`project.force_backend` is **not** one of them. It was demoted to a SOFT hint
that applies only on a `limited` device, so it neither pins a project to the
server nor disables the 429 fallback.

This behavior is implemented in `apps/studio/src/services/engine/renderService.ts`.

## Production Configuration

For multi-worker deployments (Gunicorn with multiple workers, Kubernetes pods):

```env
# Required: shared rate limit storage
RATE_LIMIT_STORAGE=redis://redis:6379

# Or use the general Redis URL (falls back automatically)
REDIS_URL=redis://:password@redis:6379/0

# Ensure rate limiting is active
RATE_LIMIT_ENABLED=true
FLASK_DEBUG=false
```

Without Redis, each Gunicorn worker maintains independent counters — a user could exceed limits by a factor equal to the worker count.

## Key Files

| File | Purpose |
|------|---------|
| `apps/api/extensions.py` | Limiter initialization, key function, storage backend |
| `apps/api/rate_limits.py` | Centralized limit constants for all endpoints |
| `apps/api/tiers.json` | Per-tier feature flags and render limits |
| `apps/api/services/engine/commons_render_quota.py` | Free-tier Commons CadQuery/graph quota, hourly ceiling and concurrency lease |
| `apps/api/services/core/tier_service.py` | Tier resolution from JWT claims |
| `apps/studio/src/services/engine/renderService.ts` | Client-side 429 handling and the fallback to browser rendering |
