# Yantra4D Platform — Full Codebase Audit

> **Date**: 2026-02-05
> **Scope**: Complete platform assessment — architecture, components, tests, quality, roadmap
> **Branch**: `main` (commit `45d3f66`)

---

## 1. Executive Summary

**Yantra4D** is a manifest-driven parametric 3D print design platform that turns OpenSCAD models into interactive web configurators. End-users adjust sliders, pick presets, and export production-ready STL/3MF files — with zero code required.

The platform currently ships **20 built-in parametric projects** across three web applications (API backend, Studio frontend, marketing landing page), with dual rendering (server-side OpenSCAD CLI + client-side WASM fallback), integrated STL verification, AI-assisted editing, multi-language UI (6 languages), and a full CI/CD pipeline deploying to three subdomains.

**Phase 1** (quick wins) and **Phase 2** (medium-term features) are complete. Phase 3 (storefront mode, auto-assembly, component catalog, gear migration) is planned.

**Competitive moat** — four pillars no single competitor matches:
1. Zero-code project onboarding (manifest + SCAD = working configurator)
2. Dual rendering (backend + WASM fallback)
3. Integrated verification pipeline
4. Multi-project management with BOM, assembly, and constraints

---

## 2. Architecture Overview

| Tier | Directory | Stack | Key Counts |
|------|-----------|-------|------------|
| **Backend** | `apps/api/` | Flask 3, OpenSCAD CLI, Gunicorn, trimesh | 18 routes, 14 services, 1 middleware |
| **Studio** | `apps/studio/` | React 19, Vite 7, Three.js 0.182, Shadcn UI | 34 components, 14 hooks, 9 services, 6 contexts |
| **Landing** | `apps/landing/` | Astro 5, React islands, Tailwind | 13 components (11 Astro + 2 React TSX) |
| **Shared** | `packages/` | JSON Schema, CSS tokens | 1 schema, 1 token file |
| **Projects** | `projects/` | OpenSCAD + JSON manifests | 20 projects, 48 SCAD files (excl. vendor) |
| **Libraries** | `libs/` | Git submodules | 6 global SCAD libraries |
| **Infrastructure** | `.github/`, Docker, Enclii | GitHub Actions, Docker Compose | 1 CI workflow (4 jobs), 3 Dockerfiles, 3 deploy configs |

**Domains**: `yantra4d.quest` (landing) · `studio.yantra4d.quest` (studio) · `api.yantra4d.quest` (API)

---

## 3. Component Inventory

### 3.1 Backend — API (`apps/api/`)

#### Routes (18 files)

| File | Endpoints | Purpose |
|------|-----------|---------|
| `health.py` | `GET /api/health` | Service health check, OpenSCAD availability |
| `manifest_route.py` | `GET /api/manifest` | Fetch project manifest (cached) |
| `config_route.py` | `GET /api/config` | Legacy config endpoint (delegates to manifest) |
| `render.py` | `POST /api/estimate`, `/api/render`, `/api/render-stream`, `/api/render-cancel` | Core render pipeline with SSE streaming and cancellation |
| `verify.py` | `POST /api/verify` | STL geometry quality validation |
| `projects.py` | `GET /api/projects`, `/api/projects/<slug>/manifest`, `/api/projects/<slug>/stats` | Multi-project listing, manifest fetch, stats |
| `onboard.py` | `POST /api/projects/analyze`, `/api/projects/create` | Project onboarding wizard (SCAD upload → manifest) |
| `editor.py` | `GET/PUT/POST/DELETE /api/projects/<slug>/files/*` | SCAD file CRUD within projects |
| `ai.py` | `POST /api/ai/session`, `/api/ai/chat` | AI chat sessions with SSE streaming |
| `github.py` | `POST /api/github/validate`, `/api/github/import`, `/api/github/sync` | GitHub repo import and sync |
| `git_ops.py` | `GET/POST /api/projects/<slug>/git/*` | Git status, diff, commit, push, pull |
| `admin.py` | `POST /api/admin/clear-cache`, `/api/admin/override-tier` | Admin operations |
| `download.py` | `GET /api/download/stl/<part>`, `/api/download/scad/<file>` | Auth-gated file downloads |
| `bom.py` | `GET /api/projects/<slug>/bom` | Bill of materials CSV export |
| `datasheet.py` | `GET /api/projects/<slug>/datasheet` | Project datasheet PDF generation |
| `analytics.py` | `POST /api/analytics` | Privacy-respecting render/export analytics (SQLite) |
| `user.py` | `GET /api/user/me` | User profile from JWT claims |
| `__init__.py` | — | Package init |

