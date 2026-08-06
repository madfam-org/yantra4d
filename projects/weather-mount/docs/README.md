# Weather-Instrument Mount

Mounts a rain gauge, thermometer, anemometer, or other backyard weather sensor to
a **pole or a fence**. Generated with **CadQuery** (B-Rep). A split clamp wraps a
round pole (the **Pole Clamp** socket); a flat plate screws to a fence; a cradle
ring holds a cylindrical instrument. All three share one **Mounting Boss**, so the
cradle plugs into either mount.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pole Clamp** | `pole_clamp` | A C-shaped split band with bolt ears that wraps a round pole, carrying the mounting boss on its back. |
| **Fence Mount** | `fence_mount` | A flat plate with four corner screw holes and the same boss on its front face. |
| **Gauge Cradle** | `gauge_cradle` | A C-ring that clips around a cylindrical instrument, with a male plug that fits the boss. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pole Clamp | `pole_dia` | 34 mm | Pole outer diameter the band wraps. |
| Pole Clamp | `clamp_wall` | 5.0 mm | Band / fence-plate thickness. |
| Pole Clamp | `clamp_h` | 30 mm | Band height. |
| Pole Clamp | `bolt_dia` | 5.0 mm | Clamp bolt / fence screw. |
| Mounting Boss | `boss_dia` | 20 mm | Shared boss diameter (the interface). |
| Mounting Boss | `boss_len` | 22 mm | Boss projection / cradle plug depth. |
| Mounting Boss | `clearance` | 0.4 mm | Per-side boss/plug slop. |
| Cradle & Plate | `cradle_dia` | 40 mm | Instrument body diameter (cradle). |
| Cradle & Plate | `cradle_h` | 35 mm | Cradle ring height. |
| Cradle & Plate | `plate_w` | 60 mm | Fence-plate width. |
| Cradle & Plate | `plate_h` | 80 mm | Fence-plate height. |

## Presets

- **Round Fence Post** — the pole clamp for a 34 mm post.
- **Flat Fence Board** — the screw-on plate mount.
- **Rain-Gauge Cradle** — a ring sized to a typical rain gauge.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Pole Clamp** (`socket`, internal) — the pole-wrap interface defined by
    `pole_dia`, `clamp_wall`, `clamp_h`, `bolt_dia`; sizes the band to any round
    pole or post.
  - **Mounting Boss** (`socket`, internal) — the shared accessory interface defined
    by `boss_dia`, `boss_len`, `clearance`. The clamp and the fence plate both
    present the female boss; the cradle's male plug fits either, so an instrument
    moves between pole and fence with no new hardware.
- **Material awareness:** `clearance` is exposed so the boss/plug fit can be tuned
  per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** citizen weather stations must survive outdoors on whatever
  pole or fence a household already has — a printable clamp + plate sharing one
  boss lets any gauge be sited and re-sited without vendor-specific hardware,
  supporting community climate-data collection.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. The mounting boss
  embeds through its carrier wall so every part prints as one connected body.
- All shipped presets and every mode render **watertight** as a single solid body.
