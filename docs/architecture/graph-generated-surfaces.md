# Graph-generated surfaces (RFC 0067, phase P0, surfaces half)

Last Updated: 2026-11-20

Every hyperobject in the solid, soft and sheet commons gets a configurable graph, and its
configurator, graph view and per-node preview are **generated from that graph**, designed once
per platform through impeccable and machine-checked per cartridge in CI. This document is the
Yantra4D record of phase P0's surfaces half: what was decided, the contract the graph must meet,
how the shared UI package is shaped, and the CI surface checks (ruling G-6).

Plan of record: internal-devops `rfcs/0067-graph-for-every-hyperobject.md` (accepted
2026-11-20, rulings G-1 to G-8). The shared graph core (G-2) is built in parallel in
`hyperobjects-spec`; this document states what the surfaces need from it.

| Artifact | Path | What it holds |
|---|---|---|
| Product context | [`PRODUCT.md`](../../PRODUCT.md) | users, purpose, positioning, constraints (impeccable `init`) |
| Design system | [`DESIGN.md`](../../DESIGN.md) + [`.impeccable/design.json`](../../.impeccable/design.json) | the incumbent visual system as it is (impeccable `document`) |
| Surface brief | [`.impeccable/surfaces/apps-studio-src-components-controls-controls-tsx.md`](../../.impeccable/surfaces/apps-studio-src-components-controls-controls-tsx.md) | the shaped configurator (impeccable `shape`) |
| First CI check | [`apps/studio/src/test/tokenContrast.test.ts`](../../apps/studio/src/test/tokenContrast.test.ts) | token contrast of the configurator's pairs |

## 1. Decisions taken in P0

