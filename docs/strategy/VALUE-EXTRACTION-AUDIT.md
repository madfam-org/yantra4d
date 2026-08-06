# Yantra4D Value-Extraction Audit — Verified Findings

**Method:** 7 auditors mined the codebase + 300-object commons across parity, data-insight,
dead-capability, and quality fronts; every finding was then **adversarially verified** against
the real code/data (skeptic by default). Result: **40 findings — 12 CONFIRMED, 28 PARTIAL, 2
REFUTED.** Only verified findings appear below, ranked by ROI-per-effort. Every row cites
file:line evidence checked today. Marketing language avoided; corrections from verification folded in.

## The 2 REFUTED (do NOT chase — they're already done)
- **"Presets aren't enumerated anywhere"** — FALSE. `PresetGallery.tsx` + `StorefrontView.tsx`
  enumerate presets *within an object* and load/share them. (The real gap is *cross-catalog*
  preset browse — see #7.)
- **"camera_views are a dead capability"** — FALSE. 883 camera_views across 293 manifests already
  power a live in-viewer guided-view switcher via `ManifestProvider.getCameraViews`. (The real gap
  is they don't drive auto-thumbnails — see #10, lower ROI.)

## Ranked opportunities (verified)

| # | Opportunity | Effort | ROI | Verified evidence | What it unlocks |
|---|---|---|---|---|---|
| 1 | **Declare `reportlab` in requirements.txt** — datasheet PDF export silently falls back to HTML in prod/CI/fresh installs because the (complete, finished) `_generate_pdf()` in `datasheet.py:47-115` is import-gated and the dep is undeclared | S | high | `reportlab` absent from `apps/api/requirements.txt`; `datasheet.py:20-29` `HAS_REPORTLAB` gate; `:171` defaults fmt→html | The spec-sheet/BOM PDF deliverable actually generates for every user |
| 2 | **Retarget AI synthesizer + code-editor to CadQuery** — `ai_synthesizer.py:18-50` hardcodes "OpenSCAD code files" / `main.scad`; `ai_code_editor.py:30,50` says "modify OpenSCAD"; `ScadEditor.tsx` forces `.scad`. In a now-CadQuery-first 300-object repo, AI authoring emits the wrong kernel | S–M | exceptional | cited lines; repo is CadQuery-first (300 cartridges `engine:cadquery`) | AI-authored objects land in the right kernel + inside the commons conventions (self-growing commons) |
| 3 | **Mount the send-to-printer panel** — `PrintPanel.tsx` is a complete OctoPrint/Moonraker panel (fetch printers, live status, dispatch/cancel via `/api/printers/*`; backend `moonraker.py`/`octoprint.py` real) — imported and mounted NOWHERE | S | high | `PrintPanel.tsx` 0 importers; `printer.py` 4 endpoints registered `app.py:57,223` | Direct print-to-printer from Studio — a whole built feature at 0 value today |
| 3b | **Mount the Animation panel** — `AnimationPanel.tsx` (355 lines, play/pause/scrub/render/export, 8 tests) is unmounted; only 1/326 objects even declares animations | S (mount) / M (make useful) | medium | grep: `AnimationPanel` unmounted across `apps/` | Turntable/param-sweep animation export |
| 4 | **Material-aware discovery facet** — 310 objects carry `hyperobject.material_awareness` (+ `tolerance_by_material`); `catalog_index.py:_build_record` extracts NO material key, so no filter/badge exists | M | high | `catalog_index.py:101-124` has no material field | "Objects that adapt to / are printable in material X"; surface the material-hyperawareness thesis |
| 5 | **Standards / families browse directory** — a 61-key family taxonomy (`_FAMILY_PATTERNS`, `normalize_family()`) exists but is used ONLY by the graph; 55 families cover ~98 objects; `/api/catalog/search?standard=` facet exists but there's no standards *directory* nav | S–M | high | `compatibility_graph.py` family taxonomy; `/api/catalog/families` endpoint exists, no UI | "Browse everything that speaks NEMA / VESA / GHT" — the interoperability catalog |
| 6 | **Fix 4 half-empty locales + gate i18n audit in CI** — `de/fr/pt/zh.json` each ~25% `[UNTRANSLATED]`; `resolveTranslation` (LanguageProvider.tsx:27) renders the marker verbatim (truthy → English fallback never fires); `scripts/qa/i18n_audit.py` runs in NO CI workflow | S (CI gate) / M (translate) | high | i18n_audit.py reports 47 strings + exits 1; 4 locales ~79 markers each | Honest language switcher; unblocks claimed non-en/es markets |
| 7 | **Cross-catalog preset browse** (corrected from "unbuilt") — per-object preset load/share works (`PresetGallery`); what's missing is a *commons-wide* preset index/API to browse proven configs across objects | M | high | 303/326 manifests carry presets (1,021 total); no cross-object aggregation in `catalog*.py` | "Browse the commons by proven outcome, not just by object" |
| 8 | **Migrate landing gallery to `/api/catalog/search`** — `ProjectGalleryContainer.tsx:13-38` filters a static `data/projects.ts` client-side on only search+category+domain; the new API offers server-side standard/geometry/difficulty facets | M | high | landing imports static PROJECTS; catalog API has richer facets | One discovery source of truth; standard/geometry facets on the public site |
| 9 | **Compatibility GRAPH map UI** — `/api/catalog/graph` returns full nodes+edges (degree, shared standard); `WorksWithPanel` consumes only the per-object `/works-with` slice; the whole-graph map has 0 consumers | M | medium–high | `compatibility.py` graph endpoint, 0 UI refs | A visual, demoable interoperability map (the moat, made visible) |
| 10 | **camera_views → auto-thumbnails** (corrected: not dead, just not driving thumbnails) — reuse the 883 curated angles to render per-object hero thumbnails, replacing/augmenting the SVG placeholders | M | medium | camera_views live in viewer, not in thumbnail pipeline | Real curated thumbnails instead of placeholders |
| 11 | **Constraint-driven live validation coverage** — 555 bilingual constraints across 287 objects; a live-validation UI exists but ~94% of constraints are effectively unexercised in discovery/UX | M | medium | 287/326 carry constraints | Fewer bad renders; smarter parameter UIs |
| 12 | **Zero test coverage on `/simulate/*` + `stress_analyzer.py`** — a real 5-endpoint pro-gated blueprint (stress proxy is genuine trimesh+numpy) has NO tests anywhere under `apps/api/tests` | M | medium | grep: no test references simulate_bp | Safety net on a live pro feature |
| 13 | **`ManifestProvider.tsx:112` typecheck error** — `tsc --noEmit -p tsconfig.ci.json` exits 2 (TS2352, fallback-manifest constraints shape) | S | low–medium | running typecheck reproduces it | Green strict CI |

## Honest "not worth it yet"
- **Physics / FEA / topology-opt** (`simulate/physics`, `optimizer.py`): the optimizer computes a
  closed-form heuristic vs a hardcoded target (`optimizer.py:58,108`), not a real solve; physics
  worker emits synthetic frames. README already labels these mocks. Real solving needs GPU infra —
  correctly skip; at most gate/relabel so they don't read as real.
- **ForgeSight/cotiza quote export**: backend is mature (`cotiza_export.py`, 502 lines) but it's an
  external-integration path, not maker-facing discovery value — lower priority than the above.

## Build order (highest ROI-per-effort first)
Quick wins (S, ship immediately): **#1 reportlab**, **#3 mount PrintPanel**, **#6 i18n CI gate**,
**#13 typecheck**. Then high-ROI data-insight (S–M): **#5 standards/families browse**, **#4 material
facet**. Then **#2 AI→CadQuery**, **#8 landing→catalog API**, **#7 preset browse**, **#9 graph map**.

## SHIPPED (this session, all verified green)
- ✅ **#1** `reportlab` declared in requirements.txt — datasheet PDF now generates in prod.
- ✅ **#3** Send-to-printer `PrintPanel` mounted in the export tab (was built, mounted nowhere).
- ✅ **#4** Material-aware discovery facet — the data is boolean capability flags (not material
  names, as the audit prompt guessed); shipped as a capability facet (tolerance_by_material 294 /
  shrinkage_compensation 30 / recycled_material_toggle 16). Backend index + facet + filter + UI.
- ✅ **#5** "Browse by standard" families directory (`StandardsBrowser.tsx`) — 61-key family
  taxonomy surfaced; inline-expand members, links to each object.
- ✅ **#11** Live constraint validation **activated** — the evaluator read `constraint.rule` but all
  555 authored constraints use `expression`, so validation was silently dead for all 300 objects.
  Now reads `expression` + derives `applies_to`. (This also root-caused #13.)
- ✅ **#13** Long-standing `ManifestProvider.tsx:112` typecheck error fixed (same constraint-shape
  root cause) — typecheck now exit 0.
- ✅ **+ isolation flake** caught during integration: the ProjectsView "clear pill" test raced the
  debounced-refetch loading state across files; fixed with `findByRole` (retries).

Verification: backend 29 tests + ruff clean; frontend full suite **1548 tests** green; typecheck exit
0; locale parity 327 keys × 6. **Remaining queued:** #2 AI→CadQuery, #6 locales + i18n CI gate,
#7 preset browse, #8 landing→catalog API, #9 graph map, #12 simulate/* test coverage.
