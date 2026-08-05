# Laptop / Monitor Riser

A desk riser generated with **CadQuery** (B-Rep) that lifts a laptop or monitor
to eye or airflow height on two solid side panels or four corner posts, with a
rear cable pass-through and open space underneath to slide a keyboard.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Riser** | `riser` | A flat top platform on legs — the general desk riser. |
| **Monitor Stand** | `monitor_stand` | Taller (raised to ≥ 110 mm) on a narrower, inboard-set base for a monitor that sits behind the keyboard. |
| **Laptop Stand** | `laptop_stand` | A top platform with a forward typing tilt and a row of ventilation slots cut through it for laptop airflow. |

The studio dispatches the active part via `target_part`
(`riser` / `monitor_stand` / `laptop_stand`); each mode renders distinct
geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Platform & Height | `height` | 95.0 mm | Open clearance under the platform. |
| Platform & Height | `plat_w` / `plat_d` | 260 / 240 mm | Top platform size. |
| Platform & Height | `plat_t` | 6.0 mm | Platform thickness. |
| Legs | `leg_style` | `solid_sides` | `solid_sides` panels or four `posts`. |
| Legs | `leg_t` | 6.0 mm | Panel / post thickness (posts auto-widened). |
| Cable & Airflow | `cable_slot` | on | Rear cable pass-through. |
| Cable & Airflow | `cable_w` | 60.0 mm | Cable slot width. |
| Cable & Airflow | `vents` | on | Ventilation slots (Laptop Stand). |
| Cable & Airflow | `kbd_slot` | on | Keep underside open for a keyboard. |
| Cable & Airflow | `tilt` | 6° | Typing tilt (Laptop Stand). |

## Presets

- **Wide Desk Riser** — a 300 mm solid-side riser with cable slot and keyboard space.
- **Monitor Riser** — a 120 mm-high, 8 mm-thick platform for a monitor base.
- **Laptop Stand (vented)** — a post-legged, vented, 8° tilted laptop stand.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Riser Footprint** (`profile`, internal) — the leg span and platform
    envelope, defined by `height`, `plat_w`, `plat_d`, `leg_style`, `leg_t`.
  - **Cable Pass-Through** (`socket`, internal) — `cable_slot`, `cable_w`.
  - **Ventilation Slot Grid** (`grid`, internal) — the airflow slot array
    (`vents`, `plat_w`, `plat_d`).
- **Material awareness:** wall/post thickness drives load capacity; heavier
  monitors want a thicker `plat_t` and solid sides. `tolerance_by_material` is
  declared for the cable-slot and keyboard fit.
- **Societal benefit:** raising a screen to eye level and a laptop into airflow
  is basic ergonomics and thermal health; a made-to-fit riser replaces bulky
  retail stands and improves posture without buying furniture.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Big flat parts are fine here. The tilted Laptop Stand top is built as a solid
  extruded wedge (watertight by construction) and all slots are cut with bores
  that overshoot the plate, so every mode and preset renders **watertight**.
