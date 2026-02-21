# Web Interface Documentation

**Yantra4D** is a local web application for visualizing, customizing, and verifying the design.

---

## Key Features
- **Mode-Based Workflow**: Modes are defined per-project in `project.json`. For example, the gridfinity project defines Bin, Baseplate, and Lid modes.
- **Multi-Project Platform**: Serve and switch between multiple SCAD projects. See [Multi-Project Platform](./multi-project.md).
- **Data-Driven UI**: All modes, parameters, parts, camera views, parameter group labels, viewer defaults, and estimation constants are declared in a [project manifest](./manifest.md) (`projects/{slug}/project.json`). No hardcoded control definitions, camera positions, or UI labels in the frontend.
- **Interactive 3D Viewer**: Real-time rendering of generated STL files with loading progress. Uses Z-up axis convention (matching OpenSCAD) with an orientation gizmo widget.
- **3D Carousel Gallery**: Immersive browsing interface with dynamic **Level-of-Detail (LOD)**. Optimized 2D thumbnails are used for inactive items, while the active centered item triggers a live WebGL on-the-fly rendering.
- **One-Click Verification**: Run the `verify_design.py` suite directly from the UI.
- **Live Parameter Controls**: Sliders and toggles update the model dynamically (debounced auto-render).
- **Advanced Visibility**: The Visibility section has a Basic/Advanced toggle. Basic mode shows coarse toggles (Base, Walls, Mechanism, Letters, Bottom Unit, Top Unit). Advanced mode adds sub-component toggles (e.g., Left Wall, Right Wall, Base Ring, Pillars, Snap Beams) indented under their parent. In Assembly/Grid modes, Advanced also shows per-half overrides (e.g., Bottom Base, Bottom Walls). When a parent toggle is unchecked, its children are grayed out.
- **Theme Toggle**: Switch between Light, Dark, and System (Auto) modes. Preference is persisted.
- **Bilingual UI**: English and Spanish (Spanish is default). Every user-visible string is translated: buttons, labels, error messages, onboarding wizard, viewer controls, navigation, and accessibility text. Parameter labels and tooltips come from the manifest; all other UI strings come from `LanguageProvider` via the `t()` function.
- **Shareable Configuration Links**: Encode full parameter state in URL (`?p=` base64url-encoded diff against defaults). Share exact configurations via link — recipients see the same parameter values applied on load.
- **Parameter Undo/Redo**: History stack (up to 50 entries) with `Cmd+Z` / `Cmd+Shift+Z`. Undo/redo buttons also available in the header toolbar.
- **Export Capabilities**:
    - **Download STL/3MF/OFF**: Save the current model in the selected format (or ZIP for multi-part modes). Format selector appears when the manifest declares `export_formats`.
    - **Export Images**: Capture screenshots from manifest-defined camera angles (default: Isometric, Top, Front, Right).
- **Print Estimation**: Overlay on the viewer showing estimated print time, filament weight, filament length, and cost. Material selector (PLA, PETG, ABS, TPU) and infill percentage. Computed from STL geometry volume using slicer heuristics.
- **Bill of Materials (BOM)**: Manifest-driven BOM panel (`bom.hardware[]`) with quantity formulas evaluated against current parameter values via `expr-eval`. Displays item labels, computed quantities, units, and optional supplier links. Renders in the sidebar when the manifest declares a `bom` section.
- **Cross-Parameter Validation**: Manifest-driven constraints (`constraints[]`) with `rule`, `message`, `severity`, and `applies_to` fields. The `useConstraints` hook evaluates rules against current params and returns violations indexed by parameter ID. Supports `warning` and `error` severities.
- **Grid Presets**: Optional `grid_presets` manifest section provides rendering/manufacturing quality presets that override parameter values (e.g., quick preview vs. large grid).
- **Keyboard Shortcuts**: `Cmd+Z` undo, `Cmd+Shift+Z` redo, `Cmd+1..N` to switch modes, `Cmd+Enter` to generate, `Escape` to cancel.
- **SCAD Code Editor**: Monaco-based editor with file tree, syntax highlighting, tabs, auto-save and auto-render. Available for user-owned projects (GitHub-imported, forked, onboarded) at pro+ tier.
- **Git Integration**: Status, diff, commit, push/pull for GitHub-connected projects. Local git auto-initialized on first editor interaction. "Connect to GitHub" for local-only projects.
- **Fork-to-Edit**: Pro+ users can fork built-in projects to create editable copies with their own slug.
- **AI Configurator**: Natural language chat that maps to parameter changes. Available at basic+ tier on all projects. Streams responses via SSE with live slider updates.
- **AI Code Editor**: Natural language chat that generates SCAD code edits (search/replace). Available at pro+ tier in the code editor. Supports apply/reject workflow with Monaco inline diffs.

