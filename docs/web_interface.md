# Web Interface Documentation

**Tablaco Studio** is a local web application for visualizing, customizing, and verifying the design.

---

## Key Features
- **Three-Mode Workflow**:
    1.  **Unit Mode**: Visualize and verify a single `half_cube` unit. Adjust Size, Thickness, Rod Diameter, and Primitive Visibility.
    2.  **Assembly Mode**: Preview how two half-cubes fit together (bottom + top parts).
    3.  **Grid Mode**: Generate a full `tablaco` grid assembly. Adjust Rows, Columns, and Rod Extension.
- **Data-Driven UI**: All modes, parameters, parts, camera views, parameter group labels, viewer defaults, and estimation constants are declared in a [project manifest](./manifest.md) (`scad/project.json`). No hardcoded control definitions, camera positions, or UI labels in the frontend.
- **Interactive 3D Viewer**: Real-time rendering of generated STL files with loading progress. Uses Z-up axis convention (matching OpenSCAD) with an orientation gizmo widget.
- **One-Click Verification**: Run the `verify_design.py` suite directly from the UI.
- **Live Parameter Controls**: Sliders and toggles update the model dynamically (debounced auto-render).
- **Theme Toggle**: Switch between Light, Dark, and System (Auto) modes. Preference is persisted.
- **Bilingual UI**: English and Spanish (Spanish is default). Parameter labels and tooltips come from the manifest; UI chrome strings come from `LanguageProvider`.
- **Export Capabilities**:
    - **Download STL**: Save the current model as an STL file (or ZIP for multi-part modes).
    - **Export Images**: Capture screenshots from manifest-defined camera angles (default: Isometric, Top, Front, Right).
- **Keyboard Shortcuts**: `Cmd+1..N` to switch modes, `Cmd+Enter` to generate, `Escape` to cancel.

---

## Architecture

The app follows a client-server model. Configuration is centralized in a **project manifest** that both backend and frontend consume.

### Backend Structure (`web_interface/backend/`)

```
backend/
├── app.py                # App factory, blueprint registration
├── config.py             # Environment config (paths, server settings)
├── manifest.py           # Project manifest loader (ProjectManifest class)
├── requirements.txt      # Python dependencies
├── routes/
│   ├── render.py         # /api/estimate, /api/render, /api/render-stream, /api/render-cancel
│   ├── verify.py         # /api/verify
│   ├── health.py         # /api/health
│   ├── manifest_route.py # /api/manifest
│   └── config_route.py   # /api/config (legacy, delegates to manifest)
├── services/
│   └── openscad.py       # OpenSCAD subprocess wrapper
└── static/               # Generated STL files (runtime)
```

#### Key Modules

- **`manifest.py`**: Loads `scad/project.json` and exposes a `ProjectManifest` class with typed accessors: `get_allowed_files()`, `get_parts_map()`, `get_mode_map()`, `get_scad_file_for_mode()`, `get_parts_for_mode()`, `calculate_estimate_units()`. The manifest is loaded once and cached.
- **`config.py`**: Environment-level config (paths, ports, OpenSCAD binary). Static methods delegate to the manifest for backward compatibility.
- **`routes/render.py`**: Accepts both `mode` (new) and `scad_file` (legacy) fields in payloads. The `_resolve_render_context()` helper resolves both to the correct SCAD path and part list.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/manifest` | GET | Full project manifest as JSON |
| `/api/estimate` | POST | Estimate render time. Accepts `mode` or `scad_file`. |
| `/api/render` | POST | Synchronous render |
| `/api/render-stream` | POST | SSE progress streaming. Accepts `mode` or `scad_file`. |
| `/api/render-cancel` | POST | Cancel active render |
| `/api/verify` | POST | Run verification suite for a mode |
| `/api/health` | GET | Health check |
| `/api/config` | GET | Legacy config endpoint (delegates to manifest) |

#### Payload Examples

**Estimate / Render (new style)**:
```json
{ "mode": "grid", "rows": 4, "cols": 4, "rod_extension": 10 }
```

**Estimate / Render (legacy)**:
```json
{ "scad_file": "tablaco.scad", "rows": 4, "cols": 4, "rod_extension": 10 }
```

Both styles are supported. When `mode` is present, `scad_file` is resolved automatically from the manifest.

**Verify**:
```json
{ "mode": "unit" }
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

