# Golf Accessory Set

Small course accessories sized to a standard golf ball (42.7 mm) and tee,
generated with **CadQuery** (B-Rep). A tee holder, a coin-style ball marker, and
a putting alignment tool — the ball/tee dimensions are the shared interface.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Tee Holder** | `tee_holder` | Block with a row of tee sockets + belt clip. |
| **Ball Marker** | `ball_marker` | Coin-style disc marker with a grip rim. |
| **Alignment Tool** | `alignment_tool` | Ball cradle with a pen slot to draw a line. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ball & Tee | `ball_dia` | 42.7 mm | Golf ball diameter (standard 42.67 mm). |
| Ball & Tee | `tee_dia` | 5.5 mm | Tee shaft diameter. |
| Ball & Tee | `wall` | 3.0 mm | Body wall thickness. |
| Variant Options | `tee_count` | 5 | Tees the holder carries. |
| Variant Options | `marker_dia` | 24 mm | Ball marker disc diameter. |
| Variant Options | `slot_w` | 2.2 mm | Alignment pen-slot width. |

## Presets

- **Five-Tee Belt Clip** — 5-tee holder.
- **Coin-Style Marker** — 24 mm disc marker.
- **Putting Line-Up Tool** — ball cradle with a 2.2 mm pen slot.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Golf Accessory** (`profile`, internal) — the ball/tee-indexed geometry shared
    by the set, defined by `ball_dia`, `tee_dia`, `marker_dia`, `slot_w`.
- **Material awareness:** `tolerance_by_material` declared — tee socket, marker
  stub, and pen slot fits adapt to the printed material.
- **Societal benefit:** cheap golf-accessory impulse buys pile up as landfill; a
  printable set sized to the standard ball and tee replaces them with one design.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**; each part exports as one connected body.
