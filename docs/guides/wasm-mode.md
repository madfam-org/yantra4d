# Browser Rendering (WASM) and Render Placement

Yantra4D renders in one of two **placements**:

- **browser** — OpenSCAD compiled to WebAssembly, running in a Web Worker on the
  visitor's own machine. Free for us, unmetered for them. **This is the default.**
- **server** — the Flask API's native OpenSCAD / CadQuery. Costs us CPU and
  costs the visitor one of their hourly render units.

The browser is the default because the machine is already there and already
paid for. A render only goes to the server when something concrete says the
browser cannot do it, or when the visitor asks for it.

## The decision

The policy lives in one pure function,
`apps/studio/src/services/engine/renderPlacement.ts`:

```ts
decideRenderPlacement(input) -> { placement: 'browser' | 'server', reasons: string[], hard: boolean }
```

Nothing in it reads `window`, `localStorage`, the network, or module globals —
every input is passed in. That is what makes the precedence table testable as a
table (`renderPlacement.test.js`) rather than as an integration test with six
mocks.

| # | Rule | Result |
|---|------|--------|
| 1 | the MODE's engine is `cadquery`, `graph` or `implicit` | server, **hard** |
| 2 | manifest `render.server_only === true` | server, **hard** |
| 3 | the wasm bundle is unavailable, or names `unsupported` / `unresolved` | server, **hard** |
| 4 | an `export_format` the browser kernel cannot emit (anything but `stl`) | server, **hard** |
| 5 | `?render=backend` / `?render=wasm` (or `VITE_RENDER_MODE`) | server / browser |
| 6 | the visitor's `Auto / Browser / Server` preference | server / browser |
| 7 | capability tier is `incapable` | server |
| 8 | a browser render already failed for this cartridge this session | server |
| 9 | browser estimate over the tier threshold (capable 45 s, limited 15 s) | server |
| 10 | legacy `project.force_backend`, **only** on a `limited` device | server |
| 11 | **default** | **browser** |

`isBackendAvailable()` (`/api/health`, TTL-cached: 30 s negative, 5 min
positive) no longer decides anything on its own. It answers one question: is a
**server** placement even possible? A **soft** server decision flips back to the
browser when the answer is no. A **hard** one does not — the browser genuinely
cannot produce that model, and the failure should name the unreachable server
rather than blame the visitor's machine.

`?render=backend` is exempt from that flip. Support hands it out precisely when
the browser is what broke; bouncing the user back to it on a health blip would
undo the override at the one moment it matters.

### What changed, and why it mattered

`detectMode()` used to contain, above every heuristic:

```ts
if (API_BASE) return 'backend'
```

Production always sets `VITE_API_BASE`. So in production the complexity circuit
breaker, the hardware check and `force_backend` were all unreachable, and every
visitor's render — including a slider drag on a demo link — was billed to our
CPU and metered against their hourly quota. That line is gone.

The module-global `_hardwareMode` is gone too: it pinned the path for the whole
session, so opening one CadQuery project sent every later OpenSCAD project to
the server. Placement is a property of (device, cartridge), so it is now keyed
by slug.

## Engine is a MODE property

`effectiveModeEngine(manifest, modeId)` in `renderPlacement.ts` mirrors
`ProjectManifest.mode_engine()` in `apps/api/manifest.py`, highest priority
first:

1. An explicit, known `engine` on the mode.
2. Inference from the mode's `scad_file`: `.graph.json` → graph, `.py` / `.cq`
   → cadquery.
3. The project engine (default `openscad`).

An `implicit` project is the exception: implicit fields are a whole-project
concern, so every mode is implicit and nothing overrides it.

Reading `manifest.engine` alone would be wrong, and expensively so. `gridfinity`
declares `project.engine: "cadquery"` and then three modes with
`engine: "openscad"`; 8 of the 31 OpenSCAD-capable cartridges are dual-engine
like that. The bundle endpoint agrees — it is issued whenever **any** mode is
OpenSCAD, `entry_files` lists only those modes' files, and 400 `engine_not_wasm`
comes back only when no mode is.

`canRunWasm(manifest, modeId?)` follows the same split: with a mode it answers
for that mode; without one it answers "could **any** mode run in the browser?",
which is what a surface with no mode in scope (the rate-limit banner) means.

## The capability probe

