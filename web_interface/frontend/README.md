# Tablaco Studio — Frontend

React SPA for the Tablaco parametric design studio. Built with Vite, Tailwind CSS, Shadcn UI, and Three.js (via React Three Fiber).

## Setup

```bash
npm install
npm run dev       # Development server at http://localhost:5173
npm run build     # Production build to dist/
npm run preview   # Preview production build
```

## Architecture

The frontend is data-driven via a **project manifest** fetched from the backend at `/api/manifest`. See [Project Manifest docs](../../docs/manifest.md) for the schema.

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
| `src/components/Controls.jsx` | Data-driven sliders, checkboxes, color pickers from manifest |
| `src/components/Viewer.jsx` | Three.js STL viewer with camera controls and snapshot export |
| `src/contexts/ManifestProvider.jsx` | Manifest fetch, fallback, typed accessors via `useManifest()` |
| `src/config/fallback-manifest.json` | Bundled copy of `scad/project.json` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `http://localhost:5000` | Backend API base URL |

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
