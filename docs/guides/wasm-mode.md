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
| 4 | `?render=backend` / `?render=wasm` (or `VITE_RENDER_MODE`) | server / browser |
| 5 | the visitor's `Auto / Browser / Server` preference | server / browser |
| 6 | capability tier is `incapable` | server |
| 7 | a browser render already failed for this cartridge this session | server |
| 8 | browser estimate over the tier threshold (capable 45 s, limited 15 s) | server |
| 9 | legacy `project.force_backend`, **only** on a `limited` device | server |
| 10 | **default** | **browser** |

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

A browser failure is recorded per slug (rule 7), so the next render for that
cartridge goes straight to the server instead of re-running a known failure.

Neither direction fires when the visitor pinned a placement — an override or a
`browser`/`server` preference is honoured, and the failure is reported.

## Limitations

| Feature | Server | Browser |
| :--- | :--- | :--- |
| **Performance** | native (Manifold kernel where available) | ~3-5x slower, CGAL only in the 0.0.4 build |
| **Memory** | server RAM | browser tab (`TOTAL_MEMORY` 512 MB, growth allowed) |
| **Libraries** | full checkout | whatever the bundle carries |
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
