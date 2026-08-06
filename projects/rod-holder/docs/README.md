# Fishing Rod Holder

Holds a fishing rod by its butt in a cradle socket sized to the rod diameter,
generated with **CadQuery** (B-Rep). The socket is the shared interface; three
mounts present it three ways.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wall Holder** | `wall_holder` | Screw plate with a leaning rod socket. |
| **Rail Clamp** | `rail_holder` | Clamp for a boat/rail tube, rod angled out. |
| **Ground Stake** | `ground_stake` | Spike + vertical socket for bank fishing. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rod & Socket | `rod_dia` | 26 mm | Rod handle/butt diameter. |
| Rod & Socket | `socket_len` | 70 mm | Socket seating depth. |
| Rod & Socket | `wall` | 4.0 mm | Body wall thickness. |
| Mount | `lean` | 15° | Socket lean angle (wall / rail). |
| Mount | `plate_w` | 50 mm | Wall plate width. |
| Mount | `screw_dia` | 4.5 mm | Wall screw clearance. |
| Mount | `rail_dia` | 25 mm | Boat/rail tube diameter. |
| Mount | `stake_len` | 160 mm | Ground spike length. |

## Presets

- **Garage Wall Rack** — leaning wall holder.
- **Boat Rail Clamp** — 25 mm rail clamp.
- **Bank Fishing Stake** — 180 mm ground stake.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Rod Cradle** (`socket`, internal) — the rod-butt socket shared by all three
    mounts, defined by `rod_dia`, `socket_len`, `wall`.
- **Material awareness:** `tolerance_by_material` declared — socket fit adapts to
  the printed material.
- **Societal benefit:** generic rod holders never fit a specific rod or mount; one
  socket printable three ways lets any angler store and fish with fitted gear.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