- **Manifest loading**: If `scad/project.json` is missing or contains invalid JSON, the backend raises a `RuntimeError` at startup with a descriptive message.
- **Frontend fallback**: If the `/api/manifest` fetch fails (backend unavailable or network error), `ManifestProvider` logs a warning and uses the bundled `fallback-manifest.json`. This enables GitHub Pages / static deploys.
- **Render service**: The frontend checks `response.ok` before reading the SSE stream and throws if the backend returns an error status. Malformed SSE lines are logged with `console.warn` and skipped. An empty stream (no parts produced) throws an error.
- **Verify service**: Client-side verification checks `response.ok` when fetching STL files and reports fetch failures per-part in the verification output.

#### Timeout Behavior

- Backend synchronous render: Flask default timeout (no limit, but gunicorn uses 300s)
- SSE streaming: `proxy_read_timeout 300s` in nginx config
- WASM rendering: no timeout (runs in browser worker)

---

### Frontend Structure (`web_interface/frontend/src/`)

```
src/
├── App.jsx                        # Main shell: state, API calls, layout
├── main.jsx                       # Entry point: provider hierarchy
├── components/
│   ├── Controls.jsx               # Data-driven parameter + color controls
│   ├── Viewer.jsx                 # Three.js 3D viewer (STLLoader, Z-up)
│   ├── viewer/
│   │   ├── SceneController.jsx    # Camera view switching (data-driven from manifest)
│   │   └── NumberedAxes.jsx       # Labeled XYZ axis lines with tick marks
│   ├── ConfirmRenderDialog.jsx    # Long-render confirmation dialog
│   ├── ErrorBoundary.jsx          # React error boundary
│   └── ui/                        # Shadcn UI primitives
├── contexts/
│   ├── ManifestProvider.jsx       # Fetches /api/manifest, bundled fallback
│   ├── LanguageProvider.jsx       # i18n for UI chrome strings
│   └── ThemeProvider.jsx          # Light/Dark/System theme
└── config/
    └── fallback-manifest.json     # Bundled copy of scad/project.json
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

- **`ManifestProvider.jsx`**: Fetches `/api/manifest` on mount. On failure, falls back to the bundled `fallback-manifest.json`. Exposes: `manifest`, `loading`, `getMode()`, `getParametersForMode()`, `getPartColors()`, `getDefaultParams()`, `getDefaultColors()`, `getLabel()`, `getCameraViews()`, `getGroupLabel()`, `getViewerConfig()`, `getEstimateConstants()`, `projectSlug`.
- **`Controls.jsx`**: Fully data-driven. Reads `getParametersForMode(mode)` and `getPartColors(mode)` from the manifest. Renders sliders, checkboxes (grouped by `param.group`), and color pickers dynamically. Supports click-to-edit numeric input on slider values.
- **`App.jsx`**: Uses `projectSlug` for all localStorage keys and export filenames. Sends `{ ...params, mode }` in render payloads. Dynamic `Cmd+1..N` shortcuts for however many modes the manifest declares.
- **`LanguageProvider.jsx`**: Contains only UI chrome translations (buttons, log messages, phases, view labels). All parameter labels, tooltips, tab names, and color labels come from the manifest.
- **`Viewer.jsx`**: Colors parts by looking up `colors[part.type]`; falls back to `manifest.viewer.default_color`. Camera views (iso/top/front/right) and their positions are read from `manifest.camera_views`, not hardcoded. Uses **Z-up** axis convention to match OpenSCAD (camera `up=[0,0,1]`, grid on XY plane). Includes a `GizmoHelper` orientation widget (bottom-left) and an internal `ViewerErrorBoundary` class for graceful 3D rendering error recovery.

---

## Running the App

### Development Mode
```bash
# Terminal 1: Backend
python3 web_interface/backend/app.py

# Terminal 2: Frontend
cd web_interface/frontend
npm run dev
```
Access: http://localhost:5173

### Production Mode
```bash
# Backend with gunicorn
cd web_interface/backend
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 app:app

# Frontend (build + serve)
cd web_interface/frontend
npm run build
npm run preview
```

### Docker
```bash
docker-compose up --build
```
Access: http://localhost:3000 (frontend) / http://localhost:5000 (backend)

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAD_DIR` | `../../scad` (relative to backend) | Path to SCAD files and `project.json` |
| `OPENSCAD_PATH` | `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD` | Path to OpenSCAD binary |
| `VERIFY_SCRIPT` | `../../tests/verify_design.py` | Path to verification script |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `PORT` | `5000` | Backend server port |
| `HOST` | `0.0.0.0` | Backend bind address |
| `VITE_API_BASE` | `http://localhost:5000` | Frontend → backend API base URL |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed CORS origins for backend |

[Back to Index](./index.md)