---

## Architecture

The app follows a client-server model. Configuration is centralized in a **project manifest** that both backend and frontend consume.

### Backend Structure (`apps/api/`)

```
backend/
├── app.py                # App factory, blueprint registration
├── extensions.py        # Flask extensions (rate limiter)
├── config.py             # Environment config (paths, server, AI provider settings)
├── manifest.py           # Multi-project manifest registry (ProjectManifest class)
├── requirements.txt      # Python dependencies
├── routes/
│   ├── render.py         # /api/estimate, /api/render, /api/render-stream, /api/render-cancel
│   ├── verify.py         # /api/verify
│   ├── health.py         # /api/health
│   ├── manifest_route.py # /api/manifest (default project)
│   ├── projects.py       # /api/projects, /api/projects/<slug>/manifest, /api/projects/<slug>/fork
│   ├── onboard.py        # /api/projects/analyze, /api/projects/create
│   ├── editor.py         # SCAD file CRUD (list/read/write/create/delete) with auto git-init
│   ├── git_ops.py        # Git operations (status/diff/commit/push/pull/connect-remote)
│   ├── ai.py             # AI chat SSE endpoints (session, chat-stream)
│   └── config_route.py   # /api/config (legacy, delegates to manifest)
├── services/
│   ├── openscad.py       # OpenSCAD subprocess wrapper (injects OPENSCADPATH env)
│   ├── scad_analyzer.py  # SCAD file regex analysis engine
│   ├── manifest_generator.py  # Draft manifest scaffolding from analysis
│   ├── git_operations.py # Git CLI wrappers (init/status/diff/commit/push/pull)
│   ├── ai_provider.py    # Dual LLM provider abstraction (Anthropic + OpenAI)
│   ├── ai_session.py     # In-memory conversation session store
│   ├── ai_configurator.py # NL → parameter change mapping
│   └── ai_code_editor.py # NL → SCAD code edit mapping
└── static/               # Generated STL files (runtime, namespaced by project)
```

#### Key Modules

- **`manifest.py`**: Multi-project manifest registry. `discover_projects()` scans `PROJECTS_DIR` for subdirectories with `project.json`. `get_manifest(slug)` loads and caches per-project `ProjectManifest` instances. Each manifest has a `project_dir` so SCAD paths resolve relative to the project, not a global config. Falls back to `SCAD_DIR` for single-project mode.
- **`config.py`**: Environment-level config (paths, ports, OpenSCAD binary, `STL_PREFIX`). Adds `PROJECTS_DIR` (default: `projects/`) and `MULTI_PROJECT` boolean. Adds `LIBS_DIR` / `OPENSCADPATH` for global OpenSCAD library resolution. Static methods delegate to the manifest for backward compatibility.
- **`routes/render.py`**: Accepts both `mode` (new) and `scad_file` (legacy) fields in payloads. Also accepts optional `project` slug for multi-project routing. The `_resolve_render_context()` helper resolves to the correct SCAD path and part list. STL output is namespaced by project slug.
- **`routes/projects.py`**: Lists available projects (`GET /api/projects`, supports `?stats=1` for 30-day analytics) and serves per-project manifests (`GET /api/projects/<slug>/manifest`).
- **`routes/onboard.py`**: Accepts uploaded `.scad` files for analysis (`POST /api/projects/analyze`) and creates new projects (`POST /api/projects/create`).
- **`services/scad_analyzer.py`**: Regex-based extraction of variables, modules, includes/uses, render_mode patterns, and dependency graphs from `.scad` files.
- **`services/manifest_generator.py`**: Generates draft `project.json` from analyzer output with auto-detected parameter ranges and warnings.

### API Endpoints

