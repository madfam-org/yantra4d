# Framing Hyperobject — Research Project

> **Status**: 🔬 Research complete — SCAD project not yet started
> **Phase**: Pre-development (Phase 4 in the [platform roadmap](../../docs/roadmap.md))

This directory contains foundational research for a future Yantra4D hyperobject project focused on **parametric framing and containment systems**.

---

## Research Document

📄 [`FramingHyperobjectResearchandTaxonomy.html`](../FramingHyperobjectResearchandTaxonomy.html)

*"The Morphology of Containment: A Technical and Ontological Analysis of the Framing Hyperobject"*

A comprehensive taxonomy of framing systems across 10 domains, covering the geometry, materials, standards, and industrial tolerances that govern how objects are contained, displayed, and mounted.

---

## Research Scope

| Section | Topic |
|---|---|
| 1 | Traditional picture frames: rabbet geometry, moulding profiles (bevel, scoop, ovolo, ogee/cyma, floater), archival hierarchy |
| 2 | Canvas tension systems: stretcher bar keying, gallery/museum wrap depths, SEG keder/channel tolerances |
| 3 | Industrial snap frames: spring-steel mechanism, 25mm/32mm profile standards, visual bite (10–12mm) |
| 4 | LED lightboxes: edge-lit vs. ladder-light, depth vs. diffusion tradeoffs (18mm–160mm) |
| 5 | Collectible slabs: PSA/BGS/SGC/CGC/TAG dimensional standards and incompatibility analysis |
| 6 | Numismatic capsules: direct-fit (sub-0.1mm tolerance) and ring-fit systems |
| 7 | Comic book preservation: Golden/Silver/Modern age bag standards, CGC slab inner-well gasket |
| 8 | Wearable frames (ID badges): CR80/ISO 7810 standard, slot punch geometry, lanyard hardware |
| 9 | Parametric digital frames: OpenSCAD + BOSL2 `path_sweep()` / `bezier_sweep()` for ogee profiles, FDM friction-fit tolerances |
| 10 | Mounting systems: VESA MIS-D/E/F patterns, French cleat load distribution, standoff barrel dimensions |

---

## Planned CDG Interfaces

| Interface ID | Geometry Type | Description |
|---|---|---|
| `rabbet` | `pocket` | L-shaped recess for art stack containment |
| `seg_channel` | `socket` | 3mm × 12mm keder channel for fabric graphics |
| `snap_profile` | `snap` | Spring-loaded 25mm/32mm snap frame profile |
| `vesa_pattern` | `bolt_pattern` | 75×75 / 100×100 / 200×200 / 400×400 mounting patterns |
| `french_cleat` | `profile` | 30–45° interlocking bevel for gravity-based hanging |
| `standoff_bore` | `thread` | M4/M6/M8 threaded standoff interface |

---

## Planned Modes

| Mode ID | Description |
|---|---|
| `picture_frame` | Parametric moulding profile (bevel, scoop, ogee) with configurable rabbet depth/width |
| `canvas_floater` | L-profile floater frame for gallery-wrapped canvases |
| `snap_frame` | Industrial snap frame with configurable profile width (25mm/32mm) and size |
| `seg_lightbox` | SEG lightbox frame with edge-lit depth and channel dimensions |
| `coin_capsule` | Direct-fit or ring-fit coin capsule with configurable bore diameter |
| `card_slab` | Parametric trading card display slab (configurable to PSA/BGS/CGC dimensions) |
| `badge_holder` | CR80 badge holder with slot punch and lanyard attachment point |

---

## Project Metadata (Planned)

| Field | Value |
|---|---|
| **Domain** | `culture` |
| **License** | CERN-OHL-S-2.0 |
| **Libraries** | BOSL2 (`path_sweep`, `bezier_sweep`, `diff`, `cuboid`) |
| **Difficulty** | Intermediate |

---

## Prerequisites Before Starting

This project should only begin after the following platform stability items are complete:

1. ✅ P0.1 — E2E tests in CI
2. ✅ P0.2 — Stub projects resolved
3. ✅ P1.1 — Project gallery complete
4. ✅ P1.5 — Hyperobjects Phase 2 UI live (so CDG interfaces are surfaced in the platform)

See the [roadmap](../../docs/roadmap.md) for full context.