#### Services (14 files)

| File | Purpose |
|------|---------|
| `openscad.py` | OpenSCAD subprocess wrapper: CLI builder, streaming, cancellation |
| `scad_analyzer.py` | Regex-based SCAD parsing: variables, modules, includes, render modes |
| `manifest_generator.py` | Draft manifest creation from SCAD analysis |
| `render_cache.py` | Thread-safe LRU cache (hash-keyed, 1hr TTL, 200 entry limit) |
| `git_operations.py` | Git CLI wrappers: status, diff, commit, push, pull |
| `github_import.py` | GitHub repo cloning, SCAD discovery, private repo auth |
| `github_token.py` | GitHub token extraction from JWT claims |
| `ai_provider.py` | Dual LLM abstraction (Anthropic + OpenAI) with streaming |
| `ai_configurator.py` | NL → parameter mapping with validation |
| `ai_code_editor.py` | NL → SCAD code edits (search/replace) |
| `ai_session.py` | In-memory conversation store (1hr auto-expire) |
| `tier_service.py` | Tier definitions loader, user tier resolution, feature gating |
| `route_helpers.py` | Shared utilities: error responses, STL cleanup, JSON validation |
| `__init__.py` | Package init |

#### Middleware (1 file)

| File | Purpose |
|------|---------|
| `middleware/auth.py` | JWT auth via Janua JWKS; `@optional_auth`, `@require_auth`, `@require_tier` decorators |

#### Core Config

| File | Purpose |
|------|---------|
| `app.py` | Flask factory, CORS, 17 blueprints, global error handlers |
| `config.py` | Environment config (paths, auth, tiers, AI providers) |
| `extensions.py` | Flask-Limiter (500/hr global; memory backend) |
| `manifest.py` | Manifest loader with caching, multi-project discovery, validation |
| `pyproject.toml` | pytest config, coverage threshold: **80%** |

#### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flask | ~3.0 | Web framework |
| flask-cors | ~4.0 | CORS headers |
| flask-limiter | ~3.5 | Rate limiting |
| gunicorn | ~21.0 | Production WSGI server |
| trimesh | ~4.0 | STL mesh operations |
| numpy | ~1.24 | Numerical computing |
| networkx | ~3.0 | Graph algorithms (SCAD analysis) |
| PyJWT[crypto] | >=2.8.0 | JWT validation |
| requests | ~2.31 | HTTP client |
| anthropic | >=0.40 | Claude API |
| openai | >=1.50 | OpenAI API |
| python-dotenv | ~1.0 | .env loading |

---

### 3.2 Studio — Frontend (`apps/studio/`)

#### Components (34 files, excluding `ui/` and tests)

| Component | Purpose |
|-----------|---------|
| `App.jsx` | Main shell; routes ProjectsView vs Studio; lazy-loads panels |
| `StudioHeader.jsx` | Top nav: theme/language toggles, undo/redo, share, fork, editor toggle |
| `StudioSidebar.jsx` | Left panel: mode selector, controls, presets, render, export, assembly editor |
| `StudioMainView.jsx` | Layout for Viewer + ConsolePanel |
| `Viewer.jsx` | Three.js canvas: STL preview, orbit controls, grid, axes, part highlighting |
| `Controls.jsx` | Data-driven param UI: sliders, toggles, color pickers, gradients (reads manifest) |
| `ProjectSelector.jsx` | Multi-project switching dropdown |
| `ProjectsView.jsx` | Project gallery/dashboard: listing, sorting, thumbnails |
| `OnboardingWizard.jsx` | Multi-step wizard: SCAD upload → analysis → manifest editing → save |
| `GitHubImportWizard.jsx` | Import projects from GitHub repositories |
| `ForkDialog.jsx` | Fork/duplicate a project |
| `ScadEditor.jsx` | Monaco editor for OpenSCAD: syntax highlighting, file tabs, diff view |
| `GitPanel.jsx` | Git version control: status, commit history, diffs |
| `AiChatPanel.jsx` | AI configurator chat: parameter suggestions via Claude API |
| `ExportPanel.jsx` | Export controls: STL/3MF/OBJ format selection, download triggers |
| `PrintEstimateOverlay.jsx` | Print time, filament weight, cost estimates from geometry |
| `BomPanel.jsx` | Bill of Materials display with quantities |
| `AssemblyView.jsx` | Step-by-step assembly visualization |
| `ComparisonView.jsx` | Side-by-side parameter/design comparison |
| `AuthButton.jsx` | Login/logout button |
| `AuthGate.jsx` | Auth-protected feature wrapper |
| `ErrorBoundary.jsx` | React error boundary with crash display |
| `DemoBanner.jsx` | Demo mode indicator banner |
| `RateLimitBanner.jsx` | Rate limit warning banner |
| `ConfirmRenderDialog.jsx` | Confirmation for long-running renders |
| `PluginLoader.jsx` | Dynamic plugin/extension component loader |
| `viewer/SceneController.jsx` | Three.js scene state: camera, lighting, post-processing |
| `viewer/AnimatedGrid.jsx` | Animated floor grid with perspective effect |
| `viewer/NumberedAxes.jsx` | XYZ axes with labels and dimension lines |
| `assembly-editor/AssemblyEditorPanel.jsx` | Assembly editor UI container |
| `assembly-editor/AssemblyEditorToolbar.jsx` | Assembly editor action toolbar |
| `assembly-editor/StepList.jsx` | Assembly step list with reordering |
| `assembly-editor/StepDetailForm.jsx` | Assembly step edit form |
| `assembly-editor/PartVisibilityPicker.jsx` | Part visibility toggle UI |
| `assembly-editor/CameraCaptureButton.jsx` | Camera snapshot for step thumbnails |