| Endpoint | Method | Rate Limit | Description |
|----------|--------|------------|-------------|
| `/api/projects` | GET | 500/hr | List all available projects. Append `?stats=1` for 30-day analytics counts. |
| `/api/projects/<slug>/manifest` | GET | 500/hr | Full manifest for a specific project |
| `/api/projects/analyze` | POST | 20/hr | Upload `.scad` files → analysis + draft manifest |
| `/api/projects/create` | POST | 10/hr | Create new project in `PROJECTS_DIR` |
| `/api/manifest` | GET | 500/hr | Full project manifest as JSON (default project) |
| `/api/estimate` | POST | 200/hr | Estimate render time. Accepts `mode` or `scad_file`. Optional `project` slug. |
| `/api/render` | POST | 100/hr | Synchronous render. Optional `project` slug. |
| `/api/render-stream` | POST | 100/hr | SSE progress streaming. Optional `project` slug. |
| `/api/render-cancel` | POST | 500/hr | Cancel active render |
| `/api/verify` | POST | 50/hr | Run verification suite for a mode. Optional `project` slug. |
| `/api/health` | GET | 500/hr | Health check |
| `/api/config` | GET | 500/hr | Legacy config endpoint (delegates to manifest) |
| `/api/projects/<slug>/fork` | POST | 10/hr | Fork a project (copies files to new slug, pro+) |
| `/api/projects/<slug>/files` | GET | 120/hr | List SCAD files in a project (pro+) |
| `/api/projects/<slug>/files/<path>` | GET/PUT/DELETE | 120/hr | Read/write/delete SCAD files (pro+) |
| `/api/projects/<slug>/git/status` | GET | 60/hr | Git working tree status (pro+) |
| `/api/projects/<slug>/git/diff` | GET | 60/hr | Unified diff (pro+) |
| `/api/projects/<slug>/git/commit` | POST | 30/hr | Stage files and commit (pro+) |
| `/api/projects/<slug>/git/push` | POST | 20/hr | Push to origin (pro+, GitHub token required) |
| `/api/projects/<slug>/git/pull` | POST | 20/hr | Pull from origin (pro+, GitHub token required) |
| `/api/projects/<slug>/git/connect-remote` | POST | 10/hr | Add/set GitHub remote URL (pro+) |
| `/api/ai/session` | POST | 30/hr | Create AI chat session (basic+) |
| `/api/ai/chat-stream` | POST | dynamic | SSE streaming AI chat (basic+ configurator, pro+ code-editor) |

#### Payload Examples

**Estimate / Render (new style)**:
```json
{ "mode": "grid", "rows": 4, "cols": 4, "rod_extension": 10 }
```

**Render with export format**:
```json
{ "mode": "unit", "export_format": "3mf", "project": "my-project" }
```
Supported formats: `stl` (default), `3mf`, `off`. Invalid formats fall back to `stl`.

**Estimate / Render (multi-project)**:
```json
{ "mode": "grid", "rows": 4, "cols": 4, "rod_extension": 10, "project": "my-project" }
```

**Estimate / Render (legacy)**:
```json
{ "scad_file": "yantra4d_cup.scad", "width_units": 2, "depth_units": 1, "height_units": 3 }
```

All styles are supported. When `mode` is present, `scad_file` is resolved automatically from the manifest. The optional `project` field routes to the correct project in multi-project mode.

**Verify**:
```json
{ "mode": "unit" }
```

**Verify (multi-project)**:
```json
{ "mode": "unit", "project": "my-project" }
```

**Render Cancel** (no body required):
```
POST /api/render-cancel
```

#### Response Examples

**Render (success)**:
```json
{
  "status": "success",
  "parts": [
    { "type": "main", "url": "http://localhost:5000/static/preview_main.stl", "size_bytes": 12345 }
  ],
  "log": "[main] Compiling design...\n"
}
```

**Render (error)**:
```json
{ "status": "error", "error": "OpenSCAD failed: syntax error" }
```

**Estimate**:
```json
{ "estimated_seconds": 45.2, "num_parts": 2, "num_units": 4 }
```

**Verify**:
```json
{
  "status": "success",
  "output": "--- main ---\n[PASS] ...",
  "passed": true,
  "parts_checked": 1
}
```

**Health**:
```json
{ "status": "healthy", "openscad_available": true, "scad_dir_exists": true }
```

#### Error Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Invalid input (missing JSON body, unknown SCAD file, invalid parameters) |
| 404 | Unknown endpoint |
| 500 | Render failure or internal error |

All error responses use a consistent JSON envelope:
```json
{ "status": "error", "error": "Human-readable message" }
```

Global handlers for 400, 404, and 500 ensure this format even for unhandled Flask errors.

