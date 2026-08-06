# Pedalboard Pedal Mount

Fixes guitar effects pedals to a pedalboard, generated with **CadQuery** (B-Rep)
and sized by the pedal footprint. Every part indexes off one **pedalboard rail
slot** so mounts, risers, and power cradles share a common attachment geometry.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rail Mount** | `rail_mount` | Edge-gripping bracket; `mount` picks rail slot / hook-and-loop / riser feet. |
| **Angle Riser** | `riser` | Wedge riser to a viewing angle, rail hook underneath. |
| **Power Bracket** | `power_bracket` | Under-board cradle for a power-supply brick. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pedal Footprint | `mount` | rail | Attach method for the rail mount. |
| Pedal Footprint | `pedal_w` / `pedal_d` | 66 / 120 mm | Pedal footprint. |
| Pedal Footprint | `grip_h` | 10 mm | Front-edge grip lip height. |
| Pedal Footprint | `wall` | 4.0 mm | Bracket wall thickness. |
| Board Rail | `rail_w` / `rail_t` | 18 / 6 mm | Board rail the hook clips onto. |
| Riser & Power | `riser_angle` | 12° | Riser tilt angle. |
| Riser & Power | `brick_w` / `brick_h` | 60 / 35 mm | Power brick size. |

## Presets

- **Standard Compact Pedal** — 66×120 rail mount.
- **Back-Row Riser (12°)** — viewing-angle riser.
- **Power-Supply Cradle** — under-board power bracket.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Pedalboard Rail** (`rail`, internal) — the rail-hook slot every part clips
    to, defined by `rail_w`, `rail_t`, `wall`.
  - **Pedal Edge Grip** (`pocket`, internal) — the pedal-hugging lip, `pedal_w`,
    `pedal_d`, `grip_h`.
- **Material awareness:** `tolerance_by_material` declared — rail slot and brick
  pocket fits adapt to the printed material.
- **Societal benefit:** expensive, pedal-specific board hardware replaced by a
  commons mount indexed to the board rail.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
