# Yantra4D WASM / Offline Mode

Yantra4D features a robust **dual-rendering architecture** that allows the application to function even when the backend API is unavailable or unreachable. This is achieved through a client-side OpenSCAD WebAssembly (WASM) implementation.

## Overview

The system automatically detects backend availability and switches modes seamlessly:

1.  **Backend Mode (Default)**: Sends parameters to the Python/Flask API, which runs the native OpenSCAD CLI. This is typically faster for complex models.
2.  **WASM Mode (Fallback)**: Runs OpenSCAD entirely within the browser using a Web Worker. This enables zero-latency offline usage and static deployments (e.g., GitHub Pages).

## Architecture

The logic resides principally in `apps/studio/src/services/renderService.js` and `apps/studio/src/services/openscad-worker.js`.

### Detection Mechanism
On application start (and before renders), `renderService.ts` probes the backend health endpoint via `backendDetection.ts`:
```typescript
// apps/studio/src/services/core/backendDetection.ts
export async function isBackendAvailable(): Promise<boolean> {
  // TTL-cached: 30s for negative results (allows recovery), 5min for positive
  const now = Date.now()
  if (_backendAvailable !== null) {
    const ttl = _backendAvailable ? POSITIVE_TTL_MS : NEGATIVE_TTL_MS
    if (now - _lastCheckTime < ttl) return _backendAvailable
  }
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2000) })
    _backendAvailable = res.ok
  } catch {
    _backendAvailable = false
  }
  _lastCheckTime = now
  return _backendAvailable
}
```

**Detection order** in `detectMode()`:
1. CadQuery engine → always backend (no WASM path exists)
2. Check `isBackendAvailable()` (TTL-cached)
3. If available → respect `force_backend`, `API_BASE`, complexity circuit breaker
4. If unavailable → fall back to WASM (if device is capable)

This means `force_backend: true` is only honoured when the backend is actually reachable. If the backend goes down, the studio degrades to WASM rendering automatically, and re-checks availability every 30 seconds.

### The Web Worker
The WASM worker (`openscad-worker.js`) manages the OpenSCAD instance to prevent the main thread from freezing during heavy computations.

-   **Library**: Uses `openscad-wasm` (based on OpenSCAD master branch).
-   **Isolation**: Every render spins up a *fresh* WASM instance to avoid memory corruption issues (a known quirk of the EMSCRIPTEN build).
-   **File System**: Source `.scad` files are fetched once, cached in memory, and written to the worker's virtual filesystem for each render.

## Enabling WASM Mode

### Automatic Fallback
Simply stop the backend server. The Studio will automatically detect the outage within 30 seconds (negative TTL) and fall back to WASM rendering. If the backend was initially down when the page loaded, the ProjectsView shows a "Retry" button and an "Open Demo Project" button to load the bundled gridfinity fallback manifest. If a backend render fails mid-session with a network error, `renderParts()` catches the failure and transparently retries with WASM.

### Forcing WASM Mode
You can force WASM mode for testing by blocking the API rendering or building a static version of the site without `VITE_API_BASE_URL`.

## WASM bundle endpoint

`GET /api/projects/<slug>/wasm-bundle`

### Why libraries and fonts were the blocker

Browser rendering has never actually worked for a visitor. The worker fetched
its sources from `${origin}/scad/<file>` — a path nothing serves in production —
and it mounted no libraries and no fonts at all. So the moment a cartridge said
`include <../../libs/BOSL2/std.scad>`, which is how nearly every cartridge in the
commons pulls in attachments and rounding, the browser render failed on a file
that was never there. Same for `text()`: no fontconfig, no typeface, no glyphs.

That, far more than geometry cost, is why ~490 manifests carry
`force_backend: true`. The flag was papering over a missing filesystem.

This endpoint hands the worker the whole filesystem in one response, so it can
populate its virtual FS in a single write pass and then render offline.