#### Shadcn UI Primitives (13 files in `ui/` — DO NOT EDIT)

`alert-dialog`, `button`, `card`, `checkbox`, `input`, `label`, `sheet`, `slider`, `sonner`, `switch`, `tabs`, `textarea`, `tooltip`

#### Hooks (14 files)

| Hook | Purpose |
|------|---------|
| `useAppState.js` | Master orchestrator: render params, undo/redo, presets, sharing |
| `useRender.js` | STL rendering via backend/WASM |
| `useRenderQueue.js` | Render queue with priority/cancellation |
| `useConstraints.js` | Parameter constraint validation |
| `useUndoRedo.js` | Parameter undo/redo history (50-entry stack) |
| `useShareableUrl.js` | Encode/decode shareable URLs (base64url diffs) |
| `useLocalStoragePersistence.js` | Persist state to localStorage |
| `useImageExport.js` | Three.js canvas → PNG/JPEG export |
| `useEditorRender.js` | Trigger render on code/parameter changes |
| `useAssemblyEditor.js` | Assembly step state and CRUD |
| `useAiChat.js` | AI chat session state and messages |
| `useProjectMeta.js` | Fetch project metadata (thumbnails, descriptions) |
| `useAnalytics.js` | Event tracking |
| `useTier.js` | User tier/subscription status |

#### Services (9 files)

| Service | Purpose |
|---------|---------|
| `renderService.js` | Dual-mode STL rendering (backend or WASM); SSE streaming |
| `apiClient.js` | Shared fetch wrapper: Bearer token injection, rate limit tracking |
| `verifyService.js` | STL quality checking |
| `aiService.js` | Claude API integration for AI configurator |
| `gitService.js` | Git operations (commit, diff, history) |
| `editorService.js` | Monaco editor utilities (diff, syntax highlighting) |
| `openscad-worker.js` | Web Worker for WASM OpenSCAD (offline mode) |
| `backendDetection.js` | Backend availability detection, API base URL |
| `assemblyFetcher.js` | Assembly instructions and BOM from API |

#### Contexts (6 files)

| Context | Purpose |
|---------|---------|
| `ManifestProvider.jsx` | Fetches/provides manifest; multi-project support |
| `ThemeProvider.jsx` | Light/dark/system theme |
| `LanguageProvider.jsx` | Multi-language i18n (6 languages: en, es, de, fr, pt, zh) |
| `ManifestAwareLanguageProvider.jsx` | Composes Manifest + Language contexts |
| `AuthProvider.jsx` | JWT auth, Janua integration |
| `TierProvider.jsx` | User subscription tier state |

#### Libraries & Utilities (12 files in `lib/`)

| File | Purpose |
|------|---------|
| `printEstimator.js` | Volume, bounding box, print time/filament/cost from STL geometry |
| `downloadUtils.js` | Blob download and ZIP creation |
| `monacoAiDiff.js` | AI-powered diff/inline edits for Monaco editor |
| `stl-utils.js` | STL parsing and geometry utilities |
| `scad-language.js` | OpenSCAD syntax definitions for Monaco |
| `openscad-phases.js` | Parse OpenSCAD compile phases from logs |
| `utils.js` | Shared utility (`cn` for Tailwind class merging) |

