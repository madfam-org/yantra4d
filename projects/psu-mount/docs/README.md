# Power Supply / PSU Mount

Mounts an enclosed switching PSU of the **Meanwell LRS / RS** family to a panel
or a 2020 aluminium extrusion, built with **CadQuery** (B-Rep). Pick a model for
the real case footprint and bottom mounting-hole pitch, or Custom for any
enclosed supply.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Panel Feet** | `foot_bracket` | A pair of L-feet bolting to the PSU's own bottom holes; each foot flange has an adjustable panel-screw slot. |
| **2020 Extrusion Mount** | `extrusion_mount` | The same feet, but each flange carries a 2020 T-slot bolt pair (fixed M5 at 20 mm pitch) to drop onto extrusion. |
| **Band Strap** | `strap` | An open inverted-U band that wraps the PSU body (case + clearance) with two panel feet — needs no access to the PSU's holes. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on.

## Supported PSU footprints

| Model | Case (W×D×H) | Approx. hole pitch (X×Y) | Case screw |
| :--- | :--- | :--- | :--- |
| **LRS-50** | 99 × 82 × 30 | 95 × 50 | M3 |
| **LRS-100** | 129 × 97 × 30 | 124 × 50 | M3 |
| **LRS-350** | 215 × 115 × 30 | 205 × 60 | M4 |
| **Custom** | `custom_w` × `custom_d` × 30 | `custom_px` × `custom_py` | `case_screw_dia` |

Hole pitches are the approximate on-centre bottom-mount squares Meanwell provides;
verify against the datasheet for a production run, or use Custom to set them
exactly.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| PSU Model | `psu_size` | `LRS-100` | Footprint select (or `custom`). |
| Custom Footprint | `custom_w` / `custom_d` | 129 / 97 mm | Case size when `psu_size = custom`. |
| Custom Footprint | `custom_px` / `custom_py` | 124 / 50 mm | Mounting-hole pitch when custom. |
| Custom Footprint | `case_screw_dia` | 3.4 mm | Case screw clearance (M3 ≈ 3.4, M4 ≈ 4.5). |
| Bracket | `thickness` | 4.0 mm | Feet / band material thickness. |
| Bracket | `foot_h` | 22 mm | Height the foot web rises up the PSU side. |
| Bracket | `strap_gap` | 0.8 mm | Per-side band-to-case clearance (strap). |
| Panel Mounting | `panel_screw` | 4.5 mm | Panel screw clearance (M4 ≈ 4.5); extrusion mode uses fixed M5. |

## Presets

- **LRS-100 on Panel** — L-feet with panel slots for the common 100 W supply.
- **LRS-350 on 2020** — extrusion feet for a large supply on an aluminium frame.
- **LRS-50 Band Strap** — an open band clamp for the small 50 W supply.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **PSU Mount Holes** (`bolt_pattern`, standard *Meanwell LRS/RS*) — the case
    mounting square, defined by `psu_size` / `custom_px` / `custom_py` /
    `case_screw_dia`. This is the interface that bolts to the PSU itself.
  - **2020 T-Slot Pattern** (`bolt_pattern`, standard *20 mm T-slot*) — the M5
    extrusion bolt pair on the flange (extrusion mode).
  - **Panel Mounting Face** (`profile`, internal) — `thickness`, `foot_h`,
    `panel_screw` define the flat face that meets the panel. The shared
    `bolt_grid` helper drills every pattern.
- **Material awareness:** clearance diameters are printer/material-tunable;
  `tolerance_by_material` is declared.
- **Societal benefit:** keeps salvaged and off-the-shelf industrial supplies
  serviceable — a printable mount matching the real Meanwell hole pattern lets any
  panel or 2020 build reuse a PSU without a proprietary chassis or drilling jig.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): all injected parameters are
  read once at module scope via `PARAM(lambda: name, default)` (so ruff sees the
  bindings), and the final solid is assigned to `result`.
- Each foot is one fused L (web + flange), mirrored to both case-hole columns;
  the strap is a solid outer block minus an interior channel plus two feet — all
  watertight. Feet and extrusion modes share the same web/flange but differ in
  flange drilling (adjustable slot vs T-slot bolt pair).
