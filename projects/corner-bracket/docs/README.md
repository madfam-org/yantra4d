# Corner Bracket / Angle Gusset

A simple **angle bracket** generated with **CadQuery** (B-Rep) that joins two
panels or boards at any angle. Two legs meet at a configurable angle (default
90°); each leg carries a row of screw holes with an optional countersink and an
optional triangular gusset brace.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **L-Bracket** | `bracket` | Two legs at the set `angle` (90° default), each drilled. |
| **T-Bracket** | `bracket` | A flat base plate with a perpendicular leg from its center, for T-joints. |
| **Gusset Bracket** | `bracket` | An L-bracket with a full-width triangular brace across the corner for stiffness. |

The `gusset` checkbox adds the brace to an L-bracket; the Gusset Bracket mode
forces it on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Geometry | `angle` | 90° | Angle between the legs (L / gusset). |
| Geometry | `leg_a` / `leg_b` | 40 / 40 mm | Leg lengths (base / upright in T-mode). |
| Geometry | `width` | 30 mm | Bracket width. |
| Geometry | `thickness` | 4.0 mm | Leg material thickness. |
| Screw Holes | `holes_per_leg` | 2 | Screw holes per leg (0 = none). |
| Screw Holes | `screw_dia` | 4.5 mm | Clearance hole diameter (M4 ≈ 4.5, M5 ≈ 5.5). |
| Options | `countersink` | off | Flat counterbore so heads sit flush. |
| Options | `gusset` | off | Triangular corner brace. |

## Presets

- **Shelf L-Bracket (M4)** — a 90° 50×50 bracket with two M4 holes per leg.
- **Heavy Gusset (M5)** — a braced 60×60 bracket for heavier loads.
- **T-Joiner (M4)** — a T-bracket with countersunk holes.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Bracket Screw Pattern** (`bolt_pattern`, internal) — the mounting hole
    grid, defined by `holes_per_leg`, `screw_dia`, `leg_a`, `leg_b`, `width`.
    This is the interface that mates to boards, extrusion, and panels.
  - **Leg Mounting Face** (`profile`, internal) — `leg_a`, `leg_b`, `width`,
    `thickness`, `angle` define the flat faces the bracket clamps between.
- **Material awareness:** hole diameter is a clearance value that can be tuned
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** the universal joiner — one parametric angle bracket
  replaces fixed 90° stamped brackets, sized to the exact boards, screws, and
  angle a repair or build needs.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The gusset is a **full-width** triangular brace whose contact vertices are
  pushed slightly into the leg material, so the boolean fuse leaves no coincident
  faces and the bracket stays a watertight, manifold solid at every angle (a
  partial-width rib would leave non-manifold edges where its side meets a leg
  face). All modes export watertight.
