---
version: 1
slug: "apps-studio-src-components-controls-controls-tsx"
primary_target: "apps/studio/src/components/controls/Controls.tsx"
related_targets: ["apps/studio/src/components/studio/StudioSidebar.tsx","apps/studio/src/components/editor/graph/GraphEditor.tsx","apps/studio/src/components/project/ComparisonView.tsx","apps/studio/src/components/studio/WorksWithPanel.tsx","apps/studio/src/components/export/ExportPanel.tsx"]
---

# Surface brief: the graph-generated configurator (Studio; reused by Fashion Cabinet and Pliego)

Shaped 2026-11-20 through impeccable `shape`, for RFC 0067 phase P0 (internal-devops
`rfcs/0067-graph-for-every-hyperobject.md` §5; rulings G-3 and G-6). Mode: **Operate**.
Status: **shape confirmed, not built.** The structure below was locked by the owner on the
decision round; the look stays the incumbent system in DESIGN.md until the Studio world
workshop, which runs before family goldens are approved in RFC 0067 P2 (owner ruling,
2026-11-20). Implementation plan and CI checks: `docs/architecture/graph-generated-surfaces.md`.

## 1. Job and audience

- **Makers and creators, equally** (owner ruling). The maker sets their dimensions, checks
  the fit and leaves with a file. The creator opens the same cartridge to see inside it,
  node by node, and forks it to change it.
- Arrives from: a Commons card on the landing or the Projects view, a shared link
  (`/project/{slug}/{mode}/{preset}` with non-default values), or a "works with" partner.
- State of mind: has a physical constraint in hand (a pipe, a drawer, a rail); wants
  certainty that the instance fits before spending material.

## 2. Outcome and proof

- **Primary task:** reach one named projection of the cartridge (a preset, edited or not)
  that satisfies every constraint, and export or share it.
- **Secondary tasks:** compare two to four projections; check what it works with; open
  "Inside" to read the graph and preview any node's intermediate shape; fork to edit.
- **Success:** the visitor always knows which projection they are on and how it differs
  from its preset; Generate never sits disabled without saying why; the exported file name
  names the projection.
- **Proof the surface carries:** the rendered object itself, the declared interfaces
  (works with), the verification result (Verify), and the graph. No invented figures.

## 3. Selected direction: "Projection strip"

Locked by the owner from three structures dealt by impeccable `concept-seed --scope surface
--mode operate` (seed:1886f44504b7ece3; the roll ran offline, with no challengers; seven
grounded candidates, this was the dealt lead). The other two dealt structures were an
outline + inspector three-pane layout and a two-face sidebar.

- **Thesis:** the configurator is a manager of the family's projections. The fourth axis is
  visible as a strip of projections, and the 3D view always shows exactly one of them (or
  two to four in compare). It refuses the category default of a long form beside a model
  with presets as a forgotten dropdown.
- **Signature move:** the **projection strip** along the bottom of the viewport: authored
  presets (◆), the visitor's saved projections (●), the current unsaved projection (○,
  "edited from Default"), and declared parameter sweeps (▶) as one row of labelled
  thumbnails. Selecting is navigating the 4D family; ticking is comparing.
- **Shell (desktop, ≥ 1024 px):** header (cartridge name, Procomún link, licence, mode
  switch, mm|in, language, theme, share) · viewport (centre, the largest area) · right
  panel with two faces, **Configure** and **Inside** · the projection strip under the
  viewport · a bottom action bar (Works with (n), Export, Verify, then **Generate** as the
  one primary action, right-aligned).
- **Phone (< 768 px):** header collapses to name + overflow; viewport on top (about 45 %
  of the height); the strip as a horizontal swipe row under it; the panel as a bottom sheet
  with two snap points and the Configure | Inside switch in its handle; Generate fixed in
  the bottom bar. `phone-landscape`: viewport left, sheet becomes a right drawer.
- **Tablet (768–1023 px):** desktop shell with the right panel as an overlay drawer.

## 4. Scope and boundaries

- **In scope (system):** one component system that renders any cartridge from its graph:
  panel (both faces), strip, action bar, compare layout, works-with list, export panel and
  every state below. Designed once; per cartridge only data varies.
