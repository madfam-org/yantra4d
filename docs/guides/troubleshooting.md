# Troubleshooting Guide

Common issues and their solutions when working with the Yantra4D platform.

## Render Issues

### Render Timeouts

**Symptom**: Render hangs or times out after 120 seconds.

**Causes & Fixes**:

- **Complex geometry**: High `grid_cols × grid_rows` values produce exponentially complex models. Reduce count or simplify.
- **Docker timeout**: The default OpenSCAD timeout in Docker is 300s (`OPENSCAD_TIMEOUT` in `docker-compose.yml`). For local dev, the default is 120s.
- **Browser placement**: a browser render is roughly 3-5x slower than the native server one, and the browser is the **default** placement. Reduce parameter complexity, give the cartridge a `render.browser_max_estimate_seconds` budget so the Studio hands big jobs to the server on its own, or pick **Server** in the sidebar's placement control.

### Render performance

Two knobs control how fast server-side renders run. Both default to the fast path
and degrade safely, so you normally do not need to touch them.

**OpenSCAD geometry backend.** OpenSCAD 2023+ ships a Manifold kernel alongside
the older CGAL one. CGAL degrades superlinearly on the boolean- and thread-heavy
cartridges that dominate this commons — measured on `projects/faircap-filter`
(BOSL2 threading) with OpenSCAD 2026.02.13:

| Backend | Wall time | Mesh verdict |
|---------|----------:|--------------|
| CGAL | 47.4s | watertight (volume 22715.16) |
| Manifold | 6.6s | watertight (volume 22715.17) |

The backend is probed **once** from the installed binary's `--help` and cached.
Binaries without `--backend` behave exactly as before — no flag is passed.

```bash
export YANTRA4D_OPENSCAD_BACKEND=auto      # default: Manifold when available
export YANTRA4D_OPENSCAD_BACKEND=cgal      # pin the old kernel to compare output
```

> The render cache key includes the effective backend **and** the OpenSCAD
> version, so Manifold and CGAL artifacts are never served for one another.
> Switching backends partitions the cache; it does not corrupt it. Old entries
> age out on TTL.

**Warm CadQuery pool.** `import cadquery` (OCCT) costs 1-3s and used to be paid
on every render. A pool of persistent workers imports once and then serves jobs:

| Path | Median wall time |
|------|-----------------:|
| Cold spawn per render | 9.7s |
| Warm pool worker | 0.23s |

```bash
export YANTRA4D_CQ_WORKERS=4               # more workers for parallel renders
export YANTRA4D_CQ_WORKERS=0               # disable; every render spawns fresh
export YANTRA4D_CQ_POOL_ENABLED=0          # kill switch, same effect
```

If a worker cannot start (e.g. CadQuery is not installed, or the environment
forbids extra processes) the pool logs a warning and every render falls back to
the historical per-render spawn. A pool problem never fails a render.

### "OpenSCAD not found"

**Symptom**: Health check returns `"status": "degraded"` with `"checks": { "openscad": { "ok": false } }`. The API still serves requests (200) but server-side rendering is unavailable. OpenSCAD cartridges are largely unaffected — the browser is where they render by default — but anything hard-pinned to the server (a `cadquery`, `graph` or `implicit` mode, `render.server_only`) has nowhere left to run.

**Fix**: Set `OPENSCAD_PATH` env var to your OpenSCAD binary:
```bash
export OPENSCAD_PATH=/usr/bin/openscad     # Linux
export OPENSCAD_PATH=/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD  # macOS
```

Or install OpenSCAD:
```bash
# Ubuntu/Debian
sudo apt install openscad

# macOS
brew install openscad
```

### Blank Viewer / No STL

**Causes**:
- Backend returned an error — check the console log panel at the bottom of the studio
- OpenSCAD syntax error in `.scad` file — look for `ERROR:` lines in logs
- CORS issue — backend not accepting requests from studio origin

## Network & CORS

### CORS Errors

**Symptom**: Browser console shows `Access-Control-Allow-Origin` errors.

**Fix**: Set `CORS_ORIGINS` on the backend:
```bash
export CORS_ORIGINS="http://localhost:5173,https://app.yantra4d.com"
```

Multiple origins are comma-separated. The backend reads this in `app.py` to configure Flask-CORS.

### A Render Ran in the Browser When You Expected the Server

**This is the default, not a fault.** The browser is where a render runs unless
something concrete says it cannot: rendering there is free for us and unmetered
for the visitor. A healthy backend is no longer a reason to leave it -- the old
`if (API_BASE) return 'backend'` line is gone, and `/api/health` now answers
only "is a *server* placement possible?".

**Find out which placement was chosen, and why:**

