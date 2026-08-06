# Curtain / Blind Bracket

A parametric **curtain / blind rod bracket** generated with **CadQuery** (B-Rep).
It holds a rod at a set projection from the wall, with an open-top C cradle (drop
the rod in) or a closed ring (thread the rod through), sized to `rod_dia`.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wall Bracket** | `bracket` | A standard bracket: wall plate + arm + rod cradle. |
| **End Bracket** | `end_bracket` | A bracket whose cradle has a closing end cap so the rod cannot slide off the end of the run. |
| **Center Support** | `center_support` | A stiffer mid-span support (twin arms + open saddle) for long rods; the saddle is always open so it can be added under a rod already hung. |

The studio dispatches the active part via `target_part` (`bracket` /
`end_bracket` / `center_support`).

## Cradle style (`cradle_style`)

| Value | Cradle |
| :--- | :--- |
| `open` | An open-top C; the rod drops in from above and is lightly retained by a mouth slightly narrower than the rod. |
| `closed` | A full ring; the rod threads through the end (used with an end bracket for a captive rod). |

The center support is always open-top by design.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rod & Cradle | `rod_dia` | 19.0 mm | Rod diameter the cradle holds. |
| Rod & Cradle | `cradle_style` | `open` | `open` (C) or `closed` (ring). |
| Rod & Cradle | `cradle_wall` | 4.0 mm | Cradle ring / C wall thickness. |
| Projection & Arm | `projection` | 70.0 mm | Rod-centre distance from the wall. |
| Projection & Arm | `arm_w` | 14.0 mm | Support-arm width (also cradle length). |
| Projection & Arm | `arm_thick` | 10.0 mm | Arm thickness (load / projection capacity). |
| Wall Mount | `plate_w` | 32.0 mm | Wall-plate width. |
| Wall Mount | `plate_thick` | 6.0 mm | Wall-plate thickness. |
| Wall Mount | `hole_spacing` | 40.0 mm | Vertical distance between the two screw holes. |
| Wall Mount | `screw_dia` | 4.5 mm | Screw clearance hole diameter. |

## Presets

- **Standard Curtain Rod (19 mm)** — a 70 mm-projection open bracket.
- **End Bracket (closed 25 mm)** — a captive-rod end bracket.
- **Long-Rod Center Support** — a mid-span support for a 25 mm rod.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Rod Cradle** (`socket`, internal) — the rod-holding cradle, defined by
    `rod_dia`, `projection`, `cradle_style`, and `cradle_wall`. All three parts
    place the same cradle at the same projection so a rod sits level across the
    run.
  - **Wall Screw Mount** (`bolt_pattern`, internal) — the two-hole wall plate,
    defined by `hole_spacing`, `screw_dia`, `plate_thick`, and `plate_w`.
- **Material awareness:** the open-cradle mouth is expressed relative to the rod
  diameter and `arm_thick` is exposed for load, so grip and strength tune per
  material / printer; `tolerance_by_material` is declared.
- **Societal benefit:** curtain brackets are lost, mismatched, or the wrong
  projection for the window trim more often than any other window part. One
  parametric cradle sized to the rod and set clear of the trim outfits a whole
  house — end brackets and center supports included — instead of hunting a
  hardware aisle for a discontinued size.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The arm plunges into the near wall of the cradle ring (a solid overlap, not a
  tangent contact), so every part, cradle style, and preset renders
  **watertight**.
