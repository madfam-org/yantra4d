# Enclii Diagnostic Prompt — Yantra4D Production Issues

**Date**: 2026-02-23
**Services**: `yantra4d-landing` (4d.madfam.io), `yantra4d-studio` (4d-app.madfam.io), `yantra4d-backend` (4d-api.madfam.io)
**Deploy method**: GitHub Actions → GHCR images → K8s via Kustomize (ArgoCD/Enclii-managed)

---

## Symptoms

### Issue A: Landing (4d.madfam.io) — Missing 3D Carousel

The landing page has a `ProjectCarousel3D` component (React Three Fiber + STLLoader) that renders live 3D models in a scrollable carousel. This carousel is **not appearing** in production.

The carousel:
- Is a React island mounted via `client:only="react"` in Astro (never SSR'd)
- Makes `POST /api/render` calls directly to `https://4d-api.madfam.io` to fetch STL blobs
- Uses Three.js `STLLoader` (pure JS, no WASM) to parse and display the geometry
- Lives in `ProjectGalleryContainer` → `ProjectCarousel3D` within the `ProjectGallery.astro` section

### Issue B: Studio (4d-app.madfam.io) — Blank 3D Viewport

Navigating to e.g. `https://4d-app.madfam.io/project/gears/small_motor_20t/spur_gear` shows the UI shell but the Three.js viewport renders nothing — no model, no wireframe, no error visible.

The render pipeline:
- `ManifestProvider` fetches `/api/projects` (2s timeout) then `/api/projects/{slug}/manifest`
- `renderService.detectMode()` checks `/api/health` (2s timeout), then routes to WASM or backend
- Backend path: `POST /api/render-stream` (SSE) → Flask runs OpenSCAD CLI → writes STL to `/app/backend/static/` → SSE `complete` event with `parts[].url` → `stlWorker.js` fetches the STL → `Viewer` renders mesh
- WASM path: `openscad-worker.js` (Web Worker) runs client-side OpenSCAD

---

## Diagnostic Checklist

Please investigate **each item** in order. For each, report: status (OK / FAIL / UNKNOWN), evidence (logs, HTTP responses, headers), and recommended fix if applicable.

### 1. Service Health & Reachability

```bash
# Are all three services running and responding?
curl -sI https://4d.madfam.io/              # Landing: expect 200
curl -sI https://4d-app.madfam.io/           # Studio: expect 200
curl -s  https://4d-api.madfam.io/api/health  # Backend: expect {"status":"ok","openscad":true}
```

- Is the backend pod healthy? (check readiness/liveness probe status)
- Is OpenSCAD available inside the backend container? (`openscad` binary at `/usr/local/bin/openscad`)
- Is the `render-output` emptyDir volume writable at `/app/backend/static`?

### 2. CORS Configuration

The backend should accept requests from both `https://4d-app.madfam.io` and `https://4d.madfam.io`.

```bash
# Test CORS preflight from studio origin
curl -sI -X OPTIONS https://4d-api.madfam.io/api/health \
  -H "Origin: https://4d-app.madfam.io" \
  -H "Access-Control-Request-Method: POST"
# Expect: Access-Control-Allow-Origin: https://4d-app.madfam.io

# Test CORS preflight from landing origin (for carousel API calls)
curl -sI -X OPTIONS https://4d-api.madfam.io/api/render \
  -H "Origin: https://4d.madfam.io" \
  -H "Access-Control-Request-Method: POST"
# Expect: Access-Control-Allow-Origin: https://4d.madfam.io
```

K8s deployment sets `CORS_ORIGINS=https://4d-app.madfam.io,https://4d.madfam.io`. Verify this env var is actually present in the running pod:
```bash
kubectl exec -n yantra4d deploy/yantra4d-backend -- env | grep CORS
```

### 3. Landing — CSP Blocking Three.js or API Calls

The landing `nginx.conf` sets this CSP:
```
script-src 'self' 'unsafe-inline';
connect-src 'self' https://4d-api.madfam.io http://localhost:* ws://localhost:* https://raw.githack.com https://raw.githubusercontent.com;
```

**Potential blockers:**
- `script-src` is missing `'wasm-unsafe-eval'` — while the carousel doesn't use WASM directly, some Three.js codepaths (shader compilation, buffer manipulation) may trigger CSP violations on stricter browsers
- `img-src` has `blob:` which is good (STLLoader creates blob URLs)
- `connect-src` includes `https://4d-api.madfam.io` — should be OK for `fetch()` to the render API

**Check**: Open `https://4d.madfam.io/` in Chrome DevTools → Console tab. Are there any CSP violation errors? Specifically look for:
- `Refused to evaluate a string as JavaScript` (WebGL shader compilation)
- `Refused to connect to 'https://4d-api.madfam.io/...'`
- `Refused to create a worker from 'blob:...'`

### 4. Landing — Build-Time Environment Variables

The deploy workflow (`deploy.yml`) builds the landing image **without** passing `PUBLIC_STUDIO_URL` as a build-arg:

```yaml
# deploy.yml build-landing step — NO build-args specified!
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    context: .
    file: ./apps/landing/Dockerfile
    push: true
    # ... no build-args
```

The Dockerfile accepts `ARG PUBLIC_STUDIO_URL` and sets it as an env var for the Astro build. Without it, `PUBLIC_STUDIO_URL` is empty, and the runtime fallback in `apps/landing/src/lib/env.ts` resolves `STUDIO_URL` based on hostname:
```ts
const isLocal = import.meta.env.DEV || (typeof window !== 'undefined'
  && (window.location.hostname === 'localhost' || ...));
export const STUDIO_URL = import.meta.env.PUBLIC_STUDIO_URL || (isLocal
  ? 'http://localhost:5173'
  : 'https://4d-app.madfam.io');
```

Since `PUBLIC_STUDIO_URL` is empty and the hostname is `4d.madfam.io` (not localhost), `STUDIO_URL` correctly falls back to `https://4d-app.madfam.io`. **This should be OK** but verify in the built JS bundle:

```bash
# Inside the landing container, check the bundled env value
kubectl exec -n yantra4d deploy/yantra4d-landing -- grep -r "4d-app.madfam.io" /usr/share/nginx/html/assets/ | head -5
kubectl exec -n yantra4d deploy/yantra4d-landing -- grep -r "4d-api.madfam.io" /usr/share/nginx/html/assets/ | head -5
```

Similarly, `API_URL` in the landing uses the same `isLocal` check and should resolve to `https://4d-api.madfam.io`. The carousel's `POST /api/render` calls use this value.

### 5. Landing — Carousel Actually in Built HTML

Verify the `ProjectGallery` section and its React island are present in the deployed HTML:

```bash
kubectl exec -n yantra4d deploy/yantra4d-landing -- grep -c "ProjectGallery\|Carousel\|client:only" /usr/share/nginx/html/index.html
# Check the JS chunk exists
kubectl exec -n yantra4d deploy/yantra4d-landing -- ls /usr/share/nginx/html/assets/ | grep -i carousel
```

If the component is tree-shaken or the Astro build errored silently, the carousel section might be missing entirely from the static output.

### 6. Landing — Carousel API Calls Actually Firing

Even if the component mounts, the `LiveModel` sub-component makes `POST /api/render` calls for each carousel item. If these fail:
- The model stays in "loading" state (grey wireframe box) or disappears
- No 3D content renders

**Check**: In Chrome DevTools Network tab on `https://4d.madfam.io/`, filter for `render`. Do you see POST requests to `https://4d-api.madfam.io/api/render`? What's the response status? If 403/401, auth is blocking guest requests. If CORS error, see item 2.

### 7. Studio — `VITE_API_BASE` Baked Correctly

The studio Dockerfile accepts `ARG VITE_API_BASE` and the deploy workflow passes:
```yaml
build-args: |
  VITE_API_BASE=https://4d-api.madfam.io
```

This gets baked into the Vite bundle at build time. Verify:
```bash
kubectl exec -n yantra4d deploy/yantra4d-studio -- grep -r "4d-api.madfam.io" /usr/share/nginx/html/assets/ | head -5
# Should find references to the API base URL in the JS bundle
```

If `VITE_API_BASE` is empty, all API calls go to relative paths (`/api/...`) which hit the studio's nginx proxy:
```nginx
location /api/ {
    proxy_pass http://yantra4d-backend:5000;
}
```
This **should** work in K8s if the backend Service is named `yantra4d-backend` — but verify DNS resolution:
```bash
kubectl exec -n yantra4d deploy/yantra4d-studio -- nslookup yantra4d-backend
```

### 8. Studio — SSE Proxy Buffering

The studio nginx proxies `/api/` to the backend but has **no `proxy_buffering off`** directive. This can buffer SSE streams (`/api/render-stream`), delaying or dropping events.

**Check**: Does a render request via the studio actually receive SSE events in real time?
```bash
curl -N -X POST https://4d-api.madfam.io/api/render-stream \
  -H "Content-Type: application/json" \
  -d '{"mode":"spur_gear","parameters":{"teeth":20},"parts":["spur_gear"],"project":"gears"}' \
  2>&1 | head -20
# Should see: event: progress / event: complete with parts[] URLs
```

If the direct API call works but going through the studio nginx proxy doesn't, buffering is the culprit.

### 9. Studio — WASM vs Backend Mode Routing

On capable hardware (4+ cores, 4+ GB RAM), `renderService.detectMode()` forces **WASM mode** even when the backend is available:

```js
// backendDetection.js → renderService.js
_hardwareMode = hasWasmCapabilities() ? 'wasm' : 'backend'
```

If the WASM binary (`openscad.wasm`) fails to load (CSP, missing file, network error), the render produces zero parts and the viewport stays blank — **silently**.

**Check**: In Chrome DevTools on `https://4d-app.madfam.io/project/gears/small_motor_20t/spur_gear`:
1. Console: any errors about WASM, worker, or module loading?
2. Network: is there a request for `openscad.wasm` or `openscad-worker.js`? Status?
3. Network: is there a request to `/api/render-stream`? (If WASM mode is selected, this won't fire at all)

### 10. Studio — Static File Serving for Rendered STLs

Backend renders write STLs to `STATIC_DIR` (defaults to `<app_dir>/static/`). In K8s:
- `readOnlyRootFilesystem: true` on the backend container
- `render-output` emptyDir mounted at `/app/backend/static`
- The Dockerfile sets `WORKDIR /app/backend` and app code is at `/app/backend/`
- `Config.STATIC_DIR` resolves to `Path(__file__).parent / "static"` = `/app/backend/static`

This **should** align, but verify:
```bash
kubectl exec -n yantra4d deploy/yantra4d-backend -- python -c "from config import Config; print(Config.STATIC_DIR)"
kubectl exec -n yantra4d deploy/yantra4d-backend -- ls -la /app/backend/static/
# After triggering a render:
kubectl exec -n yantra4d deploy/yantra4d-backend -- ls -la /app/backend/static/preview_*
```

Also verify the Flask static route serves these files:
```bash
# After a successful render, try fetching the STL directly
curl -sI https://4d-api.madfam.io/static/preview_spur_gear.stl
```

### 11. Studio — Auth Blocking Guest Renders

K8s backend has `AUTH_ENABLED=true`. The render endpoint may require authentication. Check:
```bash
# Unauthenticated render request
curl -s -o /dev/null -w "%{http_code}" -X POST https://4d-api.madfam.io/api/render \
  -H "Content-Type: application/json" \
  -d '{"mode":"spur_gear","parameters":{"teeth":20},"parts":["spur_gear"],"project":"gears"}'
# 200 = OK, 401/403 = auth blocking guests
```

Guest tier allows 30 renders/hr. If auth middleware rejects unauthenticated requests entirely (rather than assigning guest tier), nothing renders.

### 12. Pod Logs

Pull recent logs from all three services:
```bash
kubectl logs -n yantra4d deploy/yantra4d-backend --tail=100
kubectl logs -n yantra4d deploy/yantra4d-studio --tail=50
kubectl logs -n yantra4d deploy/yantra4d-landing --tail=50
```

Look for:
- Backend: OpenSCAD execution errors, permission denied on static dir, CORS rejections
- Studio/Landing: nginx 502/504 errors (upstream connection refused = backend DNS issue)

---

## Architecture Reference

```
                    ┌──────────────────────┐
                    │  4d.madfam.io        │
                    │  (landing - nginx)   │
                    │                      │
                    │  ProjectCarousel3D   │──── POST /api/render ────┐
                    │  (R3F + STLLoader)   │                          │
                    │                      │                          ▼
                    │  InteractiveShowcase │    ┌──────────────────────────────┐
                    │  (iframe ─────────── │──► │  4d-app.madfam.io           │
                    └──────────────────────┘    │  (studio - nginx)           │
                                                │                              │
                                                │  Viewer (R3F)               │
                                                │  renderService              │──── POST /api/render-stream ──┐
                                                │    ├─ WASM path (local)     │                               │
                                                │    └─ Backend path (SSE) ── │───────────────────────────────│
                                                └──────────────────────────────┘                               │
                                                                                                               ▼
                                                                              ┌──────────────────────────────────┐
                                                                              │  4d-api.madfam.io                │
                                                                              │  (backend - gunicorn)            │
                                                                              │                                  │
                                                                              │  /api/render-stream (SSE)        │
                                                                              │  /api/render (sync)              │
                                                                              │  /api/health                     │
                                                                              │  /static/*.stl (rendered output) │
                                                                              └──────────────────────────────────┘
```

## Key Files

| File | Relevance |
|------|-----------|
| `apps/landing/src/components/ProjectCarousel3D.tsx` | 3D carousel — R3F, STLLoader, API calls |
| `apps/landing/src/components/InteractiveShowcase.tsx` | Studio iframe embed |
| `apps/landing/src/lib/env.ts` | `STUDIO_URL` and `API_URL` resolution |
| `apps/landing/nginx.conf` | CSP headers, static serving |
| `apps/landing/Dockerfile` | `PUBLIC_STUDIO_URL` build-arg |
| `apps/studio/src/components/Viewer.jsx` | Three.js 3D viewport |
| `apps/studio/src/services/engine/renderService.js` | WASM/backend mode detection |
| `apps/studio/src/services/core/backendDetection.js` | `VITE_API_BASE`, health check |
| `apps/studio/nginx.conf` | `/api/` proxy (no `proxy_buffering off`), CSP |
| `apps/studio/Dockerfile` | `VITE_API_BASE` build-arg |
| `apps/api/app.py` | Flask CORS setup, static route |
| `apps/api/config.py` | `CORS_ORIGINS`, `STATIC_DIR` |
| `apps/api/routes/render.py` | Render + SSE stream endpoints |
| `k8s/production/yantra4d-backend-deployment.yaml` | Env vars, volume mounts, security context |
| `.github/workflows/deploy.yml` | Build-args, image push |

## Expected Output

For each checklist item (1–12), provide:
1. **Status**: OK / FAIL / PARTIAL / UNKNOWN
2. **Evidence**: Actual HTTP responses, log lines, or command output
3. **Root cause** (if FAIL): What specifically is wrong
4. **Fix**: Concrete change needed (file, line, value)

Then provide a **prioritized summary** of all findings, ordered by impact on the two symptoms.
