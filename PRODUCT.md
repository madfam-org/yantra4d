# Product

<!-- impeccable:product-schema 1 -->

<!-- Written 2026-11-20 through impeccable `init`, for RFC 0067 phase P0 (internal-devops
rfcs/0067-graph-for-every-hyperobject.md). Sources: the Studio and landing code on main
(91b3ffc9), the capability map in the 2026-11-20 landing copy audit, ROADMAP.md, and the
owner's rulings listed under "Brand Commitments". Facts marked OPEN are undecided; do not
fill them in. -->

## Platform

web

## Users

Yantra4D is designed for two people **equally** (owner ruling, 2026-11-20). Neither is the
"advanced mode" of the other.

- **The maker.** Has a job in the physical world: a bracket that must fit a 42 mm pipe, a
  drawer insert for a known drawer, a jig for a given plate thickness. Opens a cartridge from
  the Hyperobjects Commons, sets their dimensions, checks the result fits what it mates with,
  and leaves with a file to print or machine. Usually on a laptop next to a printer or a phone
  in the workshop. Measures in millimetres or inches; does not read code.
- **The creator.** Authors or improves cartridges: forks one, reads and rewires its graph,
  adds a parameter, a preset or a constraint, and contributes the result back to the Commons
  by pull request. Wants to see inside the hyperobject, node by node, and to trust that what
  they publish passes the same verification bar as everything else.

Other audiences that exist and are served by the same surfaces: product teams in the MADFAM
ecosystem who embed or white-label a configurator; self-hosters running the AGPL platform.

## Product Purpose

Yantra4D is three tools around one Commons:

1. **A configurator**: pick a cartridge, set its parameters, get one exact instance.
2. **A visualizer**: see that instance in 3D (measure, section, compare variants, check what
   it works with) before committing material.
3. **A 4D → 3D projections manager**: a cartridge is a *family* of objects; its parameters are
   the fourth axis, and every point on that axis is one printable 3D solid. Yantra4D chooses,
   names, shares, compares, exports and verifies those projections. Played back (parameter
   sweeps), the fourth axis reads as time.

At the heart is **the Hyperobjects Commons** (Spanish: **el Procomún de Hiperobjetos**):
open, verified, licensed cartridges that share standard interfaces, so the Commons grows as
one system rather than a pile of files.

Success: a maker leaves with an instance that fits on the first print; a creator's
contribution lands in the Commons and is immediately configurable by everyone.

## Positioning

A Yantra4D cartridge is not a file of one object; it is a verified definition of every
object inside a bounded parameter range, declared as a graph, with interfaces typed against
real standards (threads, snaps, rails, mounting patterns). Two things a neighbouring CAD,
model-sharing or configurator product cannot truthfully claim together:

- **Every cartridge is configurable and inspectable through one graph format** (RFC 0067):
  the same document drives the controls, the graph view, the verification and the export.
- **Interfaces are first-class**: the Commons knows which cartridges mate with which, by
  shared standard (the "works with" graph), across solid, soft (Fashion Cabinet) and sheet
  (Pliego) commons.

## Operating Context

- **Studio** (`apps/studio`, app.yantra4d.com): React 19 + Three.js. Routes
  `/project/{slug}/{mode}/{preset}`; shareable links carry non-default parameters.
- **Landing** (`apps/landing`, yantra4d.com): Astro; es and en; prerendered GLBs of the
  Commons' default instances and parameter sweeps.
- **Commons** (`projects/`, pinned from the public `madfam-org/solid-hyperobjects`): 512
  cartridges, 1,501 modes, 4,509 parameters (slider 4,028, select 272, checkbox 195,
  text 14), 482 with presets, 509 with cross-parameter constraints, 502 with declared
  interfaces (figures read 2026-11-20).
- **Kernels**: OpenSCAD (browser WASM and server), CadQuery, implicit SDF, and the graph
  engine (`.graph.json` → sandboxed CadQuery). Graph format 1.1 has parameters, ordered
  derived values and expressions.
- **Verification**: the keystone (`hyperobjects-spec`) renders every cartridge fail-closed
  (body count, watertightness, dimensions, collisions).
- **Sibling platforms that reuse these surfaces** (RFC 0067 G-3): Fashion Cabinet (soft
  commons) and Pliego (sheet commons) share one graph-editor UI package with the Studio.
