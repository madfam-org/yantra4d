# VESA Arm Extender

Extends or offsets a VESA display mount for extra reach, wall clearance, or to
bridge two pattern sizes — built with **CadQuery** (B-Rep). Every part carries a
real **VESA MIS-D** bolt square (75×75 or 100×100, M4) on both a mount-side face
and a display-side face, so it drops transparently into a VESA screw chain.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Spacer** | `spacer` | Straight standoff — the same VESA square drilled through a solid block of height `offset`; pushes the display out from the wall. |
| **Offset Arm** | `offset_arm` | L/Z crank — a mount plate, a rising web, and a horizontal reach carry the pattern OUT and UP to a forward-facing display plate, clearing an obstruction. |
| **Combo Adapter** | `combo_adapter` | Standoff whose two faces carry **different** squares (75 ↔ 100), drilled as blind bores from each face with a solid core between; converts pattern size while offsetting. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| VESA Pattern | `vesa` | `100` | Mount-side square (75 or 100, both M4). |
| VESA Pattern | `dest_vesa` | `75` | Display-side square — Combo Adapter only. |
| Extension Geometry | `offset` | 40 mm | Standoff distance / crank reach. |
| Extension Geometry | `plate_thick` | 5.0 mm | Each VESA face-plate thickness. |
| Extension Geometry | `web_thick` | 6.0 mm | Crank web/column thickness (Offset Arm). |
| Extension Geometry | `plate_margin` | 11.0 mm | Material beyond the bolt square. |
| Extension Geometry | `corner_r` | 6.0 mm | Plate corner radius (0 = sharp). |
| Cable Management | `cable_slot` | on | Rounded cable pass-through channel. |
| Cable Management | `slot_w` | 16.0 mm | Cable slot width. |

## Presets

- **50 mm Standoff (100×100)** — a straight spacer pushing a 100-pattern display 50 mm off the wall.
- **Clearance Crank (100×100)** — an offset arm cranking a 100-pattern display out and up.
- **Combo 75 → 100 + 40 mm** — mounts a 75-pattern monitor onto a 100-pattern arm with 40 mm of offset.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **VESA MIS-D (mount face)** (`bolt_pattern`, standard **VESA MIS-D**) — the
    75×75 or 100×100 M4 square that bolts to the arm / wall bracket, defined by
    `vesa`, `plate_thick`, `plate_margin`.
  - **VESA MIS-D (display face)** (`bolt_pattern`, standard **VESA MIS-D**) — the
    square the monitor bolts to (`dest_vesa` differs in Combo), lifted by
    `offset`.
  - **Cable Pass-Through Slot** (`pocket`, internal) — routing channel from
    `cable_slot`, `slot_w`.
- **Material awareness:** the M4 clearance holes are printable clearance values
  tunable per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a commercial monitor arm ships with one reach and one
  pattern; this extender adds standoff, crank reach, or a 75 ↔ 100 conversion so
  an existing arm keeps serving a new display instead of buying a whole new mount.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- All three modes export **watertight**. The Combo Adapter keeps a ≥3 mm solid
  core between its two blind bore stacks so neither VESA pattern breaks through.
  The Offset Arm builds the mount plate, web, reach, and display plate as boxes,
  drills each pattern in its own axis, and fuses them into one manifold solid.
