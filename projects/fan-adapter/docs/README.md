# Fan Grill / Duct Adapter

PC and printer fan accessories built on the standard PC-fan screw square,
generated with **CadQuery** (B-Rep). A fan table gives the correct corner-hole
spacing for 40 / 60 / 80 / 120 / 140 mm fans; build a finger-guard grill, a
tapered duct, or a filter frame.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Fan sizes

| `fan_size` | Body (mm) | Corner-hole spacing (mm) |
| :--- | :--- | :--- |
| `40mm` | 40 | 32 |
| `60mm` | 60 | 50 |
| `80mm` | 80 | 71.5 |
| `120mm` | 120 | 105 |
| `140mm` | 140 | 124.5 |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Finger Guard** | `grill` | Square frame + central hub + concentric rings + radial spokes over the bore, plus the four corner mounting holes. Built entirely from unioned solids, so it exports **watertight**. |
| **Duct Adapter** | `duct` | A hollow tapered duct: square fan flange lofted to a round outlet of `outlet_dia`. |
| **Filter Frame** | `filter_frame` | A shallow frame with a media pocket and floor cross-ribs that clamps a filter over the fan. |

Render each mode with `target_part` set to that mode's part id to see the
distinct part.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Fan Size | `fan_size` | 120mm | Sets body and corner-hole spacing. |
| Grill | `thickness` | 3.0 mm | Grill guard / duct flange thickness. |
| Grill | `ring_count` | 4 | Concentric rings between hub and rim. |
| Grill | `spoke_count` | 6 | Radial spokes. |
| Grill | `bar_w` | 2.4 mm | Ring / spoke bar width. |
| Duct | `duct_len` | 40 mm | Axial length of the taper. |
| Duct | `outlet_dia` | 80 mm | Round outlet diameter. |
| Duct | `duct_wall` | 2.4 mm | Duct tube wall thickness. |
| Filter | `filter_depth` | 6.0 mm | Filter-media pocket depth. |

## Presets

- **120 mm Finger Guard** — 4 rings, 6 spokes.
- **80 → 60 mm Duct** — adapts an 80 mm fan face to a 58 mm outlet.
- **140 mm Filter Frame** — an 8 mm-deep filter frame.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Fan Screw Pattern** (`bolt_pattern`, *PC fan 40-140mm*) — the four
    corner mounting holes, selected by `fan_size`. Every mode presents the same
    fan screw square, so any accessory bolts to the matching fan.
  - **Duct Outlet Profile** (`profile`, internal) — `outlet_dia`, `duct_len`,
    `duct_wall`: the round outlet the duct adapts to.
  - **Filter Media Pocket** (`pocket`, internal) — `fan_size`, `filter_depth`:
    the recess that holds the filter disc.
- **Material awareness:** `tolerance_by_material` is declared so the corner-hole
  clearance can be tuned per filament/printer.
- **Societal benefit:** the PC-fan screw square is a universal interface;
  on-demand guards, ducts, and filter frames keep fingers safe, direct airflow,
  and add filtration to hardware never designed for it.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`
  and the active part is selected through `target_part`.
- The grill is assembled from positive solids (rings, spokes, hub, frame) so its
  mesh is watertight. All shipped presets and defaults render **watertight**.