- **Rituals**: makers print and come back to adjust; creators fork, edit, open a PR; the
  Commons pin is bumped weekly.

## Capabilities and Constraints

- **Graph for every hyperobject** (RFC 0067, accepted 2026-11-20): every cartridge gets a
  configurable graph, first as a *wrapper* (one typed `script` node, everything declared by
  the graph), then native nodes by value. The configurator, graph view and per-node preview
  are **generated from the graph**; a cartridge never ships bespoke UI code. Per cartridge
  only data varies: labels and help (en, es, fr, pt at least), groups, order, ranges, units,
  presets, imagery.
- **Surface checks per cartridge in CI** (G-6): impeccable detect, accessibility (axe),
  contrast, label/unit/i18n completeness against the graph, golden screenshots per family at
  phone and desktop widths.
- **Graph visibility** (owner ruling, 2026-11-20): every visitor can open the graph of any
  Commons cartridge **read-only**; editing and saving stay on forks, with tier gates
  unchanged.
- **Free tiers** customise every Commons cartridge under a render quota (owner ruling,
  2026-11-20; implementation in PR #313, open at the time of writing). Until it lands,
  CadQuery and graph renders are Pro on the hosted service.
- **Units**: the Studio stores millimetres; a display-only mm ↔ inch toggle exists.
- **Studio languages**: de, en, es, fr, pt, zh. The Commons is quadrilingual: en, es, fr, pt
  (RFC 0039).
- **Honest limits**: no physics solver ships (the physics endpoint answers 501; stress and
  optimise are labelled estimates). The sweep player (`AnimationPanel`) exists but is not
  mounted. Public `.scad` onboarding is admin-only.
- **Contributions** reach the Commons by pull request to `solid-hyperobjects`, never by an
  in-app publish.
- OPEN: whether the parameter-sweep player is mounted, and for which tier; whether a Premium
  tier is published.

## Brand Commitments

- Name: **Yantra4D**. The Commons is **"the Hyperobjects Commons"**; in Spanish **"el
  Procomún de Hiperobjetos"** (owner ruling, 2026-11-20). Use "Procomún" consistently in
  Spanish; not "Commons", "Comunes" or "acervo común".
- **"4D" means parameters and, played back, time** (owner ruling, 2026-11-20). Never imply
  time-dependent geometry or physics the product does not compute.
- Cartridge vocabulary: *cartridge*, *hyperobject*, *mode*, *preset*, *interface* (CDG,
  Common Denominator Geometry), *works with*.
- Licences: platform AGPL-3.0; every Commons cartridge CERN-OHL-W-2.0.
- Voice: plain, exact, measured. Say what the product does and what it does not. No
  "blazingly fast", no unearned superlatives (the README's older hype is not a model).

## Evidence on Hand

- 512 real cartridges with manifests, presets, constraints, interfaces and verification
  blocks (`projects/*/project.json`); 502 prerendered default-instance GLBs and keyframe GLBs
  for the 20 swept cartridges (`apps/landing/public/models/manifest.json`).
- Interface graph: 211 nodes, 266 edges, 113 families (`GET /api/catalog/graph`).
- 15 graph files in the solid Commons (2 references, 13 golden twins).
- Absences future work must not fabricate: testimonials, customer names, usage figures,
  print-success rates, certifications (medical cartridges are reference geometry, not
  certified devices).

## Product Principles

1. **The Commons is the product.** Surfaces serve cartridges; no surface outranks the
   object being configured.
2. **One graph, many surfaces.** If a surface needs a fact, the graph declares it; nothing is
   hand-kept per cartridge in UI code.
3. **Show the family, then the instance.** The visitor always knows which projection of the
   4D family they are looking at, and how to get back to its defaults.
4. **Open by default, gated only where it costs.** Reading, inspecting and comparing are
   open; renders, edits and saves follow the tiers.
5. **Verified or labelled.** Every number shown is computed, or labelled as an estimate.

## Accessibility & Inclusion

- WCAG 2.2 AA on every generated surface; small accent text uses the `primary-readable`
  token (4.5:1), as the landing already enforces.
- Every control is operable by keyboard and screen reader; sliders always have an exact
  numeric entry.
- Touch targets work on a phone in a workshop (44 px minimum); `prefers-reduced-motion`
  stops sweeps and loops.
- Labels, help, units and constraint messages exist in every Commons language before a
  cartridge's surface passes CI.