**Note on `/api/render-stream`**: Input validation errors (missing body, invalid SCAD file) return a standard HTTP 400 JSON response *before* opening the SSE stream. Only valid requests upgrade to `text/event-stream`.

#### Error Handling

- **Manifest loading**: If `projects/{slug}/project.json` (or `scad/project.json` in single-project mode) is missing or contains invalid JSON, the backend raises a `RuntimeError` at startup with a descriptive message.
- **Frontend fallback**: If the `/api/manifest` fetch fails (backend unavailable or network error), `ManifestProvider` logs a warning and uses the bundled `fallback-manifest.json`. This enables static/offline deploys.
- **Render service**: The frontend checks `response.ok` before reading the SSE stream and throws if the backend returns an error status. Malformed SSE lines are logged with `console.warn` and skipped. An empty stream (no parts produced) throws an error.
- **Verify service**: Client-side verification checks `response.ok` when fetching STL files and reports fetch failures per-part in the verification output.

#### Rate Limiting

All endpoints enforce per-IP rate limits via Flask-Limiter (`extensions.py`). Default: 500 requests/hour. Expensive endpoints have stricter limits:
- **Render**: 100/hr (render + render-stream)
- **Estimate**: 200/hr
- **Verify**: 50/hr
- **Project Analysis**: 20/hr
- **Project Creation**: 10/hr

Rate-limited responses return HTTP 429 with a `Retry-After` header.

#### Security Headers

Production nginx (`nginx.conf`) adds:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy`: restricts sources; allows `wasm-unsafe-eval` (OpenSCAD WASM), `blob:` (web workers), `unsafe-inline` in styles (Tailwind), `data:` images (Three.js textures)

#### Timeout Behavior

- Backend synchronous render: `subprocess.run(timeout=300)` kills OpenSCAD after 300s; gunicorn also enforces 300s
- Backend verification: `subprocess.run(timeout=120)` kills the verify script after 120s
- SSE streaming: `Popen` subprocess; gunicorn worker timeout applies (300s)
- WASM rendering: no timeout (runs in browser worker)
- Frontend manifest fetch: `AbortSignal.timeout(2000)` — falls back to bundled manifest on timeout

---

### Frontend Structure (`apps/studio/src/`)

```
src/
├── App.jsx                        # Main shell: state, API calls, layout (lazy-loads ProjectsView, OnboardingWizard)
├── main.jsx                       # Entry point: provider hierarchy
├── components/
│   ├── Controls.jsx               # Data-driven parameter + color controls
│   ├── Viewer.jsx                 # Three.js 3D viewer (STLLoader, Z-up)
│   ├── viewer/
│   │   ├── AnimatedGrid.jsx       # Animated grid preview (Z-rotation per cube)
│   │   ├── SceneController.jsx    # Camera view switching (data-driven from manifest)
│   │   └── NumberedAxes.jsx       # Labeled XYZ axis lines with tick marks
│   ├── ProjectSelector.jsx        # Multi-project dropdown (visible when >1 project)
│   ├── OnboardingWizard.jsx       # 4-step SCAD project onboarding wizard
│   ├── BomPanel.jsx               # Manifest-driven bill of materials panel
│   ├── ConfirmRenderDialog.jsx    # Long-render confirmation dialog
│   ├── PrintEstimateOverlay.jsx   # Print time/filament/cost overlay on viewer
│   ├── ErrorBoundary.jsx          # React error boundary (accepts `t` prop for i18n)
│   ├── ScadEditor.jsx             # Monaco-based SCAD code editor with file tree and tabs
│   ├── GitPanel.jsx               # Git status, diff, commit, push/pull, connect-remote
│   ├── AiChatPanel.jsx            # AI chat UI (configurator + code-editor modes)
│   ├── ForkDialog.jsx             # Fork-to-edit modal for built-in projects
│   └── ui/                        # Shadcn UI primitives
├── contexts/
│   ├── ManifestProvider.jsx       # Fetches /api/manifest, bundled fallback
│   ├── LanguageProvider.jsx       # i18n for UI chrome strings
│   └── ThemeProvider.jsx          # Light/Dark/System theme
├── hooks/
│   ├── useRender.js               # Render orchestration (generate, cancel, cache, confirm)
│   ├── useConstraints.js          # Manifest constraint evaluation (rule + severity + applies_to)
│   ├── useImageExport.js          # PNG snapshot export for camera views
│   ├── useLocalStoragePersistence.js # Debounced localStorage sync
│   ├── useShareableUrl.js         # Shareable URL generation (base64url param encoding)
│   ├── useUndoRedo.js             # Parameter undo/redo with 50-entry history stack
│   ├── useProjectMeta.js          # Fetch project.meta.json for source type detection
│   ├── useEditorRender.js         # Debounced save + auto-render for editor changes
│   └── useAiChat.js               # AI chat state management hook (both modes)
├── lib/
│   ├── openscad-phases.js         # Shared OpenSCAD phase detection (main + worker)
│   ├── stl-utils.js               # Binary STL parser + bounding box
│   ├── printEstimator.js          # Print time/filament/cost estimation from STL geometry
│   └── downloadUtils.js           # File/ZIP download helpers
├── services/
│   ├── renderService.js           # Dual-mode render (backend SSE / WASM worker)
│   ├── backendDetection.js        # Backend availability check + API base URL
│   ├── openscad-worker.js         # Web Worker for OpenSCAD WASM rendering
│   ├── verifyService.js           # STL verification client
│   ├── assemblyFetcher.js         # Assembly STL fetcher for animated preview
│   ├── editorService.js           # SCAD file CRUD API client
│   ├── gitService.js              # Git operations API client
│   └── aiService.js               # AI chat API client (SSE consumer)
└── config/
    └── fallback-manifest.json     # Bundled copy of projects/gridfinity/project.json
