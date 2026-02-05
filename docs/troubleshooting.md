# Troubleshooting Guide

Common issues and their solutions when working with the Qubic platform.

## Render Issues

### Render Timeouts

**Symptom**: Render hangs or times out after 120 seconds.

**Causes & Fixes**:

- **Complex geometry**: High `grid_cols × grid_rows` values produce exponentially complex models. Reduce count or simplify.
- **Docker timeout**: The default OpenSCAD timeout in Docker is 300s (`OPENSCAD_TIMEOUT` in `docker-compose.yml`). For local dev, the default is 120s.
- **WASM mode**: Client-side rendering is ~4x slower than server-side. Reduce parameter complexity.

### "OpenSCAD not found"

**Symptom**: Health check returns `"openscad_available": false`.

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
export CORS_ORIGINS="http://localhost:5173,https://studio.qubic.quest"
```

Multiple origins are comma-separated. The backend reads this in `app.py` to configure Flask-CORS.

### WASM Mode Activating Unexpectedly

**Symptom**: Studio falls back to WASM mode even though the backend is running.

**Causes**:
- Backend health check times out (2s timeout is aggressive)
- `VITE_API_BASE` not set or points to wrong URL
- CORS not configured for the studio origin
- Backend hasn't finished starting when studio loads

**Fix**: Ensure `VITE_API_BASE` matches your backend URL and CORS includes your studio origin. Refresh the page after the backend is fully started.

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

**Fix**: Copy the Tablaco manifest to the fallback location:
```bash
cp projects/tablaco/project.json apps/studio/src/config/fallback-manifest.json
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

**Fix for development**: Rate limits use in-memory storage by default. Restart the backend to reset. For production with Redis:
```bash
export RATE_LIMIT_STORAGE=redis://redis:6379
```

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

### Port Conflicts

| Service | Default Port |
|---------|:---:|
| Backend API | 5000 |
| Studio (Vite) | 5173 |
| Landing (Astro) | 4321 |

If ports conflict, edit `docker-compose.yml` port mappings or use `--port` flags in dev scripts.

## WASM-Specific Issues

### "wasm-unsafe-eval" CSP Error

**Symptom**: WASM module fails to load in production.

**Fix**: Add `wasm-unsafe-eval` to your Content-Security-Policy header:
```
Content-Security-Policy: script-src 'self' 'wasm-unsafe-eval';
```

### High Memory Usage in Browser

WASM rendering uses ~200MB peak. On mobile devices or memory-constrained environments, complex models may fail. Reduce parameter complexity or use server-side rendering.

### SCAD Files Not Found in WASM Mode

**Symptom**: Worker reports "Module not found" errors.

**Fix**: SCAD files must be served from the `/scad/` public path in the studio build. Verify they exist in `apps/studio/public/scad/` or are copied during the build step.
