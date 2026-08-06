# Universal Bracket Generator

The most-requested functional generator after storage bins, built with
**CadQuery** (B-Rep). One cartridge produces the common bracket topologies from a
single set of leg / width / thickness / screw-pattern parameters, so a whole
blister-pack wall of fixed stamped brackets collapses into one configurable part.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Angle (L) Bracket** | `angle_bracket` | Two flat legs meeting at `angle` (90° default); each leg drilled. |
| **Flat Strap / Plate** | `flat_bracket` | A single flat slab (span `leg_a`) with a screw-hole row — a mending / joiner plate. |
| **T-Bracket** | `T_bracket` | A flat base plate (span `leg_a`) with a perpendicular upright (height `leg_b`). |
| **3D Corner Gusset** | `corner_bracket_3d` | Three mutually perpendicular legs sharing one corner, for bracing a box/frame corner in all three planes. |

The `bracket_type` select mirrors these four families and stays in sync with the
active mode; the platform renders per-part via `target_part`, and each mode's
`parts[]` id equals the value the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bracket Type | `bracket_type` | `angle_L` | Topology family (`angle_L` / `flat` / `T` / `corner_3d`). |
| Geometry | `leg_a` / `leg_b` | 50 / 50 mm | Leg lengths (strap length / base span in Flat & T). |
| Geometry | `width` | 30 mm | Bracket width across the legs. |
| Geometry | `thickness` | 4.0 mm | Material thickness. |
| Geometry | `angle` | 90° | Bend angle (L only). |
| Screw Pattern | `holes_per_leg` | 2 | Screw holes per leg (0 = none); the 3D corner uses one per face. |
| Screw Pattern | `screw_dia` | 4.5 mm | Clearance hole diameter (M4 ≈ 4.5, M5 ≈ 5.5, M6 ≈ 6.5). |
| Options | `counterbore` | off | Flat counterbore so heads sit flush. |
| Options | `gusset` | off | Triangular corner brace (L only). |

## Presets

- **Shelf L-Bracket (M4)** — a 90° 50×50 angle bracket, two M4 holes per leg.
- **Mending Plate (M5)** — a 90 mm flat strap with four counterbored M5 holes.
- **3D Box Corner (M4)** — a three-axis corner gusset for a box/frame corner.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Bracket Screw Pattern** (`bolt_pattern`, internal) — the mounting hole
    layout, defined by `holes_per_leg`, `screw_dia`, `counterbore`, `leg_a`,
    `leg_b`, `width`. This is the interface that mates to boards, extrusion, and
    panels; the shared `bolt_grid` / `drill_row` helper drives it in every mode.
  - **Leg Mounting Face** (`profile`, internal) — `leg_a`, `leg_b`, `width`,
    `thickness`, `angle` define the flat faces the bracket clamps between.
- **Material awareness:** `screw_dia` is a clearance value tunable per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** the universal joiner — one parametric cartridge replaces
  the fixed stamped brackets sold in blister packs, sized to the exact boards,
  screws, angle, and topology a repair or build actually needs.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The L-bracket builds leg B flat, drills it, then rotates it about the bend line
  and fuses — so the bend is one watertight solid at any angle. The optional
  gusset is a full-width brace whose contact vertices are pushed into the leg
  material, leaving no coincident faces. All four modes export watertight; the L
  and T families share an envelope but differ in mass distribution (the T upright
  rises from the plate centre, the L leg folds about the edge).