- **Generated from the graph, never hand-kept:** parameters (type, label, help, unit, range,
  step, default, group, order, advanced flag, visibility condition, widget), presets,
  constraints (rule, severity, message, applies-to), interfaces, export formats, sweeps,
  hero still. Where a fact is missing, the surface does not guess (no unit from label text,
  as `SliderControl.tsx` does today with `(mm)`); CI reports the gap.
- **Reused by Fashion Cabinet and Pliego (G-3):** the panel, strip, compare, Inside and
  their states are one package, themed only by each platform's tokens (DESIGN.md of that
  platform) and fed by each kernel's node catalogue. Nothing solid-specific in the package:
  "Generate", the viewer and Verify are slots each platform fills (a 3D viewport for solid,
  a pattern-piece layout for soft, a crease pattern and fold preview for sheet).
- **Untouched:** cartridge content; the viewer's tools (measure, section, axes, quality); tier
  rules and quotas; the BOM and assembly panels (they move into the Configure face's last
  section unchanged); the code editor for script cartridges.
- **Anti-goals:** bespoke UI per cartridge; a wizard; a graph-first canvas as the default
  view; decorative motion; any colour, font or radius not in DESIGN.md; a modal as the first
  answer.

## 5. States and ranges (Commons figures read 2026-11-20)

- **Parameters per cartridge:** median 8, p90 12, max 82. Above 20 the Configure face shows a
  filter field; groups stay. **Groups:** median 3, max 12; ungrouped parameters go under
  "General". **Modes:** median 3, max 7; one mode hides the switch. **Presets:** median 3,
  max 30 (482 of 512 cartridges have some); zero presets leaves the strip with "Default" and
  the visitor's own projections. **Sweeps:** 20 cartridges, up to 3 each.
- **Labels:** 4,495 of 4,509 parameter labels exist in en and es only today; fr and pt are
  missing. The runtime falls back to en; CI reports the gap (ratchet, see the plan).
- **Graph depth (Inside):** a wrapper graph is one `script` node; a native graph has tens of
  nodes. Inside says which it is ("Wrapper: one script node, source `x.py`" vs node count).
- **States every generated surface has:** first load (controls render at once from the
  graph declarations; the viewport shows the prerendered default instance with a
  "Default instance, not yet rendered" chip); rendering (progress in the Generate button and
  a non-blocking chip); queued; quota reached (free tier, explains when it resets and what
  Pro changes, no dead end); render error (message, retry, "report" link); constraint
  violated (inline + summary, below); edited-from-preset; compare with 2–4; offline;
  read-only Inside for visitors; fork-to-edit; wrapper vs native graph; missing
  translation (en fallback, flagged only in development).

## 6. Interaction and layout

### Configure face: controls by declared type

| Declared type | Control | Notes |
|---|---|---|
| number, bounded | slider **and** a numeric field side by side, unit after the value | field always visible (today it hides behind a click); ticks when ≤ 30 steps; the default marked on the track; keyboard: arrows = step, Shift+arrows = 10 steps |
| number, unbounded or range > 1,000 steps | numeric field with stepper | |
| integer count | stepper (− value +) | |
| enum, ≤ 4 short options | segmented control | |
| enum, > 4 options | select | options with declared images become an image grid (`image-picker`) |
| boolean | switch; checkbox inside a visibility list | |
| text | text field with a remaining-characters count | |
| colour / gradient | swatch + hex field / two swatches with a preview bar | |
| declared widget (`tpms-topology`, `component-picker`, `pattern-selector`, energy) | the widget from the package's registry | an unknown widget renders its base type's control and CI fails; never dropped silently (today `!p.widget` drops it) |

- Every control: label, optional help (one line, expands), unit, **per-parameter reset**
  shown only when the value differs from the current projection's preset, and a "changed"
  dot. Labels and values follow DESIGN.md's Measurement Rule.
- **Groups** are collapsible sections in declared order, first open, sticky headings; the
  `advanced` flag folds parameters under "More" inside their group.
- **Visibility conditions** declared by the graph hide or disable a control and say why on
  hover/focus ("Needs: Mount = Screw").
- **Modes** switch in the header; switching re-scopes the strip and resets out-of-mode
  values (behaviour as today).
