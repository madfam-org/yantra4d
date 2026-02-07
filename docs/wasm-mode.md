# WASM Mode — Client-Side Rendering Fallback

When the backend API is unreachable, the studio automatically falls back to client-side rendering using OpenSCAD compiled to WebAssembly.

## How Detection Works

On startup, the studio calls `isBackendAvailable()` from `backendDetection.js`:

1. **Health check**: `GET /api/health` with a **2-second timeout** (`AbortSignal.timeout(2000)`)
2. **Pass**: HTTP 200 → backend mode (server-side rendering via OpenSCAD CLI)
3. **Fail**: Any error (network, CORS, timeout, non-200) → WASM fallback mode
4. **Caching**: The result is cached for the entire session — no retries. Refresh the page to re-check.

The API base URL is read from `VITE_API_BASE` (defaults to `http://localhost:5000`).

## Architecture

```
Main Thread                          Web Worker (openscad-worker.js)
─────────────                        ──────────────────────────────
ManifestProvider
  └─ isBackendAvailable() ──fail──►  Worker initialized
                                       └─ Fetches SCAD files from /scad/
                                       └─ Caches files in memory
                                       └─ Creates OpenSCAD WASM instance

User adjusts params ────────────────►  { type: 'render', scadFile, params }
                                       └─ Creates FRESH Emscripten instance
                                       └─ Builds CLI args: -D param=value
                                       └─ callMain(args) → STL output
                     ◄────────────── { type: 'progress', phase, percent }
                     ◄────────────── { type: 'result', stl: Uint8Array }
Three.js viewer renders STL
```

**Fresh instance per render**: Emscripten's `callMain()` corrupts internal state after first invocation. The worker creates a new WASM module for each render, reusing cached SCAD source files.

## When It Activates

- Backend server is down or unreachable
- Network connectivity is lost (offline mode)
- CORS misconfiguration prevents health check
- Deployed as a static site without a backend (e.g., GitHub Pages)

## Fallback Manifest

WASM mode uses an embedded fallback manifest (`apps/studio/src/config/fallback-manifest.json`) that mirrors `projects/gridfinity/project.json`. This means:

- **Only the Gridfinity project** is available in WASM mode
- Other projects require the backend API for manifest delivery
- CI enforces sync between the fallback manifest and `projects/gridfinity/project.json`

**After editing the Gridfinity manifest**, update the fallback:
```bash
cp projects/gridfinity/project.json apps/studio/src/config/fallback-manifest.json
```

## Limitations

| Limitation | Detail |
|------------|--------|
| Performance | ~4x slower than server-side OpenSCAD CLI |
| Memory | ~200MB peak per render |
| Single project | Only Gridfinity available without backend |
| No external libs | WASM build includes BOSL2 but not all global libs |
| Sequential renders | Single worker thread — renders queue, not parallelize |
| WASM binary size | ~15MB gzipped on first load |
| No retry | Detection result cached per session |

## Browser Support

WASM mode requires:

- **WebAssembly** support (all modern browsers)
- **Web Workers** for off-main-thread rendering
- **`AbortSignal.timeout()`** — Chrome 120+, Firefox 123+, Safari 17.4+

Unsupported: IE11, Safari < 17.4.

## CSP Requirements

Production servers must include `wasm-unsafe-eval` in the Content-Security-Policy header:

```
Content-Security-Policy: script-src 'self' 'wasm-unsafe-eval';
```

This is required for Emscripten's dynamic WASM compilation. Without it, the WASM module fails to load silently.

## Debugging

- **Worker console**: Open DevTools → Sources → Workers panel to see `openscad-worker.js` logs
- **Progress phases**: The worker reports `compiling`, `rendering`, `meshing` phases parsed from OpenSCAD stderr
- **Common errors**: "Module not found" → SCAD files missing from `/scad/` public path; "Memory allocation failed" → model too complex for browser memory limit
