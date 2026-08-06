# Magnetic Tool Strip

A wall-mounted magnetic strip that holds screwdrivers, pliers, knives, and other
steel tools on a row of embedded disc magnets — built with **CadQuery** (B-Rep).
The magnets drop into blind pockets on the front face; wall screws pass through
countersunk holes near the ends. Glue the magnets in, screw the strip up, and
tools snap on.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Flat Strip** | `strip` | A flat magnetic bar: magnet pockets on the front, wall screws near the ends. |
| **Shelf Strip** | `shelf_strip` | The flat strip plus a bottom ledge with a lip, so heavier tools rest on a shelf as well as stick to the magnets. |
| **Corner Strip** | `corner_strip` | An L-section strip that wraps an inside wall corner, screwing to both faces; the magnet row stays on the main face. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Strip Body | `length` | 200 mm | Strip length. |
| Strip Body | `height` | 25 mm | Face height. |
| Strip Body | `thickness` | 8.0 mm | Body thickness (> magnet depth + backing). |
| Magnets | `magnet_dia` | 6.0 mm | Disc magnet diameter. |
| Magnets | `magnet_th` | 2.0 mm | Disc magnet thickness = pocket depth. |
| Magnets | `magnet_count` | 6 | Number of magnet pockets (evenly spaced). |
| Magnets | `magnet_wall` | 1.2 mm | Backing left behind each pocket. |
| Wall Mount | `wall_screw` | 4.5 mm | Wall screw clearance. |
| Wall Mount | `countersink` | on | Cone the screw holes flush. |
| Shelf / Corner | `ledge_depth` | 15.0 mm | Bottom shelf depth (Shelf Strip). |
| Shelf / Corner | `leg_b` | 25.0 mm | Return leg depth (Corner Strip). |

## Presets

- **Screwdriver Strip (6×2 magnets)** — a 200 mm flat strip with six 6×2 mm magnet pockets.
- **Heavy Tool Shelf (8×3 magnets)** — a 250 mm shelf strip with eight 8×3 mm pockets and an 18 mm ledge.
- **Corner Knife Strip** — a 150 mm corner strip with five 6×2 mm pockets.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Magnet Pocket Array** (`pocket`, internal) — the row of blind magnet
    pockets, defined by `magnet_dia`, `magnet_th`, `magnet_count`, `magnet_wall`.
    All pockets are cut in a **single `pushPoints` operation**, and never break
    through the back (a `magnet_wall` web remains), so the strip stays watertight.
  - **Wall Screw Pattern** (`bolt_pattern`, internal) — the two countersunk
    wall-mounting holes (`wall_screw`, `countersink`) near the strip ends.
- **Material awareness:** the magnet pocket and screw clearances are printable
  values tunable per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** magnetic tool bars ship in fixed lengths with fixed
  magnet spacing; a strip sized to the wall, the tools, and the exact disc
  magnets on hand turns a handful of cheap magnets into a workshop organizer.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Pocket depth is clamped to `thickness − magnet_wall` so the blind magnet
  pockets can never break through the back face. All three modes export
  watertight, and `magnet_count` scales the pocket row without affecting fit.