- **Units:** every dimension declares its unit (mm, deg, %, count, none). The mm|in toggle
  converts only `mm` values, in one shared state (today each control holds its own).

### Constraints

- Evaluated live from the graph's declared rules. A violation shows **under every affected
  control** (every control type, not only sliders as today), with severity (error blocks,
  warning informs) and the declared message in the visitor's language.
- A **summary line above Generate** names the conflicts and links to each ("2 conflicts:
  Wall, Cable Ø"), so Generate is never disabled without a reason.
- Error text uses a token that clears 4.5:1 in both themes (today `text-destructive` does
  not; see the plan's findings).

### Projection strip and compare

- Items: preset ◆, saved ● (stored in the URL and locally; named by the visitor), current ○
  (appears when values differ from the selected item: "Edited from Thin"), sweep ▶.
- Thumbnails come from the prerender pipeline for presets; saved projections take a capture
  on save. Labels always visible; keyboard: arrows move, Enter selects, Space ticks.
- **Compare:** tick 2–4 items; the viewport splits (two side by side, three or four in a
  grid); camera sync is on by default and must actually sync (today the toggle does nothing
  and the first slot cannot be added). Each cell names its projection and lists only the
  parameters that differ.
- **Sweeps** play in the viewport from prerendered keyframes; `prefers-reduced-motion`
  shows the frames as a still sequence. Whether live sweeps (server renders) are offered,
  and to which tier, is OPEN (the sweep player is not mounted today).

### Inside face: the graph view and per-node preview

- Everyone can open Inside read-only (owner ruling); editing and saving stay on forks with
  tier gates unchanged ("Fork to edit" is the face's one action for a visitor).
- Desktop: the canvas takes the right panel widened to about 45 % of the window (the
  viewport keeps the rest); phone: Inside opens full screen over the sheet with a back
  action.
- Nodes as cards with typed sockets (React Flow, as today); a list view of the same nodes in
  topological order for keyboard and screen-reader users, kept in sync with the canvas.
- **Per-node preview:** selecting a node renders its intermediate shape in the main viewport
  as the solid, with the final result ghosted around it (the ghost overlay exists); a chip
  names the node ("Showing: fillet_2, step 5 of 9"). For a wrapper graph, the one node is
  the whole result, and the card links to the source file and its provenance.
- From Configure, each parameter's "show in graph" action selects the node(s) it drives;
  from Inside, a node's promoted inputs link back to their controls.
- Validation messages in the canvas and the issues list are i18n keys (today they are
  hard-coded English).

### Works with, export, verify

- **Works with (n)** opens a list (popover on desktop, sheet on phone) of partner cartridges
  with their shared interface and standard, from the graph's declared interfaces and the
  catalogue's compatibility graph; each opens the partner.
- **Export:** formats declared by the graph, filtered by tier; a locked format shows the tier
  that unlocks it in words, not only a lock glyph; the file name carries cartridge,
  projection and key values (`cable-clip_mine-1_6mm.stl`).
- **Verify** reports the verification result for the current projection.

## 7. Constraints and open decisions

- Platform web; React 19 + Tailwind + Radix in the Studio; the package must also run in
  Fashion Cabinet and Pliego, so its tokens are CSS custom properties only.
- WCAG 2.2 AA; 44 px targets; every control keyboard- and screen-reader-operable; the canvas
  never the only way to read the graph.
- Languages: Studio chrome in de, en, es, fr, pt, zh; cartridge text required in en, es, fr,
  pt (RFC 0039).
- **The graph must declare** (contract for the shared core, G-2): per parameter `type`,
  `label` (i18n), `help` (i18n, optional), `unit`, `min`/`max`/`step`, `default`, `group`,
  `order`, `advanced`, `visible_when`, `widget`; per group `id`, `label`, `order`; presets
  with `label` and optional `mode`; constraints with `rule`, `severity`, `message` (i18n),
  `applies_to`; interfaces; export formats; sweeps. Today's graph schema declares only
  `default` and an option `map` per parameter.
- OPEN: sweep playback beyond prerendered keyframes and its tier; whether saved projections
  sync to an account; the world workshop's outcome (it may change type, palette, density and
  the strip's signature styling, not this structure).
