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

### Render Mode Override

The studio renders either in the browser (`wasm`) or on the server (`backend`).
By default it picks for you from the device's core count and memory
(`hardwareConcurrency >= 4 && deviceMemory >= 4` → WASM). The override forces
one path instead.

| Precedence | Mechanism | Values | Scope |
|-----------|-----------|--------|-------|
| 1 (highest) | `?render=` query param | `backend`, `wasm` | One browser session |
| 2 | `VITE_RENDER_MODE` env | `backend`, `wasm` | Whole build |
| 3 | hardware heuristic | — | Per device |

```
https://studio.yantra4d.com/project/gridfinity?render=backend
```

The value is read **once at page load**. Reload after changing it; navigating
within the app will not re-read it. Unrecognised values (`?render=serverr`) are
ignored and detection proceeds normally, so a typo degrades to the default
rather than silently pinning the wrong path.

**When support should use it:**

- `?render=backend` — the user's browser can't run WASM: renders hang at
  "Compilando...", die with an OpenSCAD/WASM error, or the tab runs out of
  memory on a large grid. This also stops the app from falling back to WASM if a
  backend render later fails, so the user stays on the working path.
- `?render=wasm` — the server render queue is rate-limited or degraded and the
  user's machine is capable, or you need to reproduce a WASM-only bug on a
  machine the heuristic would route to the backend.

Two cases the override cannot change: projects whose engine is `cadquery` or
`graph` always render on the backend (no browser kernel exists), and a project
manifest's `force_backend` still applies where the override is absent.

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
