# Guitar Pick Holder & Punch

Store, carry, and make guitar picks, generated with **CadQuery** (B-Rep). The
shared geometric denominator is the classic **351 pick outline** (a rounded
equilateral triangle), so every part references the same real pick footprint.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pocket Clip** | `pick_clip` | Slim pocket clip holding a pick stack. |
| **Wall Tray** | `wall_holder` | Wall tray with N pick slots. |
| **Pick Punch Template** | `pick_punch_template` | Flat stencil with the 351 outline cut through. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pick Shape | `pick_size` | 31 mm | Overall pick span (351 ≈ 31 mm). |
| Pick Shape | `pick_count` | 6 | Picks in the clip stack / wall slots. |
| Pick Shape | `pick_th` | 1.0 mm | Single pick thickness (sizes stack/slots). |
| Body & Mount | `wall` | 2.4 mm | Body wall thickness. |
| Body & Mount | `mount` | screw | Wall tray attachment (screw / adhesive). |
| Body & Mount | `screw_dia` | 4 mm | Wall screw clearance. |
| Body & Mount | `plate_t` | 3 mm | Punch template plate thickness. |

## Presets

- **Belt / Strap Clip** — 6-pick pocket clip.
- **Desk / Wall Tray** — 10-slot screw-mount tray.
- **Standard 351 Stencil** — 31 mm punch template.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Pick Outline (351)** (`profile`, internal) — the rounded-triangle pick
    footprint shared by all three parts, defined by `pick_size`, `pick_th`.
- **Material awareness:** `tolerance_by_material` declared — slot/stack sizing
  adapts to the printed material's fit.
- **Societal benefit:** picks are cheap but constantly lost; the shared outline
  lets anyone store, carry, and even cut their own from scrap sheet.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- The 351 outline is built from three tangent `threePointArc` curves.
- All shipped presets render **watertight**.