Scope, measured against the checked-out commons (501 cartridges): 31 have at
least one OpenSCAD mode and get a bundle; the other 470 are CadQuery, graph or
implicit and are refused with `engine_not_wasm`. Eight of the 31 are dual-engine
cartridges whose *project* engine is CadQuery but which declare OpenSCAD on
individual modes — those get a bundle covering exactly those modes.

### Contract

```json
{
  "slug": "rugged-box",
  "engine": "openscad",
  "entry_files": ["rugged_complete.scad", "rugged_bottom.scad"],
  "files": {
    "projects/rugged-box/rugged_core.scad": "include <../../libs/BOSL2/std.scad>…",
    "libs/BOSL2/std.scad": "…"
  },
  "fonts": {
    "projects/rugged-box/fonts/Label.ttf": "<base64>",
    "fonts/AllertaStencil-Regular.ttf": "<base64>",
    "fonts.conf": "<?xml version=\"1.0\"?>…"
  },
  "unsupported": [],
  "unresolved": [],
  "bytes": 2837697,
  "etag": "<sha256>"
}
```

| Key | Meaning |
| :--- | :--- |
| `slug` | The cartridge asked for. |
| `engine` | Always `openscad` — a bundle is only ever issued for the browser kernel. |
| `entry_files` | `scad_file` of every mode the browser can render, as the manifest writes it (bare name, relative to the cartridge root). |
| `files` | Virtual path → UTF-8 source, for the whole resolved closure. |
| `fonts` | Virtual path → base64 font, plus `fonts.conf` (fontconfig XML, not base64). |
| `unsupported` | What this WASM build cannot honour. Non-empty means **server required**. |
| `unresolved` | Include targets that did not resolve, as `"<including path>: <target>"`. |
| `bytes` | Everything the worker writes to its FS: sources + raw fonts + `fonts.conf`. |
| `etag` | SHA-256 over exactly that content. Also the `ETag` header on public projects. |

### Virtual filesystem layout

Every path is POSIX and relative to a virtual root that **mirrors the server's own
directory shape**:

```
/projects/<slug>/…   the cartridge          (Config.PROJECTS_DIR/<slug>)
/libs/…              shared libraries       (Config.LIBS_DIR — BOSL2, dotSCAD, …)
/fonts/…             shared typefaces       (Config.FONTS_DIR)
```

Mirroring is the whole point: `include <../../libs/BOSL2/std.scad>` written in
`/projects/rugged-box/rugged_core.scad` resolves to `/libs/BOSL2/std.scad` inside
the worker exactly as it does on disk, and nobody has to rewrite anyone's source.

For includes that resolve through the search path rather than relatively, the
worker must set

```
OPENSCADPATH=/libs:/libs/dotSCAD/src:/projects
```

which is the virtual mirror of what `config.py` composes for the native binary.
It is a constant: the virtual layout does not depend on where those directories
happen to live on a host.

### Resolution rules

1. Start from every `modes[*].scad_file` whose mode renders with OpenSCAD. A
   dual-engine cartridge keeps its OpenSCAD modes and drops the rest; a cartridge
   with none is refused with **400 `engine_not_wasm`**.
2. Parse `include <…>` and `use <…>` (they differ in scope, not in lookup).
3. Resolve each target the way OpenSCAD does — relative to the **including
   file's** directory first, then each OPENSCADPATH entry in order
   (`LIBS_DIR`, `dotSCAD/src`, `PROJECTS_DIR`).
4. Recurse, with a visited set keyed on the resolved real path, so cycles
   terminate and BOSL2's many diamond dependencies are read once.
5. **Confine.** A resolved file is admitted only when it lands inside the
   cartridge's own directory or inside `LIBS_DIR` (checked with
   `utils.route_helpers.safe_join_path`). A traversal, an absolute path, a
   symlink pointing out of the tree, or another cartridge reached through
   `PROJECTS_DIR` is dropped and named in `unresolved` — never silently omitted,
   because a missing include changes what OpenSCAD renders.