`apps/studio/src/services/engine/renderCapability.ts`.

**Static signals**: `WebAssembly` present; SIMD (via `WebAssembly.validate` of a
29-byte `i8x16.splat` module); `hardwareConcurrency`; `deviceMemory`;
`userAgentData.mobile` with a UA-string fallback; `crossOriginIsolated`;
`connection.saveData`; `prefers-reduced-data`.

**Unknown is unknown.** A signal the browser withholds neither promotes nor
demotes. `deviceMemory` does not exist on Firefox or Safari, and the old
`navigator.deviceMemory || 4` invented a value for roughly a third of the web.

**Dynamic**: a one-shot micro-benchmark — instantiate a fresh WASM module and
render `$fn=64; cube(10);` — run in the worker on first need and cached in
`localStorage` under a versioned key (`y4d.render_capability.v1`), re-probed
after 7 days or when the version bumps. Concurrent callers share one probe.

**Tiers**: `capable | limited | incapable`. The static signals set a *ceiling*;
the benchmark can only lower it (a phone that compiles a cube quickly is still a
phone). Thresholds, in wall ms for the reference render:

| Benchmark | Tier |
|---|---|
| ≤ 600 ms | ceiling (usually `capable`) |
| ≤ 2500 ms | at most `limited` |
| > 2500 ms | `incapable` |

Calibrated against the shipped `openscad-wasm@0.0.4` build measured on a
server-class x86 host under Node 22 (5 runs): **42 ms median instantiate, 3 ms
median tiny render, 45 ms combined** (151 ms on the cold first run). The
thresholds sit at roughly 13x and 55x that floor. The same lab measured what
real cartridges cost in this build: `gridfinity/cup.scad` (BOSL2, fn=32) 5.2 s,
`relief/plaque.scad` with fonts 5.5 s, `torus-knot` 1.0 s — a machine 55x slower
than the reference turns the 5 s cartridge into four minutes, which is a server
render.

## The render bundle

`GET /api/projects/<slug>/wasm-bundle` (fetched with `apiFetch`, so the bearer
token flows and a private project answers 403 `project_locked`):

```json
{
  "slug": "gridfinity",
  "engine": "openscad",
  "entry_files": ["cup.scad"],
  "files": {
    "projects/gridfinity/cup.scad": "include <../../libs/BOSL2/std.scad>\n…",
    "libs/BOSL2/std.scad": "…"
  },
  "fonts": {
    "projects/gridfinity/fonts/Label.ttf": "<base64>",
    "fonts/Allerta.ttf": "<base64>",
    "fonts.conf": "<?xml version=\"1.0\"?>…"
  },
  "unsupported": [],
  "unresolved": [],
  "bytes": 1234567,
  "etag": "…"
}
```

`unsupported` names features this WASM build cannot honour (`import`, `surface`,
`unresolved_includes`). `unresolved` names include/use targets the server could
not confine to the cartridge directory or `libs/`, as `"<including path>:
<target>"`. **Both are hard**: a missing include does not make the browser
render something slightly different, it makes it render something else or
nothing at all.

The server resolves the `include`/`use` graph transitively, allowlisted to
`projects/` and `libs/`. The studio caches one bundle per slug in worker memory.

### What it replaces, and why the old path could not work

The worker used to fetch `${origin}/scad/${scad_file}` for each mode's entry
file and write it at `/${name}`. Three defects, each fatal on its own:

1. **Nothing serves `/scad/` in production.** nginx's `try_files … /index.html`
   answers `/scad/anything` with the SPA's own HTML at **200 OK**, so the worker
   wrote a page of `<!doctype html>` into the virtual filesystem as a SCAD file.
2. **Only the entry file was fetched.** Nearly every OpenSCAD cartridge in this
   commons opens with `include <../../libs/BOSL2/std.scad>`; none of BOSL2 was
   ever written, so the include could not resolve even when the entry file was
   real.
3. **No fonts were mounted**, so `text()` silently rendered nothing — the base
   plate came out, the lettering did not, at exit code 0.

A dev-only fallback to `/scad/` remains behind the same interface for a local
backend that predates the endpoint. It is disabled in production builds and
refuses a response that begins with `<!doctype`.

### Filesystem layout

`planBundleFsLayout()` (pure, unit-tested) maps bundle keys to absolute virtual
paths and lists the directories to create, parents first — `FS.mkdir` creates no
intermediates:

