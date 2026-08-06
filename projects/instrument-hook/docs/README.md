# Instrument Wall Hook

A wall hanger that cradles a stringed instrument by its **neck**, generated with
**CadQuery** (B-Rep). Sized by the neck width so the rounded saddle fits a
guitar, bass, violin, or ukulele exactly, with a stud-screw back plate.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Guitar Hook** | `guitar_hook` | Full-size single cradle on a wall plate. |
| **Violin / Ukulele Hook** | `violin_hook` | Narrower cradle on a smaller plate. |
| **Double Hook** | `multi_hook` | Two cradles on one wide plate. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Neck Cradle | `neck_w` | 52 mm | Neck width at the nut — sizes the saddle. |
| Neck Cradle | `arm_gap` | 32 mm | Vertical opening the neck sits in. |
| Neck Cradle | `arm_thick` | 12 mm | Arm and lip thickness. |
| Neck Cradle | `reach` | 55 mm | How far the cradle projects from the wall. |
| Wall Plate | `plate_w` / `plate_h` | 70 / 90 mm | Back plate size. |
| Wall Plate | `plate_t` | 8 mm | Back plate thickness. |
| Wall Plate | `screw_dia` | 5 mm | Stud-screw clearance holes. |

## Presets

- **Electric Guitar** — 52 mm neck, 55 mm reach.
- **Bass Guitar** — 62 mm neck, thicker arms.
- **Ukulele / Violin** — narrow 36 mm cradle.
- **Twin Guitar Rack** — double hook, taller plate.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Neck Cradle** (`pocket`, internal) — the rounded neck saddle, defined by
    `neck_w`, `arm_gap`, `arm_thick`, `reach`.
  - **Stud Screw Mount** (`bolt_pattern`, internal) — the two-screw wall pattern,
    `plate_w`, `plate_h`, `plate_t`, `screw_dia`.
- **Material awareness:** `tolerance_by_material` declared — print in a softer
  padding-friendly filament (TPU-lined or PLA) per instrument finish.
- **Societal benefit:** instrument storage sized to the exact neck, keeping
  guitars and violins off the floor without dent-prone generic hooks.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
