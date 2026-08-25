# Compliant Gripper Pad

A **compliant jaw pad** — the wear surface between a hard gripper and a soft part
— generated with **CadQuery** (B-Rep). A ribbed face deflects under load so the
grip spreads across an irregular part instead of concentrating on one high spot.
Rib pitch is the compliance knob, and it is published, not buried.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Why this cartridge exists

This is the **bridge** between the commons' soft-robotics family and its existing
industrial grippers. It bolts to the same patterns `tool-gripper` and
`pneu-net-finger` already use, so an existing rigid gripper gains compliance
without being redesigned. Deliberately built from **patterned boolean ribs** — no
organic sculpture, nothing that needs a mesh kernel.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flat Pad** | `flat_pad` | The ribbed flat pad — the general wear surface. |
| **Vee Pad** | `vee_pad` | A V-groove face that self-centres round stock. |
| **Dovetail Pad** | `dovetail_pad` | The pad on a dovetail back, for tool-free swapping. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pad | `pad_len` | 50.0 mm | Pad length. |
| Pad | `pad_w` | 30.0 mm | Pad width. |
| Pad | `back_th` | 4.0 mm | Solid backing plate behind the ribs. |
| Ribs | `rib_pitch` | 5.0 mm | **The compliance knob** — closer ribs are stiffer, wider ribs deflect more. |
| Ribs | `rib_w` | 2.0 mm | Rib thickness. |
| Ribs | `rib_h` | 4.0 mm | Rib height above the backing. |
| Ribs | `rib_taper` | 0.6 | Tip/root width ratio — lower tapers to a softer tip. |
| Vee | `vee_angle` | 90.0 deg | Included angle of the V-groove. |
| Mount | `bolt_span` | 34.0 mm | Bolt centre spacing — match the jaw it replaces. |
| Mount | `bolt_dia` | 4.3 mm | Bolt clearance (4.3 = M4). |
| Dovetail | `dove_w` | 16.0 mm | Dovetail width. |
| Dovetail | `dove_h` | 6.0 mm | Dovetail depth. |

## Presets

- **Standard Flat Pad** — the general-purpose wear face.
- **Soft Grip** — wide rib pitch and a strong taper, for fragile parts.
- **Vee Pad for Round Stock** — self-centring on tube and bar.
- **Quick-Swap Dovetail** — tool-free pad changes.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:**
  - **Rib Compliance Profile** (`profile`, internal) — `rib_pitch`, `rib_w`,
    `rib_h`, `rib_taper`. Compliance is a published, tunable interface rather
    than a fixed property of the part.
  - **Jaw Bolt Pattern** (`bolt_pattern`, internal) — `bolt_span`, `bolt_dia`,
    `pad_len`, `pad_w`. Compatible with `tool-gripper` and `pneu-net-finger`.
  - **Accessory Dovetail** (`rail`, internal) — `dove_w`, `dove_h`, `back_th`.
- **Material awareness:** rib geometry and `back_th` are exposed so the same pad
  can be printed rigid or in TPU; `tolerance_by_material` is declared.
- **Societal benefit:** gripper pads are a wear consumable normally bought as
  proprietary inserts; an open pad on the existing bolt patterns lets a shop
  reprint its own and tune the compliance to the part it is actually gripping.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Ribs are **unioned onto** the backing plate (never cut into a shell), and rib
  count is derived from length and pitch with a floor of 1, so no rib can ever be
  left floating.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
