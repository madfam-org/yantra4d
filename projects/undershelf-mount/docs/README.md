# Under-Shelf / Under-Desk Mount

Reclaims the dead space under a shelf, desk, or cabinet, built with **CadQuery**
(B-Rep). A shelf-edge clamp grips over the surface (no tools, no drilling) or a
screw plate fixes to the underside, carrying a payload that hangs below.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Edge Clamp + Payload** | `clamp_bin` | A C-clamp that hooks over the shelf edge (`surface_t` thick) with the selected payload hanging beneath. |
| **Screw Plate + Payload** | `screw_cradle` | A flat plate that screws up into the underside of the surface, with the selected payload beneath — a permanent, load-bearing fix. |
| **Edge Hook** | `edge_hook` | The C-clamp with a simple downward hook, for cables, headphones, or bags. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on. The `payload` select (bin / router cradle /
power-strip cradle / hook) chooses what hangs below in the two payload modes.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Attachment | `payload` | `bin` | Hanging payload (bin / router_cradle / strip / hook). |
| Attachment | `screw_dia` | 4.2 mm | Underside screw clearance (screw mode); #8 ≈ 4.2. |
| Surface & Clamp | `surface_t` | 25 mm | Thickness of the shelf/desk the clamp grips over. |
| Surface & Clamp | `grip_len` | 35 mm | How far the clamp jaw reaches over the surface top. |
| Surface & Clamp | `clamp_clear` | 0.4 mm | Slide-on play between the clamp and the surface. |
| Surface & Clamp | `width` | 70 mm | Mount width along the shelf edge. |
| Surface & Clamp | `wall_t` | 4.0 mm | Material thickness of clamp / plate / payload. |
| Hanging Payload | `payload_depth` | 60 mm | How far the payload projects out from the edge. |
| Hanging Payload | `payload_height` | 45 mm | How far the payload hangs below the mount. |

## Presets

- **Under-Desk Parts Bin** — an edge clamp with an open parts bin.
- **Under-Shelf Router Cradle** — a wide screw plate with a router cradle.
- **Desk-Edge Headphone Hook** — a narrow edge clamp with a downward hook.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Shelf-Edge Clamp** (`snap`, internal) — the C that grips the surface,
    defined by `surface_t`, `grip_len`, `clamp_clear`, `width`, `wall_t`. This is
    the interface that mates to the physical shelf edge.
  - **Underside Screw Plate** (`bolt_pattern`, internal) — the four-screw plate
    (`screw_dia`, `width`, `payload_depth`) for the permanent fix.
  - **Hanging Payload Carrier** (`profile`, internal) — `payload`, `payload_depth`,
    `payload_height`, `width`, `wall_t` define the bin / cradle / hook that hangs
    beneath either attachment.
- **Material awareness:** `clamp_clear` is a printer/material-tunable slide fit;
  `tolerance_by_material` is declared.
- **Societal benefit:** turns wasted under-surface space into storage without
  buying furniture — one parametric mount clamps or screws under any shelf or desk
  and carries the bin, cradle, or hook a workspace actually needs, sized to the
  real surface thickness.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): all injected parameters are
  read once at module scope via `PARAM(lambda: name, default)`; the final solid is
  assigned to `result`.
- The clamp is a solid outer block minus the shelf slot (mouth open toward the
  shelf, closed at the back web), so it is a true watertight C; the payload's top
  fuses at z=0 to whichever attachment holds it. All three modes export watertight
  and are volumetrically distinct; the two payload modes share one bin/cradle/hook
  builder so the hanging part is identical whichever attachment is used.