```
/projects/<slug>/cup.scad         <- entry, run by this path
/libs/BOSL2/std.scad              <- `../../libs/BOSL2/std.scad` from the entry
/projects/<slug>/fonts/<face>.ttf <- the cartridge's own typefaces
/fonts/<face>.ttf                 <- the shared typefaces
/fonts/fonts.conf                 <- FONTCONFIG_FILE points here
/tmp/fontconfig                   <- fontconfig's cache dir
```

Fonts keep the virtual path the bundle gave them. Flattening them into `/fonts`
would silently unmount every cartridge-local typeface, because the server's
`fonts.conf` names those exact directories.

Keys containing `..`, `.` or empty segments are refused rather than written.

### OPENSCADPATH

Relative includes resolve against the including file's own directory and need
nothing set. Includes written against the search path — `include
<BOSL2/std.scad>`, `include <dotSCAD/src/…>` — resolve only if the worker
searches the same directories, in the same order, as the server did when it
built the bundle:

```
OPENSCADPATH=/libs:/libs/dotSCAD/src:/projects
```

the virtual mirror of what `config.py` composes for the native binary. A
different order would let the browser render a different model from identical
source.

**It must be set in Emscripten's `preRun`.** `OPENSCADPATH` is read through
`getenv()` and the environment is materialised during startup, so a late
assignment is ignored. Measured against this build: the search-path include
failed with `Can't open include file 'BOSL2/std.scad'` when `ENV` was assigned
after `createOpenSCAD()` resolved, and produced a 19,073-byte STL when the same
assignment happened in `preRun`. `FONTCONFIG_FILE` happens to survive the late
assignment; relying on that difference would be relying on an accident, so the
worker mounts the whole layout in `preRun`.

### Fonts

The OpenSCAD WASM build has fontconfig and freetype compiled in but **no default
config file**. Without `FONTCONFIG_FILE` it answers every `text()` with

```
Fontconfig error: Cannot load default config file: No such file: (null)
WARNING: Can't get font  in file …
```

and renders the model minus its lettering, at exit code 0.

The `fonts` map carries one key that is not a typeface: **`fonts.conf`**, whose
value is fontconfig XML rather than base64. The API generates it with the same
`fontconfig_xml()` the native renderer uses, already pointed at the virtual font
directories, and the worker writes it **verbatim** at `/fonts/fonts.conf` and
sets `FONTCONFIG_FILE` / `FONTCONFIG_PATH`. One generator, because a typeface
that resolves on the server and not in the browser is the kind of divergence
nobody notices until a customer does. The studio only synthesises its own
`fonts.conf` for the dev-only `/scad/` fallback, which has no API to ask.

> The `openscad-wasm@0.0.4` tarball ships `openscad.fonts.d.ts` declaring
> `addFonts(openscad)` but **no corresponding JavaScript** — the package's only
> export is `createOpenSCAD`. The fontconfig mount is therefore implemented in
> `openscad-worker.ts` rather than delegated to the package.

**Measured** against the real build (Node 22, 2026-09-01):

All of these ran the SHIPPED `planBundleFsLayout()` and the shipped
`mountLayout()` sequence, not a hand-written approximation.

| Case | Result |
|---|---|
| `projects/gridfinity/cup.scad`, relative `../../libs/BOSL2/std.scad` | rc 0, **335,273-byte STL**, 4.4 s |
| `include <BOSL2/std.scad>` resolved through `OPENSCADPATH` in `preRun` | rc 0, **19,073-byte STL**, 0.26 s |
| the same include with `ENV` assigned AFTER instantiation | rc 1, **0 bytes**, `Can't open include file` |
| `projects/relief/plaque.scad`, no fonts mounted | rc 0, **1,479-byte STL** (base only), fontconfig error |
| `projects/relief/plaque.scad`, cartridge-local font dir + supplied `fonts.conf` | rc 0, **424,910-byte STL**, 4.9 s |
| `projects/relief/sign.scad`, shared + local font dirs | rc 0, **426,914-byte STL**, 5.2 s |
| `projects/soft-jaw/soft_jaw.scad`, BOSL2 + fonts together | rc 0, 91,439-byte STL, 1.6 s |

## The worker

`apps/studio/src/services/engine/openscad-worker.ts`.

