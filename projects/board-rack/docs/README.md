# Board Wall Rack

A wall bracket that holds a ski, snowboard, or SUP paddle in a horizontal slot
sized to the board thickness, generated with **CadQuery** (B-Rep). Print a pair
and mount them apart to carry a board flat against the wall.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ski Rack** | `ski_rack` | Narrow slot for skis on edge. |
| **Snowboard Rack** | `snowboard_rack` | Wider slot, longer arm for a snowboard. |
| **Paddle Rack** | `paddle_rack` | Small cradle for a SUP/kayak paddle shaft. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Board Slot | `slot_w` | 28 mm | Board/shaft thickness the slot cradles. |
| Board Slot | `arm_len` | 90 mm | Arm reach from the wall. |
| Board Slot | `arm_w` | 40 mm | Arm width along the wall. |
| Board Slot | `lip_h` | 22 mm | Up-turned front retaining lip. |
| Bracket & Mount | `wall` | 6 mm | Bracket wall thickness. |
| Bracket & Mount | `plate_h` | 90 mm | Wall plate height. |
| Bracket & Mount | `screw_dia` | 5 mm | Wall screw clearance. |

## Presets

- **Alpine Skis (pair)** — 28 mm slot.
- **Snowboard (flat)** — 30 mm slot, 130 mm arm.
- **SUP Paddle** — 32 mm cradle.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Board Slot** (`rail`, internal) — the horizontal board channel every variant
    shares, defined by `slot_w`, `arm_len`, `arm_w`, `lip_h`.
  - **Wall Mount** (`bolt_pattern`, internal) — the two-screw wall pattern,
    `plate_h`, `screw_dia`, `wall`.
- **Material awareness:** `tolerance_by_material` declared — slot fit adapts to the
  printed material.
- **Societal benefit:** bulky product-specific board racks replaced by a printable
  slot bracket sized to any board, reclaiming floor space.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The board slot is an open channel cut into the arm top with a floor and side
  walls left, plus an up-turned lip and an under-arm gusset for strength.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