```

#### Provider Hierarchy

```
<ThemeProvider>
  <ManifestProvider>                    ← fetches manifest, provides useManifest()
    <ManifestAwareLanguageProvider>     ← derives storageKey from projectSlug
      <App />
    </ManifestAwareLanguageProvider>
  </ManifestProvider>
</ThemeProvider>
```

#### Key Components

- **`ManifestProvider.jsx`**: Fetches `/api/projects` on mount to discover available projects, then fetches `/api/projects/{slug}/manifest` for the active project. On failure, falls back to the bundled `fallback-manifest.json`. All accessor functions are memoized with `useCallback`; the provider `value` is wrapped in `useMemo`. Exposes: `manifest`, `loading`, `getMode()`, `getParametersForMode()`, `getPartColors()`, `getDefaultParams()`, `getDefaultColors()`, `getLabel()`, `getCameraViews()`, `getGroupLabel()`, `getViewerConfig()`, `getEstimateConstants()`, `projectSlug`, `projects`, `switchProject()`.
- **`Controls.jsx`**: Fully data-driven. Reads `getParametersForMode(mode)` and `getPartColors(mode)` from the manifest. Renders sliders, checkboxes (grouped by `param.group`), color pickers, and custom widgets dynamically. Supports `widget: { type: "color-gradient" }` for dual-color picker with gradient preview (used in polydice for two-tone dice). Supports click-to-edit numeric input on slider values. Accessible: sliders carry `aria-label` matching the parameter name; value displays have descriptive `aria-label` with parameter name and current value, `role="button"`, and keyboard support.
- **`App.jsx`**: Uses `projectSlug` for all localStorage keys and export filenames. Sends `{ ...params, mode }` in render payloads. Dynamic `Cmd+1..N` shortcuts for however many modes the manifest declares.
- **`LanguageProvider.jsx`**: Contains all UI chrome translations (buttons, log messages, phases, view labels, theme labels, error boundary text, viewer controls, navigation, onboarding wizard, and accessibility strings). Every user-visible string in the frontend is bilingual (es/en) via the `t()` function. Parameter labels, tooltips, tab names, and color labels come from the manifest.
- **`AnimatedGrid.jsx`**: Renders an animated grid of cubes for preview. Grid pitch formula matches the backend (`size × √2 + rotation_clearance`). Columns spread along the Y axis; rows stack along Z with tubing spacer gaps (`r × (size + tubing_H) + tubing_H`). Each cube plays a sequential 90° Z-rotation animation.
- **`Viewer.jsx`**: Colors parts by looking up `colors[part.type]`; falls back to `manifest.viewer.default_color`. Camera views (iso/top/front/right) and their positions are read from `manifest.camera_views`, not hardcoded. Uses **Z-up** axis convention to match OpenSCAD (camera `up=[0,0,1]`, grid on XY plane). Includes a `GizmoHelper` orientation widget (bottom-left) and an internal `ViewerErrorBoundary` class for graceful 3D rendering error recovery.
- **`ProjectCarousel3D.jsx`**: Implements a large-scale horizontal scrolling scene using `@react-three/drei`'s `ScrollControls`. It manages the spatial distribution of 36+ projects in a unified 3D space.
- **`CarouselItem.jsx`**: The core LOD component. It uses `useFrame` to calculate its distance from the world center. When centered, it activates a `LiveModel` component which fetches a high-fidelity GLTF/GLB from the `/api/render` endpoint.

---

## 3D Performance Engine (LOD Strategy)

Yantra4D implements a "Zero-Waste" rendering strategy for the project gallery:

1. **Phase 1: Thumbnail Cold Storage**: Inactive carousel items render a single `Image` plane using the project's pre-rendered thumbnail. This keeps the draw call count low.
2. **Phase 2: Live Hydration**: As a project scrolls into the center (Active Zone), the `CarouselItem` triggers a backend render request with default parameters.
3. **Phase 3: GLTF Seamless Swap**: Once the backend produces a GLTF/GLB blob, the UI swaps the 2D plane for a live 3D mesh. 
4. **Phase 4: Turntable Interaction**: Active models auto-rotate on a turntable and respond to scale/parallax animations based on scroll position.

This architecture allows the platform to showcase 36+ complex parametric models in a single scene without browser memory exhaustion.

#### Build Optimization

The frontend build uses Vite with manual chunk splitting:
- `vendor-react`: React + ReactDOM (~193KB, gzip ~61KB)
- `vendor-three`: Three.js (~722KB, gzip ~188KB)
- `vendor-r3f`: React Three Fiber + Drei (~381KB, gzip ~128KB)
- `vendor-ui`: Radix UI primitives (~60KB, gzip ~19KB)
- Lazy-loaded routes: `ProjectsView` (~4KB), `OnboardingWizard` (~7KB)

Run `npm run analyze` to generate an interactive bundle visualization at `dist/stats.html`.

#### Accessibility

- **ESLint**: `eslint-plugin-jsx-a11y` enforces WCAG accessibility rules at lint time
- **Runtime audits**: `jest-axe` runs axe-core accessibility checks in component tests
- **ARIA**: Sliders carry `aria-label`/`aria-labelledby`; checkboxes have explicit `aria-label`; color inputs linked via `htmlFor`/`id`; form inputs labeled

---

## Running the App

### Development Mode
```bash
./scripts/dev.sh              # start backend (Flask :5000) + frontend (Vite :5173)
./scripts/dev-stop.sh         # stop all dev servers
./scripts/dev.sh --frontend-only  # frontend only (e.g. for WASM-only mode)
```
Access: http://localhost:5173

### Production Mode
```bash
# Backend with gunicorn
cd apps/api
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 app:app