- A **fresh WASM instance per render** — Emscripten's `callMain()` corrupts
  internal state after the first call. The bundle is kept in worker memory and
  re-mounted each time.
- **Failure kinds** on every error message: `init-error`, `oom`, `timeout`,
  `scad-error`. Only the first three are worth retrying on the server.
- `--enable=manifold` is passed for forward compatibility. The shipped 0.0.4
  build answers `WARNING: Ignoring request to enable unknown feature 'manifold'`
  and falls through to CGAL — measured, harmless.

### The timeout lives in the caller

`instance.callMain()` is a **synchronous** call into WASM. While it runs the
worker's event loop is blocked, so a `setTimeout` armed inside the worker could
not possibly fire. The only thing that can stop a runaway render is
`worker.terminate()` from the main thread — so the clock runs in
`renderService.ts`, and the worker has no timeout logic at all.

Default 120 s; a manifest may override with
`estimate_constants.wasm_timeout_seconds`.

## Fallback, both directions

| Direction | Trigger | Why |
|---|---|---|
| server → browser | network failure, HTTP 429, `render_worker_unavailable` | free capacity the visitor already owns beats an error page |
| browser → server | `init-error`, `oom`, `timeout` | the environment failed, not the model |
| browser → server | **never** on `scad-error` | the server compiles the identical source and fails identically, for one rate-limit unit |

A browser failure is recorded per slug (rule 8), so the next render for that
cartridge goes straight to the server instead of re-running a known failure.

Neither direction fires when the visitor pinned a placement — an override or a
`browser`/`server` preference is honoured, and the failure is reported.

## Export formats are a server capability

The browser kernel produces **STL and nothing else**. `openscad-worker.ts`
renders to the single hard-coded path `/output.stl` and posts those bytes back;
there is no format argument on the worker protocol and no converter on the
browser side. `3mf`, `off` and `obj` are written by the native binary, and
`glb`, `gltf`, `step`, `vrml` and `amf` come out of trimesh or CadQuery — all
of it server-side.

So an explicit `export_format` other than `stl` is a **hard** server placement
(rule 4), above the `?render=` override and the visitor's preference. Those two
choose a placement; neither can ask the kernel for bytes it has no code to
write.

This is not a preference we are enforcing, it is a defect we were shipping.
`useRender` forwards the export panel's current format on **every** render, not
just on Download, so before rule 4 existed a browser-placed cartridge set to
`step` rendered STL, `handleDownloadStl` found no URL ending in `.step`, fell
through to the STL blob and saved it as `<slug>_<mode>_<part>.step`.

It also matters for tier gating. #87 checks the caller's tier `export_formats`
twice — when a format is GENERATED (`/api/render`, `/api/render-stream`) and
again when it is RETRIEVED (`/api/projects/<slug>/download/...`) — so that
knowing a param-hash filename is not enough to pull a format the tier may not
export. A browser render reaches neither check; it was a third door on a gate
the server keeps shut on the other two. Rule 4 puts the request back in front
of that gate.

`stl` is unaffected and stays on the free browser path — which is the common
case, since the export panel defaults to `stl`.

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

| Feature | Server | Browser |
| :--- | :--- | :--- |
| **Performance** | native (Manifold kernel where available) | ~3-5x slower, CGAL only in the 0.0.4 build |
| **Memory** | server RAM | browser tab (`TOTAL_MEMORY` 512 MB, growth allowed) |
| **Libraries** | full checkout | virtual FS populated from `/api/projects/<slug>/wasm-bundle` (transitive includes + fonts) |
| **Export** | STL, 3MF, OFF, PNG, GLB | STL |
| **Caching** | Redis / disk | IndexedDB (the studio's own render cache) |
| **Rate limit** | per tier, per hour | **none** |

## Troubleshooting

- **"Out of memory"** — the browser→server fallback handles it automatically and
  pins the cartridge to the server for the session. Reduce `fn` to get back.
- **`text()` renders nothing** — the bundle carried no `fonts`. Check the
  server's font resolution for that cartridge.
- **A cartridge that must never run client-side** — set
  `render.server_only: true` in its manifest. `force_backend` is only a hint now.
- **`SharedArrayBuffer` / `crossOriginIsolated`** — the single-threaded
  `openscad-wasm` build works without COOP/COEP headers. The probe records
  `crossOriginIsolated` for diagnosis only.