| # | Decision | By | Consequence |
|---|---|---|---|
| S-1 | Makers and creators are served **equally**; neither is the "advanced mode" of the other | owner, 2026-11-20 | Configure and Inside are two faces of one panel, same weight |
| S-2 | **Document the incumbent look now; run the Studio world workshop before family goldens are approved in P2** | owner, 2026-11-20 | DESIGN.md records today's stock shadcn system honestly; no new colours, fonts or radii until the workshop; goldens are not baselined before it |
| S-3 | **Everyone can read any Commons cartridge's graph**; editing and saving stay on forks, tier gates unchanged | owner, 2026-11-20 | Inside is open; the header's Pro-gated code editor stays as it is for script editing |
| S-4 | Structure: **"Projection strip"** (viewport centre; Configure/Inside panel on the right; the family's projections as a strip under the viewport; action bar with Generate) | owner, from three structures dealt by impeccable `concept-seed` (seed:1886f44504b7ece3, offline roll) | presets, saved projections, compare and sweeps become one strip; compare is ticking projections |
| S-5 | Every visible fact comes from the graph's declarations; the surface never infers (units from label text, groups from naming) | this shape | the graph contract in §2; CI reports gaps instead of the UI guessing |
| S-6 | An unknown widget renders its base control and fails CI; nothing is dropped silently | this shape | today a parameter with an unimplemented widget disappears |
| S-7 | The first surface check wired is token contrast with a ratchet of recorded debt | this P0 | §5 |

## 2. What the graph must declare (input to the shared core, G-2)

Today `packages/schemas/graph.schema.json` declares per parameter only a `default` and an option
`map`; labels, ranges, groups and help live in the manifest, and units nowhere. For the surface to
be generated from the graph, the shared core's declarations need:

- **Parameter:** `id`, `type` (number, integer, enum, boolean, text, colour, gradient), `label`
  (i18n), `help` (i18n, optional), `unit` (`mm`, `deg`, `%`, `count`, `none`), `min`, `max`,
  `step`, `default`, `options` (value, i18n label, optional image), `group`, `order`, `advanced`,
  `visible_when` (an expression in the 1.1 dialect), `widget` (a registry name), and
  `preview_hint` (as the manifest has today).
- **Group:** `id`, `label` (i18n), `order`.
- **Preset:** `id`, `label` (i18n), `values`, optional `mode`.
- **Constraint:** `rule` (1.1 dialect), `severity` (`error` | `warning`), `message` (i18n),
  `applies_to` (parameter ids). Today the manifest schema leaves constraint items untyped.
- **Interface:** as `hyperobject.interfaces` today (typed sockets per RFC 0067 §2).
- **Outputs:** export formats, sweeps (`from`, `to`, frames, easing), and the hero still.
- **i18n:** every i18n field in en, es, fr and pt (RFC 0039); other Studio languages fall back
  to en at run time.

A wrapper graph (G-1) carries all of this, promoted from the manifest by the wrapper generator
(P1), so the surface does not care whether a graph is wrapper or native, except to say which on
the Inside face.

## 3. The shared surface package (G-3)

**Finding that shapes it:** the Fashion Cabinet and Pliego web studios are plain HTML and JavaScript
(no React), while the Studio is React 19. A React-only package cannot be
the one package G-3 asks for.

**Recommended shape (to confirm when P2 starts):**

1. **Surface model** (TypeScript, no DOM, no framework): graph declarations → a surface model
   (groups, ordered controls with resolved labels and units, presets and projections,
   constraint results, visibility, export list). Pure functions; the 1.1 expression dialect from
   the shared core. This is where the generation lives and where most tests run.
2. **Custom elements** rendering the model (`<hx-configure>`, `<hx-projection-strip>`,
   `<hx-inside>`, `<hx-works-with>`), styled only through CSS custom properties, so each
   platform themes them from its own tokens (its DESIGN.md). React 19 consumes custom elements
   natively (properties and events), so the Studio does not need a wrapper layer.
3. **Slots per platform:** the viewport (3D for solid, pattern layout for soft, crease pattern
   and fold preview for sheet), the render action, Verify, and per-node preview rendering.

Open within this recommendation: the Inside canvas uses React Flow in the Studio today; inside a
custom element it either brings its own React (loaded only when Inside opens) or moves to the
framework-neutral `@xyflow/system`. Decide at P2 with a size measurement.

Where it lives: start as a workspace package in this repository (`packages/graph-surfaces`), and
publish it to the MADFAM npm registry when Fashion Cabinet adopts it in P3.

## 4. What the incumbent Studio does today (gaps the generated surface closes)

Read on `main` at `91b3ffc9`. Several are defects worth fixing before P2 regardless.

| Area | Today | Evidence |
|---|---|---|
| Order and groups | controls render in fixed type buckets, not declared order; only the `visibility` group is rendered as a group | `Controls.tsx:300-310`, `:603` |
| Widgets | a slider or text parameter with an unimplemented widget (`pattern-selector`, `image-picker`, `custom`) is dropped | `Controls.tsx:301-302` |
| Units | a parameter is "dimensional" only if its English label contains `(mm)`; the mm/in toggle keeps separate state per caller, so the header toggle may not reach mounted sliders until they remount (inferred from code) | `SliderControl.tsx:44-47`, `useUnitSystem.ts:23-30` |
| Reset | no per-parameter reset; the default is only a star on the track | `SliderControl.tsx:143-149` |
| Constraints | messages show only under sliders; Generate is disabled by an error with no explanation; a formula that throws is skipped silently | `Controls.tsx:530-534`, `StudioSidebar.tsx:46`, `useConstraints.ts:68-70` |
| Constraint text | `text-destructive` measures 3.76:1 (light) and 1.99:1 (dark), under 4.5:1 | `tokenContrast.test.ts` |
| Compare | nothing adds the first slot, so compare never opens from the UI; "Sync camera" toggles state that no viewer reads; desktop only, because the phone sheet renders the sidebar without the compare props | `StudioMainView.tsx:192`, `ComparisonView.tsx:30-91`, `StudioSidebar.tsx:422` |
| Graph editor | Pro + fork only; no per-node preview; issues list and validator messages hard-coded in English; no axe test | `StudioHeader.tsx:155-165`, `GraphIssues.tsx:58-67`, `graphDocument.ts:248-286` |
| Visual regression | the only `toHaveScreenshot` suite is `describe.skip` | `e2e/tests/18-visual-regression` |
| Cartridge labels | 4,495 of 4,509 parameter labels exist in en and es only | commons scan, 2026-11-20 |

## 5. CI surface checks (G-6)

G-6 asks for, per cartridge: impeccable `detect`, accessibility (axe), contrast, label/unit/i18n
completeness against the graph, and golden screenshots per family at phone and desktop widths.
Running every cartridge (512 solid today; about 1,195 across the solid, soft and sheet commons)
through a browser on every pull request is neither possible on this
infrastructure nor useful, so the checks split into **static** (every cartridge, every PR, no
browser) and **rendered** (sampled per PR, full sweep nightly on the cluster's CPU workers,
RFC 0061).

| # | Check | Kind | Scope per run | Where | State |
|---|---|---|---|---|---|
| C1 | **Token contrast**: the configurator's text, non-text and focus pairs in both themes, with recorded debt as a ratchet | static | tokens (once per platform) | Studio `test` job (vitest) | **wired in this PR** |
| C2 | **Declaration completeness**: every parameter has a label and every constraint a message in en/es/fr/pt, every number a unit, every group and widget a known id, every preset a label; a baseline file ratchets today's gaps (fr/pt labels) down | static | every cartridge | commons CI (`solid-hyperobjects`, later soft and sheet) and the keystone; a copy in Studio CI for the fixture set | P1 (needs the declarations from §2) |
| C3 | **Surface model tests**: generation is total (every declared type, widget and state maps to a control) | static | package | Studio CI | P2, with the package |
| C4 | **axe** on the generated surface (serious and critical fail), both faces, both themes | rendered | changed cartridges + family representatives | commons CI for changed cartridges; Studio e2e for representatives; nightly all | P2 |
| C5 | **impeccable detect** on the rendered surface's HTML snapshot (telemetry off), and on the package source when it changes | rendered + static | as C4 | as C4 | P2 |
| C6 | **Layout integrity**: no horizontal scroll at 360 px, no clipped or overlapping controls, no truncated labels, 44 px targets | rendered | as C4 | as C4 | P2 |
| C7 | **Family goldens**: one representative cartridge per family, at 390×844 and 1440×900, light (plus one dark sample), `toHaveScreenshot` with Linux baselines made in the Playwright container | rendered | one per family (the Commons has 113 interface families today; surface families are defined in P2) | Studio e2e; nightly | P2, **after** the world workshop (S-2) |

How a rendered check sees one cartridge: a harness route renders the generated surface from the
cartridge's graph with the 3D viewport replaced by its prerendered still (WebGL output is not
deterministic enough for goldens), with motion settled. The same harness serves Fashion Cabinet
and Pliego with their own slot content.