#### Key Dependencies

| Package | Version |
|---------|---------|
| react | 19.2.0 |
| three | 0.182.0 |
| @react-three/fiber | 9.5.0 |
| @react-three/drei | 10.7.7 |
| @monaco-editor/react | 4.7.0 |
| vite | 7.2.4 |
| tailwindcss | 3.4.19 |
| openscad-wasm | 0.0.4 |
| manifold-3d | 3.3.2 |
| @radix-ui/react-* | 1.x (13 packages) |
| lucide-react | 0.563.0 |
| sonner | 2.0.7 |
| expr-eval | 2.0.2 |
| jszip | 3.10.1 |

---

### 3.3 Landing — Marketing Site (`apps/landing/`)

#### Components (13 files)

| Component | Type | Purpose |
|-----------|------|---------|
| `Header.astro` | Astro | Navigation bar with logo, menu, theme toggle, language selector |
| `Hero.astro` | Astro | Main headline, CTA, feature highlights |
| `HowItWorks.astro` | Astro | Step-by-step platform guide |
| `BeforeAfter.astro` | Astro | Visual comparison slider |
| `InteractiveShowcase.tsx` | React | Iframe embed of studio with project tabs |
| `ProjectGalleryGrid.tsx` | React | Gallery grid with thumbnails and metadata |
| `OpenSource.astro` | Astro | Open-source libraries section |
| `ForCreators.astro` | Astro | Value prop for creators/makers |
| `ForMakers.astro` | Astro | Value prop for engineers |
| `LiveDemo.astro` | Astro | Live demo embed section |
| `ProjectGallery.astro` | Astro | Project listing container |
| `CallToAction.astro` | Astro | Bottom CTA with signup |
| `Footer.astro` | Astro | Footer with links and copyright |

**Pages**: `index.astro` (single-page site composing all components)

**Key Dependencies**: Astro 5.7.0, React 19.2.0, Three.js 0.182.0, Tailwind 3.4.19

---

### 3.4 Shared Packages (`packages/`)

| Package | File | Purpose |
|---------|------|---------|
| schemas | `project-manifest.schema.json` | JSON Schema validating `project.json` manifests |
| tokens | `colors.css` | Shared CSS custom properties (imported by both studio and landing) |

### 3.5 Scripts & Tools

| File | Purpose |
|------|---------|
| `scripts/dev.sh` | Start all dev servers (API :5000, Studio :5173, Landing :4321) |
| `scripts/dev-stop.sh` | Kill all dev processes and clean PID files |
| `scripts/generate-thumbnails.js` | Generate project thumbnails from STL files |
| `tools/yantra4d-init` | CLI for onboarding external SCAD projects |

### 3.6 Locales

| Language | Code | File |
|----------|------|------|
| English | en | `src/locales/en.json` |
| German | de | `src/locales/de.json` |
| French | fr | `src/locales/fr.json` |
| Portuguese | pt | `src/locales/pt.json` |
| Chinese (Simplified) | zh | `src/locales/zh.json` |

Spanish is listed as a language code (`es` in `languages.js`) but handled by the landing site and parameter descriptions in manifests.

---

## 4. Test & Quality Health Report

### 4.1 Backend Tests

