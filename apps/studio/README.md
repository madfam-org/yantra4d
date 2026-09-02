# Yantra4D — Frontend

React SPA for the Yantra4D parametric design studio. Built with Vite, Tailwind CSS, Shadcn UI, and Three.js (via React Three Fiber).

## Setup

```bash
npm install
npm run dev       # Development server at http://localhost:5173
npm run build     # Production build to dist/
npm run preview   # Preview production build
```

## Architecture

The frontend is data-driven via a **project manifest** fetched from the backend at `/api/manifest`. See [Project Manifest docs](../../docs/reference/manifest.md) for the schema.

### Provider Hierarchy (`main.jsx`)

```
ThemeProvider → ManifestProvider → LanguageProvider → App
```

- **ManifestProvider**: Fetches manifest from API; falls back to `src/config/fallback-manifest.json`.
- **LanguageProvider**: UI chrome translations only (buttons, log messages, phase labels). Parameter labels and tooltips come from the manifest.
- **ThemeProvider**: Light / Dark / System theme persistence.

### Key Files

| File | Role |
|------|------|
| `src/App.jsx` | Main shell — state, API calls, layout, keyboard shortcuts |
| `src/components/controls/Controls.jsx` | Data-driven sliders and checkboxes for physical/geometric parameters |
| `src/components/controls/AppearancePanel.jsx` | Viewport visualization settings (lighting, wireframe, clipping, materials) |
| `src/components/bom/BomPanel.jsx` | Smart Bill of Materials parsing physical parts and required hardware |
| `src/components/Viewer.jsx` | Three.js STL viewer with camera controls and snapshot export |
| `src/contexts/ManifestProvider.jsx` | Manifest fetch, fallback, typed accessors via `useManifest()` |
| `src/config/fallback-manifest.json` | Bundled copy of `scad/project.json` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `http://localhost:5000` | Backend API base URL |
| `VITE_RENDER_MODE` | _(unset)_ | Pins the render path to `backend` or `wasm` for the whole build. Any other value is ignored. |

### Render Placement

A render runs in one of two **placements**:

- **browser** — `openscad-wasm` in a Web Worker. Free for us, unmetered for the
  visitor. **This is the default.**
- **server** — the API's native OpenSCAD/CadQuery. Costs us CPU and costs the
  visitor one of their hourly render units.

The choice is made by the pure function `decideRenderPlacement()` in
`src/services/engine/renderPlacement.ts`. Its precedence table, highest first:

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

After the table, one guard: a **soft** server decision flips back to the browser
when `/api/health` says the server is unreachable. A **hard** one never does —
the browser genuinely cannot produce that model, so the failure should name the
real problem.

`?render=backend` is deliberately exempt from that guard: support hands it out
precisely when the browser is what broke.

There is **no API-base rule**. `detectMode()` used to contain
`if (API_BASE) return 'backend'`, and production always sets `VITE_API_BASE`, so
every heuristic below that line was dead code and every visitor's render was
billed to us and metered to them. That line is gone.

#### The override

| Precedence | Mechanism | Values | Scope |
|-----------|-----------|--------|-------|
| 1 (highest) | `?render=` query param | `backend`, `wasm` | One browser session |
| 2 | `VITE_RENDER_MODE` env | `backend`, `wasm` | Whole build |

```
https://studio.yantra4d.com/project/gridfinity?render=backend
```

The value is read **once at page load**. Reload after changing it; navigating
within the app will not re-read it. Unrecognised values (`?render=serverr`) are
ignored and detection proceeds normally, so a typo degrades to the default
rather than silently pinning the wrong path.

**When support should use it:**

- `?render=backend` — the user's browser can't render: it hangs at
  "Compilando...", dies with an OpenSCAD/WASM error, or the tab runs out of
  memory on a large grid. This also stops the app from falling back to the
  browser if a server render later fails, so the user stays on the working path.
- `?render=wasm` — the server render queue is rate-limited or degraded, or you
  need to reproduce a browser-only bug on a machine the probe would route to the
  server.