Gate policy: C1 blocks now. C2 starts as a report with a baseline and blocks new regressions
from the day it lands; C4 to C7 report first and block per commons when the entry gate (G-7)
turns on.

### C1 findings on the incumbent tokens (2026-11-20)

| Pair | Light | Dark | Floor |
|---|---|---|---|
| `destructive` text on background/card (constraint messages) | 3.76 | 1.99 | 4.5 |
| `destructive-foreground` on `destructive` (destructive button) | 3.60 | 9.59 | 4.5 |
| `input` border on background (field boundary) | 1.27 | 1.34 | 3.0 |
| `primary` on `secondary` (slider's filled range on its track) | 16.13 | 2.86 | 3.0 |

Everything else the configurator uses clears its floor. The fixes are token work (a readable
error token, as `primary-readable` was for accent text, a field boundary that clears 3:1, and a
dark slider track or range that clears 3:1).
They are left to the world workshop or a token PR, and the ratchet makes each fix update the test.

## 6. Next steps

1. **P1** (with the shared core): declarations of §2 in the core schema; the wrapper generator
   promotes them from manifests; C2 lands with its baseline.
2. **Before P2:** the Studio world workshop through impeccable (S-2); then `document` refreshes
   DESIGN.md from the result.
3. **P2:** the package (§3) and the generated configurator in the Studio, built through
   impeccable's build, critique and polish; C3 to C7; family critiques; then the incumbent
   `Controls.tsx` retires.
4. **P3:** Fashion Cabinet and Pliego adopt the package with their own tokens and slots.

Fixes that need not wait for P2 (defects today): compare's first slot and camera sync,
constraint messages for every control type and a reason for a disabled Generate, the shared
unit state, and English-only graph validator messages.
