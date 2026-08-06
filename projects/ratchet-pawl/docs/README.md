# Ratchet & Pawl

A **one-way motion mechanism** generated with **CadQuery** (B-Rep): a sawtooth
**ratchet wheel** plus a pivoting **pawl** arm that drops into the teeth, so the
wheel turns freely one way and locks the other. For winches, tie-down tensioners,
indexing tables, and hand tools.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ratchet Wheel** | `ratchet` | Asymmetric sawtooth wheel with a center bore. Each tooth is a gentle ramp up to the tip and a steep locking face down. |
| **Pawl Arm** | `pawl` | A rounded arm with a tail pivot hole, a tooth-engaging nose, and a spring tab for a return element. |
| **Assembly** | `assembly` | Wheel + pawl positioned as in service (fused for preview/staging). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ratchet Wheel | `outer_dia` | 50 mm | Diameter at the tooth tips. |
| Teeth | `teeth` | 16 | Number of sawtooth teeth. |
| Teeth | `rake_angle` | 20° | Lean of the steep locking face; higher = harder-locking. |
| Teeth | `tooth_depth` | 4.0 mm | Radial tooth height (clamped to 20 % of diameter). |
| Ratchet Wheel | `thickness` | 6.0 mm | Part thickness (Z). |
| Ratchet Wheel | `bore` | 8.0 mm | Center shaft bore. |
| Pawl | `pawl_length` | 40 mm | Length of the pivoting arm. |

## Presets

- **Winch Wheel (12T)** — coarse, hard-locking wheel for a hoist drum.
- **Fine Indexer (36T)** — many shallow teeth for fine angular indexing.
- **Ratchet + Pawl Demo** — the Assembly at default size.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Ratchet Sawtooth** (`spline`, internal) — the engaging tooth profile, defined
    by `teeth`, `rake_angle`, `outer_dia`, `tooth_depth`. The pawl nose is sized
    from the same tooth pitch, so a pawl built for a given tooth count + diameter
    seats in the matching wheel.
- **Material awareness:** printed clearances are declared via
  `tolerance_by_material` so the tip/nose engagement can be tuned per material.
- **Societal benefit:** the wheel is the part that shears first in winches and
  tensioners — printing wheel and pawl together in the exact tooth count keeps
  hoists and jigs working without a machine shop.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The wheel is one closed sawtooth polyline extruded to `thickness`; each boundary
  root vertex appears exactly once (a duplicated shared vertex would make a
  zero-length segment and break the wire), and `.close()` forms the final steep
  face. **All shipped presets, all modes, and both extremes render watertight.**
