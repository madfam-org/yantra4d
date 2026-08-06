# VESA Adapter Plate (75<->100)

The **VESA FDMI / MIS-D** flat-display mounting standard, generated with
**CadQuery** (B-Rep): square bolt patterns of **75 x 75 mm** and **100 x 100 mm**
(both M4). This adapter reconciles a display that exposes one pattern with an arm
that expects the other. Part of the **Yantra4D Hyperobjects Commons**. Official
visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **75->100 Flat Adapter** | `adapter_75_to_100` | A flat slab drilled with **both** the 75 mm and 100 mm VESA squares plus a central cable pass-through — the display's 75 mm pattern and the arm's 100 mm pattern share one plate. |
| **100->75 Stand-off Adapter** | `adapter_100_to_75` | Carries the 100 mm square on the base and a raised solid boss carrying the 75 mm square, lifting a recessed monitor back clear of the arm. |
| **Universal Slotted Plate** | `combo_universal` | Both squares cut as short radial obround slots so slightly off-spec displays still bolt up. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Plate | `plate_t` | 5.0 mm | Base slab thickness. |
| VESA Patterns | `vesa_small` | 75.0 mm | MIS-D 75 bolt-square spacing. |
| VESA Patterns | `vesa_large` | 100.0 mm | MIS-D 100 bolt-square spacing. |
| Holes & Cable | `bolt_d` | 4.5 mm | M4 clearance hole diameter. |
| Holes & Cable | `cbore_d` / `cbore_depth` | 8.5 / 2.5 mm | M4 head counterbore. |
| Holes & Cable | `cable_d` | 30.0 mm | Central cable pass-through (0 = none). |
| Plate | `spacer_h` | 8.0 mm | Stand-off height (`adapter_100_to_75`). |
| Plate | `corner_r` | 6.0 mm | Plate corner fillet radius. |

## Why it holds (and stays watertight)

The plate is a filleted rounded slab, **filleted before any hole is cut** (a fillet
on a feature-laden solid crashes OCCT's `clean()`). The VESA squares are
**through-holes** that vent to both faces, so no trapped voids form. The stand-off
boss is a **solid** slab **unioned with overlap** onto the base — never a hollow
post — so the whole part is a single watertight body. Counterbores are open pockets
that vent to the outward face. The universal mode uses obround slots (more robust
than fans of arc-circles).

## Presets

- **Standard 75->100** — the reference flat adapter at spec dimensions.
- **Stand-off 100->75** — an 8 mm boss for recessed monitor backs.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **VESA MIS-D 75 Pattern** (`bolt_pattern`, *VESA MIS-D*) — the 75 x 75 mm
    square defined by `vesa_small`, `bolt_d`. Mates `vesa-mount`,
    `vesa-arm-extender`, `framing-hyperobject`.
  - **VESA MIS-D 100 Pattern** (`bolt_pattern`, *VESA MIS-D*) — the 100 x 100 mm
    square defined by `vesa_large`, `bolt_d`. Mates `vesa-mount`,
    `vesa-arm-extender`, `framing-hyperobject`.
- **Material awareness:** `tolerance_by_material` is declared — hole clearances
  tune per material/printer.
- **Societal benefit:** the VESA FDMI interface is the universal open standard for
  monitor mounting, but the 75 mm and 100 mm patterns rarely match between a display
  and its arm; a printed adapter reconciles them on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes and per-mode extreme parameter cases render **watertight**,
  single-body, in well under 20 s.