# Frontend (build + serve)
cd apps/studio
npm run build
npm run preview
```

### Docker
```bash
docker compose up --build     # start
docker compose down           # stop
```
Access: http://localhost:3000 (frontend) / http://localhost:5000 (backend)

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECTS_DIR` | `projects/` (at repo root) | Directory containing project subdirectories (multi-project mode) |
| `SCAD_DIR` | `../../scad` (relative to backend) | Path to SCAD files and `project.json` (single-project fallback) |
| `OPENSCAD_PATH` | `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD` | Path to OpenSCAD binary |
| `LIBS_DIR` | `libs/` (at repo root) | Directory containing global OpenSCAD libraries (BOSL2, NopSCADlib, etc.) |
| `OPENSCADPATH` | value of `LIBS_DIR` | OpenSCAD library search path, injected into render subprocesses |
| `VERIFY_SCRIPT` | `../../tests/verify_design.py` | Path to verification script |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `PORT` | `5000` | Backend server port |
| `HOST` | `0.0.0.0` | Backend bind address |
| `VITE_API_BASE` | `http://localhost:5000` | Frontend → backend API base URL |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed CORS origins for backend |
| `AI_PROVIDER` | `anthropic` | AI provider: `anthropic` or `openai` |
| `AI_API_KEY` | (none) | API key for the configured AI provider |
| `AI_MODEL` | (auto) | Model override (defaults: `claude-sonnet-4-20250514` / `gpt-4o`) |
| `AI_MAX_TOKENS` | `2048` | Maximum tokens per AI response |

[Back to Index](./index.md)