Rules 1-3 override it: a CadQuery mode has no browser kernel, and `?render=wasm`
on one would trade a working render for a certain failure.

#### Engine is a MODE property

`effectiveModeEngine(manifest, modeId)` mirrors `ProjectManifest.mode_engine()`
in `apps/api/manifest.py`: an explicit `engine` on the mode wins, else the
`scad_file` extension decides (`.graph.json` → graph, `.py`/`.cq` → cadquery),
else the project engine (default `openscad`); an `implicit` project makes every
mode implicit.

This matters commercially. `gridfinity` declares `project.engine: "cadquery"`
and then three modes with `engine: "openscad"`; 8 of the 31 OpenSCAD-capable
cartridges are dual-engine like that. Reading the project engine alone would
keep every one of those modes on the metered path forever.

#### The capability probe

`src/services/engine/renderCapability.ts` classifies the device as
`capable | limited | incapable` from static signals plus a one-shot
micro-benchmark (instantiate a WASM module + render `$fn=64; cube(10);`) run in
the worker on first need. The result is cached in `localStorage` under a
versioned key and re-probed after 7 days.

Signals the browser does not expose (`deviceMemory` on Firefox and Safari, for
example) read as **unknown** — they neither promote nor demote. The old
heuristic's `navigator.deviceMemory || 4` invented a value for roughly a third
of the web.

Benchmark thresholds — `capable ≤ 600 ms`, `limited ≤ 2500 ms`, above that
`incapable` — are calibrated against the shipped `openscad-wasm@0.0.4` build,
measured at a 45 ms median (42 ms instantiate + 3 ms render) on a warm
server-class host.

#### The placement control

The sidebar's action dock shows where the render will run and why, with an
`Auto | Browser | Server` select bound to `render_placement_preference` in
`localStorage`. The **browser badge never shows a quota**, because a browser
render does not consume one.

#### Fallback, both directions

- **server → browser** on a network failure, HTTP 429, or an unhealthy render
  worker. Capacity the visitor already owns beats an error page.
- **browser → server** on `init-error`, `oom` or `timeout` (default 120 s,
  overridable with `estimate_constants.wasm_timeout_seconds`). **Not** on a SCAD
  error: the server compiles the identical source and fails identically, for the
  price of one rate-limit unit.

#### One gotcha worth knowing

The worker mounts the bundle **inside Emscripten's `preRun`**, not after
`createOpenSCAD()` resolves. `OPENSCADPATH` is read through `getenv()` and the
environment is materialised during startup, so a late assignment is ignored:
measured against `openscad-wasm@0.0.4`, `include <BOSL2/std.scad>` (the
search-path form) failed with "Can't open include file" when `ENV` was set
afterwards and rendered a 19,073-byte STL when the same assignment happened in
`preRun`. `FONTCONFIG_FILE` happens to survive the late assignment;
`OPENSCADPATH` does not.

### Updating the Fallback Manifest

When `scad/project.json` changes, copy it to the frontend:

```bash
cp scad/project.json web_interface/frontend/src/config/fallback-manifest.json
```

This ensures the app works even when the backend is unreachable.

## Testing

```bash
npm test              # Single run (Vitest)
npm run test:watch    # Watch mode
npm run test:coverage # With coverage thresholds
npm run lint          # ESLint + jsx-a11y accessibility rules
npm run analyze       # Bundle size visualization (opens stats.html)

# i18n gate (CI job `i18n-audit`): locale key parity fails hard; the hardcoded-string
# count is a ratchet against scripts/qa/i18n_baseline.json (`--update-baseline` to lower it).
python3 ../../scripts/qa/i18n_audit.py
```

### Coverage Thresholds

| Metric | Threshold |
|--------|-----------|
| Statements | 65% |
| Branches | 55% |
| Functions | 60% |
| Lines | 65% |

### Accessibility

- **Linting**: `eslint-plugin-jsx-a11y` enforces WCAG rules at lint time
- **Audits**: `jest-axe` runs axe-core checks in component tests (`it('has no a11y violations')`)

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. See the [LICENSE](../../LICENSE) file for more details.