- The sidebar's placement control (`data-testid="render-placement"`) names the
  placement in its badge and the deciding rule in the line beneath it.
- From the console, `getPlacementDecision('<slug>')` in
  `services/engine/renderService.ts` returns `{ placement, reasons, hard }`.
  Reason keys are stable: `default_browser`, `capability_incapable`,
  `browser_failed:oom`, `estimate_over_threshold:62s>45s`,
  `engine_unsupported:cadquery`, `manifest_server_only`, `bundle_unavailable`.
- To pin one placement for a session: `?render=backend` or `?render=wasm`
  (whole build: `VITE_RENDER_MODE`). `?render=backend` is deliberately exempt
  from the outage guard below -- support hands it out when the browser is what
  broke.

**When the server IS expected** -- the hard rules, which nothing overrides and
which disable the Auto/Browser/Server control:

| Cause | Reason key |
|-------|------------|
| the MODE's engine is `cadquery`, `graph` or `implicit` | `engine_unsupported:<engine>` |
| manifest `render.server_only: true` | `manifest_server_only` |
| the wasm bundle is unavailable or names `unsupported` / `unresolved` | `bundle_unavailable`, `bundle_unsupported:…`, `bundle_unresolved:…` |

Everything else that picks the server -- an `incapable` device, a browser render
that already failed for this slug this session, an estimate over the budget, a
legacy `force_backend` on a `limited` device -- is **soft**, and flips back to
the browser when the backend is unreachable. `project.force_backend` alone never
pins anything.

**If it is the SERVER you cannot reach**: a 2 s health-check timeout, a
`VITE_API_BASE` pointing at the wrong URL, `CORS_ORIGINS` missing your studio
origin, or a backend that had not finished starting all make `isBackendAvailable()`
answer "no". That does not change the default, but it does strand every
hard-pinned cartridge. Fix the URL and the CORS origin, then reload.

## Git Submodules

### Missing Libraries (BOSL2, NopSCADlib, etc.)

**Symptom**: OpenSCAD errors like `Can't open include file 'BOSL2/std.scad'`.

**Fix**: Initialize git submodules:
```bash
git submodule update --init --recursive
```

The `libs/` directory contains three submodules: BOSL2, NopSCADlib, and Round-Anything. These must be checked out for server-side rendering to find library includes.

## Manifest Issues

### Fallback Manifest Out of Sync

**Symptom**: CI `manifest-sync` job fails.

**Fix**: Copy the Gridfinity manifest to the fallback location:
```bash
cp projects/gridfinity/project.json apps/studio/src/config/fallback-manifest.json
```

The CI workflow runs `diff` between these two files. They must be byte-identical.

### New Parameter Not Appearing in UI

**Causes**:
- Parameter missing from `project.json` → `parameters[]` array
- Parameter `modes` array doesn't include the active mode
- Frontend cache — hard refresh or clear service worker cache

## Shareable URLs

### Shared Link Shows Wrong Parameters

**Format**: `?p=<base64url-encoded JSON>` encodes only non-default parameter values.

**Causes**:
- Parameters were changed after the link was generated
- Manifest default values changed — old links encode a diff against old defaults
- URL was truncated (very long parameter sets produce long URLs)

**Debugging**: Decode the `p` parameter:
```javascript
JSON.parse(atob(new URLSearchParams(location.search).get('p').replace(/-/g,'+').replace(/_/g,'/')))
```

## Rate Limiting

### 429 Too Many Requests

**Symptom**: Backend returns HTTP 429.

**Limits** (from `extensions.py`):

| Endpoint | Limit |
|----------|-------|
| `/api/render` | 100/hour |
| `/api/estimate` | 200/hour |
| `/api/verify` | 50/hour |
| `/api/ai/*` | Tier-dependent (30–300/hour) |

**Response headers**: The backend includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers on all rate-limited responses. The studio `apiClient.ts` reads these headers and exposes them via the `useRateLimit()` hook.

**Fix for development**: Rate limits use in-memory storage by default (`memory://`). Restart the backend to reset.

**Production with Redis**: Docker Compose automatically uses Redis for shared rate limiting across workers. To configure manually:
```bash
export RATE_LIMIT_STORAGE=redis://redis:6379
```

If Redis is unreachable, Flask-Limiter will log a warning and fall back to in-memory storage. Ensure the `redis` Python package is installed (`pip install redis~=5.0`).