| Metric | Value |
|--------|-------|
| Test files | 35 (32 `test_*.py` + `conftest.py` + `verify_design.py` + `__init__.py`) |
| Coverage threshold | **80%** (enforced via `pyproject.toml` `fail_under`) |
| Framework | pytest + pytest-cov |
| Linting | ruff |
| Dependency audit | pip-audit (warn, don't fail) |

**Test Categories**:

| Category | Files | Coverage Area |
|----------|-------|---------------|
| Render & Export | 4 | Render endpoint, streaming, cache, verification |
| Projects & Manifest | 5 | Listing, stats, creation, manifest loading, onboarding |
| OpenSCAD & SCAD | 3 | Subprocess, CLI building, SCAD analysis |
| Git & GitHub | 5 | Git operations, GitHub import, token extraction |
| AI Services | 5 | Chat endpoints, code editor, configurator, provider, sessions |
| Auth & Admin | 4 | JWT validation, admin ops, user profile, tier service |
| File I/O & Downloads | 3 | Downloads, SCAD editor CRUD, forking |
| Analytics & Utilities | 3 | Analytics, BOM, datasheet |
| Infrastructure | 2 | Health check, conftest fixtures |

### 4.2 Studio Unit Tests

| Metric | Value |
|--------|-------|
| Test files | 52 |
| Framework | Vitest + React Testing Library + jest-axe |
| Coverage thresholds | Statements: **80%**, Lines: **82%**, Branches: **65%**, Functions: **73%** |
| Environment | jsdom |
| Accessibility | jest-axe audits in component tests |

**Coverage Exclusions**: `node_modules/`, `src/test/`, `src/components/ui/`, `*.test.*`, `src/locales/`, `fallback-manifest.json`

### 4.3 E2E Tests

| Metric | Value |
|--------|-------|
| Test suites | 18 |
| Framework | Playwright |
| Browsers | Chromium, Firefox, WebKit |
| Mobile | Pixel 5 (responsive suite) |
| Reports | HTML report, JSON output |
| CI status | **Not yet in CI pipeline** |

**E2E Suites**:

| # | Suite | Focus |
|---|-------|-------|
| 01 | Navigation | Project selection, view switching, URL navigation |
| 02 | Header | Logo, menu, language, theme toggle |
| 03 | Sidebar | Parameter controls, panel collapse/expand |
| 04 | Viewer | Model loading, pan/zoom/rotate, view presets |
| 05 | Export | Format selection, download, file validation |
| 06 | Print Estimate | Time/weight/cost calculations, material selection |
| 07 | Projects View | Project listing, switching, filtering |
| 08 | Onboarding | File upload, manifest generation, parameter setup |
| 09 | Keyboard | Undo/Redo, parameter navigation, modals |
| 10 | Rendering | Render trigger, mode selection, parameter re-render |
| 11 | Shareable URLs | Base64url encoding, link restoration |
| 12 | Responsive | Touch controls, responsive grid, sidebar collapse |
| 13 | Accessibility | WCAG compliance, ARIA labels, semantic HTML |
| 14 | i18n | Language switching, translation, locale persistence |
| 15 | Theme | Dark/light toggle, localStorage, system preference |
| 16 | Error Handling | Network failures, timeouts, rate limiting |
| 17 | Auth | Login/logout, token handling, auth-gated endpoints |
| 18 | Visual Regression | Screenshot comparisons across routes and states |

### 4.4 Landing Tests

| Method | Detail |
|--------|--------|
| Build validation | `npm run build` (Astro static build) in CI |
| Unit/E2E tests | None (appropriate for static marketing site) |

### 4.5 CI/CD Pipeline

**Workflow**: `.github/workflows/ci.yml` — triggers on push/PR to `main`

| Job | Steps | Enforces |
|-----|-------|----------|
| `studio` | npm ci → npm audit → lint → test:coverage | ESLint, Vitest coverage thresholds |
| `landing` | npm ci → npm run build | Astro build succeeds |
| `backend` | pip install → pip-audit → ruff check → pytest --cov | ruff linting, 80% coverage |
| `manifest-sync` | JSON diff of gridfinity manifest vs fallback | Manifests in sync |

### 4.6 Code Quality Summary

| Metric | Status |
|--------|--------|
| Backend coverage | 80%+ enforced |
| Studio coverage | 80%/82%/65%/73% enforced |
| E2E tests written | 18 suites |
| E2E in CI | Not yet |
| Linting (JS) | ESLint + jsx-a11y |
| Linting (Python) | ruff |
| Dependency audit | npm audit + pip-audit (warnings only) |
| Accessibility | jest-axe audits + ESLint jsx-a11y |
| Pre-commit hooks | Husky + lint-staged (ESLint fix + Vitest on changed files) |
| Manifest validation | CI diff check (gridfinity ↔ fallback) |

### 4.7 Health Score

| Area | Score | Notes |
|------|-------|-------|
| Backend testing | 9/10 | Strong: 80%+ coverage, 35 test files, all routes covered |
| Studio testing | 9/10 | Strong: 80%+ thresholds, 52 test files, accessibility audits |
| E2E testing | 7/10 | Good: 18 suites written but not yet in CI |
| Landing testing | 5/10 | Adequate: build-only validation, no component tests |
| Code quality | 9/10 | Excellent: dual linting, pre-commit hooks, dependency audits |
| CI/CD | 8/10 | Solid: 4-job pipeline, auto-deploy; E2E integration pending |

---

## 5. Project Catalog

### 19 Built-in Projects

| # | Slug | Description | SCAD Files | Exports | Vendor | Docs | Features |
|---|------|-------------|-----------|---------|--------|------|----------|
| 1 | `portacosas` | Portable container system | 3 | Yes | — | — | BOM, constraints |
| 2 | `gridfinity` | Grid-based storage system | 3 | Yes | Yes | — | BOM, assembly, constraints |
| 4 | `gear-reducer` | Gear reduction system | 3 | — | — | — | Multi-mode |
| 5 | `gears` | Basic gear generation | 2 | Yes | — | — | — |
| 6 | `voronoi` | Voronoi pattern generator | 3 | — | — | — | Multi-mode |
| 7 | `maze` | Parametric maze generator | 3 | — | — | — | Multi-mode |
| 8 | `relief` | Relief/embossing generator | 3 | — | — | — | Multi-mode |
| 9 | `fasteners` | Hardware fastener library | 2 | Yes | — | — | — |
| 10 | `motor-mount` | Motor mounting bracket | 1 | Yes | — | — | — |
| 11 | `spiral-planter` | Spiral parametric planter | 1 | — | — | — | — |
| 12 | `julia-vase` | Generative vase from Julia sets | 1 | Yes | — | — | — |
| 13 | `superformula` | Superformula shape generator | 1 | — | — | — | — |
| 14 | `torus-knot` | Torus knot generator | 1 | — | — | — | — |
| 15 | `polydice` | Parametric dice generator | 1 | Yes | Yes | — | color-gradient widget |
| 16 | `keyv2` | Mechanical keyboard keycap | 1 | Yes | Yes | — | — |
| 17 | `multiboard` | Parametric pegboard | 1 | Yes | Yes | — | — |
| 18 | `stemfie` | Open-source building system | 3 | Yes | Yes | — | Multi-mode |
| 19 | `ultimate-box` | Universal box generator | 1 | Yes | Yes | — | — |
| 20 | `yapp-box` | Yet Another Parametric Box | 2 | Yes | Yes | — | — |

**Totals**: 48 SCAD files (excluding vendor), 14 with exports, 7 with vendor submodules, 1 with docs

### Global SCAD Libraries (`libs/`)

| Library | License | Purpose |
|---------|---------|---------|
| BOSL2 | BSD-2 | Attachments, rounding, math, gears |
| NopSCADlib | GPL-3 | Real-world hardware models |
| Round-Anything | MIT | Coordinate-based filleting |
| dotSCAD | Apache-2 | Turtle graphics, function-based geometry |
| threads-scad | Public Domain | Thread generation |
| MCAD | LGPL-2 | Legacy OpenSCAD component library |

---

## 6. Documentation Inventory

### Platform Documentation (`docs/`)

| File | Lines | Purpose | Quality |
|------|-------|---------|---------|
| `index.md` | 52 | Documentation hub, platform overview | Adequate — links to other docs |
| `manifest.md` | 290 | Manifest schema, parameter types, modes, UI controls | Excellent — detailed with examples |
| `web_interface.md` | 389 | Full-stack architecture, component maps, render pipeline | Excellent — exhaustive reference |
| `verification.md` | 130 | STL quality verification algorithm, design rules | Good — complete |
| `devx-guide.md` | 107 | Developer experience: setup, linting, testing, workflow | Good — practical |
| `roadmap.md` | 94 | Phase 3–4 feature planning, priority matrix | Good — high-level |
| `competitive-landscape.md` | 165 | 18+ projects researched, positioning, feature comparison | Good — strategic |
| `multi-project.md` | 90 | PROJECTS_DIR setup, discovery, fallback behavior | Good — clear |

**Total**: 1,317 lines across 8 docs

### Project-Specific Documentation

| Project | File | Content |
|---------|------|---------|
### Other Documentation

| File | Purpose |
|------|---------|
| `CLAUDE.md` | AI assistant instructions — full architecture guide |
| `README.md` | Repository overview, quick start, tech stack |
| `claudedocs/usability-audit.md` | Usability audit notes |

### Documentation Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| Per-project documentation (19 projects lack docs) | Medium — onboarding friction for contributors | Medium |
| WASM/offline mode guide | Low — works automatically but undocumented | Low |
| AI features documentation (configurator, code editor) | Medium — new features without user guide | Medium |
| Troubleshooting guide | Medium — common issues undocumented | Medium |
| API authentication guide (Janua setup) | Low — internal only | Low |

---

## 7. Feature Implementation Status

### Phase 1: Quick Wins — All Implemented

| Feature | Status | Key Files |
|---------|--------|-----------|
| 1.1 Shareable Configuration Links | Implemented | `useShareableUrl.js`, `App.jsx` |
| 1.2 Parameter Undo/Redo | Implemented | `useUndoRedo.js` |
| 1.3 Multi-Format Export (STL/3MF/OFF) | Implemented | `ExportPanel.jsx`, render routes |
| 1.4 Print-Time & Filament Estimation | Implemented | `printEstimator.js`, `PrintEstimateOverlay.jsx` |

### Phase 2: Medium-Term — 4/5 Implemented

| Feature | Status | Key Files |
|---------|--------|-----------|
| 2.1 Bill of Materials (BOM) | Implemented | `BomPanel.jsx`, `bom.py`, manifest `bom` field |
| 2.2 Assembly Instructions | Implemented | `AssemblyView.jsx`, assembly-editor/, manifest `assembly_steps` |
| 2.3 Project Gallery | Partial | `ProjectsView.jsx` exists but lacks thumbnail/tags/difficulty fields |
| 2.4 Cross-Parameter Validation | Implemented | `useConstraints.js`, manifest `constraints` field |
| 2.5 Plugin System | Partial | `PluginLoader.jsx`, `color-gradient` widget implemented |

### Phase 2 Add-ons (Beyond Original Roadmap)

| Feature | Status | Key Files |
|---------|--------|-----------|
| AI-Assisted SCAD Editing | Implemented | `ScadEditor.jsx`, `AiChatPanel.jsx`, `ai_*.py` services |
| AI Parameter Configurator | Implemented | `ai_configurator.py`, `aiService.js` |
| GitHub Import | Implemented | `GitHubImportWizard.jsx`, `github.py`, `github_import.py` |
| Git Operations (commit/push/pull) | Implemented | `GitPanel.jsx`, `git_ops.py`, `git_operations.py` |
| SCAD Code Editor | Implemented | `ScadEditor.jsx`, `editor.py`, Monaco integration |
| JWT Authentication (Janua) | Implemented | `AuthProvider.jsx`, `middleware/auth.py` |
| Tiered Access Control | Implemented | `TierProvider.jsx`, `tier_service.py` |
| Datasheet Generation | Implemented | `datasheet.py` route |
| Analytics | Implemented | `analytics.py`, `useAnalytics.js` |
| Fork/Duplicate Projects | Implemented | `ForkDialog.jsx` |

### Phase 3: Long-Term — Planned

| Feature | Impact | Effort | Status |
|---------|--------|--------|--------|
| 3.1 Product Configurator Storefront | High | Large | Planned — requires customer view, PDF gen, payment |
| 3.2 BOSL2 Attachment-Aware Auto-Assembly | Medium | Medium | Planned — scad_analyzer extension |
| 3.3 NopSCADlib Component Catalog Widget | Medium | Medium | Planned — hardware selector UI |
| 3.4 MCAD → BOSL2 Gear Migration | Low | Small | Planned — BOSL2 already available |

---

## 8. Strategic Position & Vision

### Competitive Landscape

18+ open-source projects analyzed across 8 categories. Key findings:

| Competitor | Strengths | Weaknesses vs Yantra4D |
|-----------|-----------|----------------------|
| OpenSCAD Playground | Monaco editor, community | Code-centric, no configurator UX |
| OpenJSCAD | Native JS, modular | Dev-focused, not a platform |
| Manifold CAD | Fast geometry kernel | Low-level, not a configurator |
| NopSCADlib | BOM, assembly docs, parts | Not web-based, code-driven |
| CadQuery/build123d | Powerful parametric scripting | No web UI |
| FreeCAD/SolveSpace | Professional features | Desktop-only, heavyweight |
| Thingiverse Customizer | Large user base | Deprecated/broken |

### Four Pillars of Differentiation

1. **Zero-Code Onboarding**: Manifest + SCAD files = working web configurator
2. **Dual Rendering**: Server-side OpenSCAD CLI + client-side WASM fallback
3. **Verification Pipeline**: Automated STL quality checks before export
4. **Multi-Project Platform**: 20 projects managed from single installation with shared libraries

### What We Deliberately Don't Build

| Feature | Rationale |
|---------|-----------|
| Code editor as primary UX | Contradicts configurator identity |
| Constraint-based sketch modeling | Different paradigm entirely |
| STEP/IGES import | Irrelevant to configurator users |
| Real-time collaborative editing | Shareable links cover 80% of need at 5% cost |
| Python/JS scripting | Fragments platform identity |

### Phase 3 Priority Matrix

| Feature | Impact | Effort | Dependencies |
|---------|--------|--------|--------------|
| Storefront Mode | High | Large | access_control, PDF gen |
| Auto-Assembly | Medium | Medium | scad_analyzer extension |
| Component Catalog | Medium | Medium | NopSCADlib metadata parser |
| MCAD→BOSL2 Gears | Low | Small | None |

---

## 9. Gaps & Recommendations

### High Priority

| Gap | Detail | Effort |
|-----|--------|--------|
| E2E tests in CI | 18 Playwright suites exist but aren't in the CI pipeline | Small — add job to `ci.yml` |
| Complete component test coverage | Some components lack tests (ComparisonView, PluginLoader, GitHubImportWizard) | Medium |
| Landing page tests | Build-only validation; no component tests | Medium — add Vitest for React islands |

### Medium Priority

| Gap | Detail | Effort |
|-----|--------|--------|
| Per-project documentation | 19 of 20 projects lack `docs/` | Medium — templated per project |
| WASM mode documentation | Auto-detection works but undocumented | Small |
| AI feature documentation | Configurator/code editor lack user guides | Small |
| Troubleshooting guide | Common issues (render timeouts, CORS, submodules) | Small |
| Project gallery completion | Thumbnail, tags, difficulty fields not populated | Medium |

### Low Priority

| Gap | Detail | Effort |
|-----|--------|--------|
| API contract testing | No OpenAPI spec or contract tests | Medium |
| Performance benchmarks | No baseline render time benchmarks | Medium |
| TypeScript migration for services | JS services could benefit from type safety | Large |
| Rate limiting backend (Redis) | Memory-based limiter doesn't share across workers | Medium |
| Landing i18n | No dedicated i18n system in landing app | Medium |

---

## 10. Quick Reference

### File Counts

| Category | Count |
|----------|-------|
| Backend routes | 18 |
| Backend services | 14 |
| Backend test files | 35 |
| Studio components (excl. ui) | 34 |
| Studio hooks | 14 |
| Studio services | 9 |
| Studio contexts | 6 |
| Studio test files | 52 |
| E2E test suites | 18 |
| Landing components | 13 |
| Shadcn UI primitives | 13 |
| Built-in projects | 20 |
| SCAD files (excl. vendor) | 48 |
| Global SCAD libraries | 6 |
| Documentation files | 8 |
| CI/CD jobs | 4 |
| Docker services | 3 |
| Supported UI languages | 5 (en, de, fr, pt, zh) |
| Git submodules | 13 (6 libs + 7 vendor) |

### Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROJECTS_DIR` | `projects/` | Multi-project root directory |
| `SCAD_DIR` | `projects/gridfinity` | Single-project fallback |
| `OPENSCAD_PATH` | Auto-detected | OpenSCAD binary path |
| `CORS_ORIGINS` | `localhost:5173,localhost:3000` | Allowed CORS origins |
| `AUTH_ENABLED` | `true` | Enable JWT authentication |
| `JANUA_ISSUER` | `https://auth.madfam.io` | Auth provider URL |
| `JANUA_AUDIENCE` | `yantra4d` | JWT audience |
| `FLASK_DEBUG` | `false` | Flask debug mode |
| `PORT` | `5000` | API server port |

### API Endpoint Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/manifest` | Project manifest |
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/<slug>/manifest` | Project-specific manifest |
| POST | `/api/estimate` | Render time estimate |
| POST | `/api/render` | Synchronous render |
| POST | `/api/render-stream` | SSE streaming render |
| POST | `/api/render-cancel` | Cancel active render |
| POST | `/api/verify` | STL quality check |
| POST | `/api/projects/analyze` | Analyze uploaded SCAD |
| POST | `/api/projects/create` | Create new project |
| POST | `/api/ai/chat` | AI chat (SSE) |
| GET | `/api/projects/<slug>/bom` | Bill of materials |

### Dev Commands

```bash
# Start all dev servers
./scripts/dev.sh

# Stop all dev servers
./scripts/dev-stop.sh

# Run backend tests
cd apps/api && pytest --cov

# Run studio tests
cd apps/studio && npm run test:coverage

# Run E2E tests
cd apps/studio && npx playwright test

# Run studio lint
cd apps/studio && npm run lint

# Run backend lint
cd apps/api && ruff check .

# Docker (all services)
docker compose up --build

# Onboard external SCAD project
tools/yantra4d-init ./path/to/scad-dir --slug my-project --install
```

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| Render | 100/hr |
| Estimate | 200/hr |
| Verify | 50/hr |
| Global | 500/hr |

---

*Generated 2026-02-05 from commit `45d3f66` on `main` branch.*
