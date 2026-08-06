# Shampoo / Bottle Wall Bracket

Shower-shelf brackets and pump-bottle holders generated with **CadQuery**
(B-Rep), sized to the **real bottle bodies** they carry: shampoo / conditioner
bottles (~55–90 mm across the body) and pump dispensers (~50–75 mm). Three
distinct socket / rail modes.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Shelf Ring** | `shelf_ring` | A wall shelf slab with one or more through ring cutouts a bottle drops into — upright, or inverted to drain the last of it. Screw mounts on the back plate. |
| **Neck Hook** | `neck_hook` | A wall plate with a keyhole that grips a pump bottle **under its neck collar** (wide entry narrows to a `neck_d` slot), so the bottle hangs nozzle-down. |
| **Body Clip** | `body_clip` | A C-clip that snaps around the bottle **body**; the open front lets the bottle press in. Mounts flat to the wall. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bottle | `bottle_d` | 70 mm | Bottle body diameter. Shampoo ~55–90, pump ~50–75. |
| Bottle | `neck_d` | 28 mm | Pump-bottle neck diameter caught under the collar (neck hook). |
| Bottle | `count` | 1 | How many ring cutouts the shelf has (1–4). |
| Bracket Body | `wall` | 4 mm | Wall and rim thickness. |
| Bracket Body | `depth` | 55 mm | How far the shelf / clip projects from the wall. |
| Bracket Body | `plate_h` | 50 mm | Back-plate height against the wall. |
| Wall Mount | `screw_d` | 4.2 mm | Wall-mount screw clearance (M4 ~4.2 mm). |

## Presets

- **Single Shampoo Shelf** — one 75 mm ring.
- **Triple Shower Caddy** — three 65 mm rings on one shelf.
- **Pump-Bottle Hanger** — neck hook for a 60 mm / 28 mm-neck dispenser.
- **Body Snap Clip** — a 70 mm C-clip.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Bottle Body Socket** (`socket`, *internal*) — the ring / clip bore sized by
    `bottle_d` (and `count`); the interface that captures a bottle body.
  - **Pump Neck Catch** (`socket`, *internal*) — the keyhole neck slot (`neck_d`)
    that catches under a pump collar.
  - **Wall Screw Mount** (`bolt_pattern`, *ISO 7045 M4*) — the screw clearance.
- **Material awareness:** `tolerance_by_material` is declared — the ring / clip
  fit is set by `bottle_d` and `wall` so it can be tuned per filament / printer.
- **Societal benefit:** shower shelving is usually a suction-cup product that
  fails or an over-priced caddy sized for nothing; fitting to a real bottle body
  or pump neck lets anyone screw-mount a bracket that holds the bottle they use.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Watertight by construction:** the blank is filleted **before** cutting; ring
  cutouts pass through the slab top-to-bottom (they drain, never trap a void);
  the neck keyhole and the C-clip bore are cut through both plate faces; screw
  holes open through to the back. All three modes and the MIN/MAX extremes render
  watertight with a single body.