## Docker

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSCAD_PATH` | `/usr/bin/openscad` | Path to OpenSCAD binary |
| `SCAD_DIR` | — | Single-project SCAD directory (legacy) |
| `PROJECTS_DIR` | `projects/` | Multi-project root directory |
| `VERIFY_SCRIPT` | `tests/verify_design.py` | Path to verification script |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `VITE_API_BASE` | `http://localhost:5000` | Studio → backend URL |
| `AI_PROVIDER` | `anthropic` | AI provider: `anthropic` or `openai` |
| `AI_API_KEY` | — | API key for AI features |
| `RATE_LIMIT_STORAGE` | `memory://` | Rate limiter backend (`memory://` or `redis://host:port`) |
| `OPENSCAD_TIMEOUT` | `120` | Render timeout in seconds |
| `YANTRA4D_OPENSCAD_BACKEND` | `auto` | Geometry kernel: `auto`, `manifold`, or `cgal`. See [Render performance](#render-performance) |
| `YANTRA4D_CQ_WORKERS` | `2` | Warm CadQuery worker processes (`0` disables the pool) |
| `YANTRA4D_CQ_WORKER_MAX_JOBS` | `50` | Recycle a CadQuery worker after this many jobs (`0` = never) |
| `YANTRA4D_CQ_POOL_ENABLED` | `1` | Kill switch for the warm CadQuery pool |

### Port Conflicts

| Service | Default Port |
|---------|:---:|
| Backend API | 5000 |
| Studio (Vite) | 5173 |
| Landing (Astro) | 4321 |

If ports conflict, edit `docker-compose.yml` port mappings or use `--port` flags in dev scripts.

## Database & Migrations

### CrashLoopBackOff After Deploy

**Symptom**: New backend pods crash at startup with `OperationalError: table X already exists`. ArgoCD shows Degraded.

**Cause**: The Dockerfile CMD runs `flask db upgrade` before gunicorn. If an Alembic migration uses `op.create_table()` unconditionally and the table already exists on the persistent volume, SQLite raises an error and the pod exits.

**Fix**: Make migrations idempotent with an inspector guard:
```python
def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "table_name" not in inspector.get_table_names():
        op.create_table("table_name", ...)
```

**Prevention**: All new migrations must check for existing tables/indexes before creating them. This is the standard Alembic pattern for idempotent migrations.

## WASM-Specific Issues

### "wasm-unsafe-eval" CSP Error

**Symptom**: WASM module fails to load in production.

**Fix**: Add `wasm-unsafe-eval` to your Content-Security-Policy header:
```
Content-Security-Policy: script-src 'self' 'wasm-unsafe-eval';
```

### High Memory Usage in Browser

WASM rendering uses ~200MB peak. On mobile devices or memory-constrained environments, complex models may fail. Reduce parameter complexity or use server-side rendering.

### Browser Render Cannot Find Its Sources

**Symptom**: the console logs `[FALLBACK] Browser render failed (init-error), rendering on our server...`, or the placement badge shows the server with a `bundle_*` reason.

**Where the sources come from**: the worker mounts a **wasm bundle** --
`GET /api/projects/<slug>/wasm-bundle` -- into its virtual filesystem at
`/projects/<slug>/…`, `/libs/…` and `/fonts/…`, and runs the entry file by that
path. There is no `/scad/` fetch and nothing is served from
`apps/studio/public/scad/`. See [wasm-mode.md](./wasm-mode.md).

**Fix by refusal:**

| Status | `error_code` | What it means |
|--------|--------------|---------------|
| 400 | `engine_not_wasm` | No OpenSCAD mode -- a cadquery, graph or implicit cartridge. Server rendering is correct; nothing to fix. |
| 403 | `project_locked` | Private project, caller not entitled. This must surface as a locked project, not as "your browser cannot render this" -- sign in. |
| 404 | `project_not_found` | Unknown slug. |
| 413 | `bundle_too_large` | The include closure crosses 24 MiB or 600 files; the body reports `files`, `bytes`, `max_files`, `max_bytes`. |

A bundle that arrives with a non-empty `unsupported` or `unresolved` list is a
**hard** server pin, not a warning: a missing include does not render a slightly
different model, it renders a different one or none at all.

**The `/scad/` trap.** A fallback to `${BASE_URL}/scad/<file>` survives behind
the same interface for a local backend predating the bundle endpoint, and it is
**disabled in production builds**. It fetches only each mode's entry file -- no
libraries, no fonts -- so a cartridge that includes BOSL2 or calls `text()` will
not render correctly under it, and it logs a `[wasm-bundle] DEV FALLBACK`
warning saying so. In production the same path is the bug the bundle exists to
fix: nginx's `try_files … /index.html` answers `/scad/anything` with the SPA's
own HTML at **200 OK**, so the fallback explicitly refuses a body beginning with
`<!doctype` rather than writing a page of HTML into the virtual FS as SCAD.
