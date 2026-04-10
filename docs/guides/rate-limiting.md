# Rate Limiting

Yantra4D uses Flask-Limiter to protect API endpoints from abuse. Limits are tiered by user subscription and can use either in-memory or Redis storage backends.

## How It Works

### Key Function

Rate limits are tracked per-user (authenticated) or per-IP (anonymous):

- **Authenticated**: Key is `user:{sub}` from JWT claims
- **Anonymous**: Key is `ip:{remote_address}`

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

## Per-Tier Render Limits

Backend (server-side) render limits are defined per tier in `apps/api/tiers.json`. Client-side WASM rendering is always unlimited.

| Tier | Backend Renders/Hour | AI Requests/Hour |
|------|:---:|:---:|
| guest | 10 | 0 |
| essentials | 30 | 20 |
| pro | 150 | 100 |
| madfam | 500 | 300 |

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

Health endpoints are exempt from rate limiting (K8s probes).

## Client-Side Behavior (WASM Fallback)

When the frontend receives an HTTP 429 (rate limited) response:

1. **Standard projects**: `renderService.ts` catches the 429 and retries the render using client-side WASM (OpenSCAD compiled to WebAssembly). The user sees a seamless fallback with no error.
2. **`force_backend` projects**: WASM fallback is disabled. The user sees an upgrade/wait message explaining the rate limit. These projects require server-side rendering (e.g., CadQuery engine, complex geometry).

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
| `apps/api/services/core/tier_service.py` | Tier resolution from JWT claims |
| `apps/studio/src/services/engine/renderService.ts` | Client-side 429 handling and WASM fallback |
