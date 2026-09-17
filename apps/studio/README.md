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

### Provider Hierarchy (`main.tsx`)

```
ErrorBoundary → BrowserRouter → ThemeProvider → AuthProvider → TierProvider
  → ManifestProvider → ManifestAwareLanguageProvider → PlatformProvider
    → UpgradePromptProvider → ProjectProvider → App
```

- **AuthProvider**: "Sign in with Janua" (OIDC + PKCE, see [Client authentication](#client-authentication)). Bridges the `@janua/react-sdk` session into `useAuth()`.
- **ManifestProvider**: Fetches manifest from API; falls back to `src/config/fallback-manifest.json`.
- **ManifestAwareLanguageProvider**: UI chrome translations only (buttons, log messages, phase labels). Parameter labels and tooltips come from the manifest.
- **TierProvider / UpgradePromptProvider**: entitlement tier and paywall prompts.
- **ThemeProvider**: Light / Dark / System theme persistence.

### Client authentication

Sign-in is OpenID Connect (authorization-code + PKCE) against Janua, implemented
in `src/lib/januaSso.ts` (the SDK's own `signInWithOAuth` is a social-login proxy
that does not fit a public PKCE client — see the module header). The exchanged
tokens are stored in `localStorage` under the SDK's keys (`janua_access_token`,
`janua_refresh_token`, `janua_id_token`).

Every request to the backend (`api.yantra4d.com`, audience `yantra4d-api`) must
carry that access token as a `Bearer`. Three things make that happen:

| Concern | How |
|---------|-----|
| API calls (`apiFetch`) | `services/core/apiClient.ts` injects `Authorization` from a token getter. It is registered **eagerly in `main.tsx`, before React renders** (`setTokenGetter(getStoredAccessToken)`) so the very first request — e.g. a private project's manifest on a hard load — is authenticated; the SDK's richer getter (refresh-on-expiry) replaces it once the auth context mounts. |
| Signed-in state | `AuthProvider` derives `isAuthenticated` from `hasStoredJanuaSession()`, not only the SDK's `user`. The SDK loads `user` from Janua's `/api/v1/auth/me`, which rejects a `yantra4d-api`-audience token, so a valid session would otherwise read as signed-out and the private-project gate would stay locked. |
| Mesh artifacts | The 3D viewer's `GLTFLoader`, the STL Web Worker (`workers/stlWorker.js`), and the IndexedDB render cache (`services/cache/renderCache.ts`) fetch `/static/<slug>_preview_*.glb\|.stl` **outside** `apiFetch`. Each attaches the token via `bearerHeaderForSameOrigin(url)` (januaSso) — **same-origin only**, so the `yantra4d-api` bearer never leaks to a third-party host. A private-project artifact answers 403 without it, and THREE then fails with "GLTFLoader: Unsupported asset". `renderCache` also refuses to cache a non-OK response, so an error body can never poison the L2 store.

The helpers `getStoredAccessToken()`, `hasStoredJanuaSession()` and
`bearerHeaderForSameOrigin()` live in `src/lib/januaSso.ts` and are unit-tested
in `januaSso.test.ts`.

### Key Files

| File | Role |
|------|------|
| `src/App.tsx` | Main shell — state, API calls, layout, keyboard shortcuts |
| `src/components/controls/Controls.tsx` | Data-driven sliders and checkboxes for physical/geometric parameters |
| `src/components/controls/AppearancePanel.tsx` | Viewport visualization settings (lighting, wireframe, clipping, materials) |
| `src/components/bom/BomPanel.tsx` | Smart Bill of Materials parsing physical parts and required hardware |
| `src/components/viewer/Viewer.tsx` | Three.js STL viewer with camera controls and snapshot export |
| `src/contexts/project/ManifestProvider.tsx` | Manifest fetch, fallback, typed accessors via `useManifest()` |
| `src/lib/januaSso.ts` | OIDC/PKCE sign-in, token storage, and the auth helpers (`getStoredAccessToken`, `hasStoredJanuaSession`, `bearerHeaderForSameOrigin`) |
| `src/contexts/auth/AuthProvider.tsx` | Bridges the Janua SDK session into `useAuth()`; derives `isAuthenticated` from the stored token |
| `src/services/core/apiClient.ts` | `apiFetch` — injects the `Authorization` bearer from a registered token getter |
| `src/hooks/render/useWorkerLoader.ts` | Loads a rendered mesh (GLB via `GLTFLoader`, STL via a Web Worker); attaches the bearer for same-origin, gated artifacts |
| `src/services/cache/renderCache.ts` | IndexedDB L2 cache of rendered parts; authenticates artifact fetches and never caches a non-OK response |
| `src/services/engine/renderPlacement.ts` | The pure placement policy — the precedence table above lives here |
| `src/services/engine/renderCapability.ts` | Device capability probe (`capable` / `limited` / `incapable`), cached in `localStorage` |
| `src/config/fallback-manifest.json` | Bundled copy of `projects/gridfinity/project.json` minus `project.force_backend`; kept in step by `scripts/qa/sync_fallback_manifest.py --check` (blocking in CI: `manifest-sync`) — never edit it by hand |

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
| 4 | an `export_format` the browser kernel cannot emit (anything but `stl`) | server, **hard** |
| 5 | `?render=backend` / `?render=wasm` (or `VITE_RENDER_MODE`) | server / browser |
| 6 | the visitor's `Auto / Browser / Server` preference | server / browser |
| 7 | capability tier is `incapable` | server |
| 8 | a browser render already failed for this cartridge this session | server |
| 9 | browser estimate over the tier threshold (capable 45 s, limited 15 s) | server |
| 10 | legacy `project.force_backend`, **only** on a `limited` device | server |
| 11 | **default** | **browser** |

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

npx playwright test --project=chromium  # E2E, mocked APIs
npx playwright test --project=audit     # Browser audit: REAL backend + real
                                        # OpenSCAD renders, no Docker. Needs
                                        # Redis + apps/api on :5000 + the render
                                        # worker — see the suite README below.
# i18n gate (CI job `i18n-audit`): locale key parity fails hard; the hardcoded-string
# count is a ratchet against scripts/qa/i18n_baseline.json (`--update-baseline` to lower it).
python3 ../../scripts/qa/i18n_audit.py
```

The nightly browser audit suite documents its own harness, skip helpers and
assertion conventions in
[`e2e/tests/23-browser-audit/README.md`](e2e/tests/23-browser-audit/README.md).

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