### Fonts

The cartridge's own `fonts/*.ttf|otf` always travels: it is part of the
cartridge. The shared font directory travels only when some resolved source
calls `text(` — it is the single largest thing a bundle can carry for nothing.
Detection is deliberately conservative and scans the whole closure, so a library
that merely offers a text helper pulls the shared fonts in too.

`fonts.conf` is generated by the same `fontconfig_xml()` the native renderer uses
(`services/engine/openscad.py`), pointed at the virtual directories. One
generator, because a font that renders on the server and not in the browser is
the kind of divergence nobody notices until a customer does.

### `unsupported`

Small and honest — each entry means the browser would render something *other*
than what the server renders:

| Value | Cause |
| :--- | :--- |
| `import` | `import(…)` pulls an external STL/DXF/SVG that is not in the closure. |
| `surface` | `surface(…)` reads a heightmap file, same problem. |
| `unresolved_includes` | At least one `include`/`use` did not resolve. |

Detection runs on comment-stripped source, so a commented-out `import()` does not
push a perfectly renderable cartridge onto the server. Anything merely *slow* in
the browser is not listed here — that belongs in the manifest's
`render.browser_max_estimate_seconds`.

### Limits

| Limit | Value |
| :--- | :--- |
| Total bytes | 24 MiB |
| File count | 600 |

Crossing either returns **413 `bundle_too_large`** with `files`, `bytes`,
`max_files` and `max_bytes`, so the caller sees how far over it went. For scale:
`rugged-box` pulls the whole of BOSL2 and lands at 40 files / ~2.7 MiB;
`relief` is 3 files / ~24 KB plus one 20 KB typeface.

### Caching

- The ETag is a SHA-256 over the bundle's own content, so it is stable across
  servers and moves whenever a source, a library, a font, the entry list or the
  honesty lists change.
- Public projects: `Cache-Control: public, max-age=300`, strong `ETag`,
  `If-None-Match` → **304**.
- Private projects: `Cache-Control: private, no-store`, **no** `ETag` and no 304
  — mirroring the private manifest route, because an ETag is a stable, guessable
  handle to the content being withheld. The `etag` field is still in the body for
  an entitled caller.
- Server side, a bundle is built at most once per (slug, mtime set): the
  in-process cache is keyed on the manifest's mtime plus the newest mtime across
  every file the last build resolved, so editing any of them — or the manifest
  that decides which files those are — rebuilds.

### Rate limiting

Only the app-wide default. This is the free browser path: the response is a
cached blob of source text, and every request it satisfies is a server render
that never happens. See the comment in `apps/api/rate_limits.py`.

### Refusals

| Status | `error_code` | When |
| :--- | :--- | :--- |
| 400 | *(slug validation)* | Malformed slug. |
| 400 | `engine_not_wasm` | No OpenSCAD mode — a cadquery, graph or implicit cartridge. |
| 403 | `project_locked` | Private project, caller not entitled. |
| 404 | `project_not_found` | Unknown slug. |
| 413 | `bundle_too_large` | Source closure over the limits. |

## Limitations

| Feature | Backend Mode | WASM Mode |
| :--- | :--- | :--- |
| **Performance** | Native speed (fast) | ~3-5x slower |
| **Memory** | Server RAM limit | Browser tab limit (~4GB) |
| **Libraries** | Full system access | Virtual FS, populated from `/api/projects/<slug>/wasm-bundle` |
| **Export** | STL, 3MF, OFF, PNG | STL only (currently) |
| **Caching** | Persistent Redis/Disk | Ephemeral (Session) |

## Troubleshooting

-   **"Out of Memory"**: Complex models with high `fn` (smoothness) may crash the browser tab. Reduce `fn` or switch to backend mode.
-   **"SharedArrayBuffer"**: Ensure your server sends `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers, which are required for high-performance WASM threading (though `openscad-wasm` single-threaded builds work without them).
