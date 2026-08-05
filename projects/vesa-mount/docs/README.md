# VESA Mount Adapter Plate

A parametric **VESA FDMI** mounting plate generated with **CadQuery** (B-Rep) —
the canonical monitor / TV / mount interoperability object. It produces a flat
plate carrying a standard VESA square bolt pattern, either as a single-pattern
mounting plate or as an **adapter** that bridges two different VESA squares so a
display of one pattern size bolts onto a mount of another.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plate** | `plate` | One VESA pattern (screw-clearance holes) plus optional corner holes — a display- or wall-side plate, spacer, or riser. |
| **Adapter** | `adapter` | A source VESA square (monitor side) **and** a differently sized destination VESA square (mount side), both drilled as clearance holes through one plate. |

The studio dispatches the active part via `target_part` (`plate` / `adapter`);
the same choice is also exposed as the `mode` parameter so the script works when
driven purely by parameter values.

## VESA standards

| `vesa_size` | Spacing (mm) | Screw | Clearance hole | Standard |
| :--- | :--- | :--- | :--- | :--- |
| `75` | 75 × 75 | M4 | 4.5 mm | VESA MIS-D |
| `100` | 100 × 100 | M4 | 4.5 mm | VESA MIS-D/E |
| `200` | 200 × 200 | M6 | 6.5 mm | VESA MIS-F |
| `200x100` | 200 × 100 | M6 | 6.5 mm | VESA MIS-F |

In **Adapter** mode the plate footprint automatically grows to clear the larger
of the source and destination squares (plus the plate margin on every side).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| VESA Pattern | `mode` | `plate` | `plate` or `adapter`. |
| VESA Pattern | `vesa_size` | `100` | Source / plate bolt pattern. |
| VESA Pattern | `dest_vesa_size` | `200` | Destination pattern (Adapter mode only). |
| Plate | `plate_thick` | 4.0 mm | Overall plate thickness. |
| Plate | `plate_margin` | 12.0 mm | Material beyond the outermost bolt square, per side. |
| Plate | `corner_r` | 6.0 mm | Outer corner rounding (0 = sharp). |
| Holes & Recesses | `countersink` | off | Counterbore a flush pocket around each hole. |
| Holes & Recesses | `cs_diameter` / `cs_depth` | 9.0 / 2.5 mm | Recess pocket size (depth auto-clamped below thickness). |
| Holes & Recesses | `extra_holes` | off | Four generic corner mounting holes (Plate mode). |
| Holes & Recesses | `extra_hole_dia` | 5.0 mm | Corner hole diameter. |
| Center Cutout | `center_hole` | off | Cable pass-through / lightening hole. |
| Center Cutout | `center_hole_dia` | 40.0 mm | Auto-clamped to keep a ≥6 mm web to the nearest bolt. |

## Presets

- **Monitor Plate 100×100** — a plain 100×100 M4 plate.
- **Adapter 75 → 100** — small-monitor 75×75 studs to a 100×100 mount, counterbored.
- **TV Adapter 200×100 → 100** — 200×100 M6 TV pattern down to a 100×100 mount, with a 60 mm cable cutout.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **VESA FDMI (source)** (`bolt_pattern`, VESA MIS-D/E/F (FDMI)) — the plate /
    monitor-side square, defined by `vesa_size`, `plate_thick`, and the
    counterbore params. Any plate at the same `vesa_size` mates with the same
    display and screws.
  - **VESA FDMI (destination)** (`bolt_pattern`, VESA MIS-D/E/F (FDMI)) — the
    mount-side square in Adapter mode, defined by `dest_vesa_size` and the same
    thickness / recess params.
  - **Center Cable / Lightening Cutout** (`socket`, internal) — `center_hole`,
    `center_hole_dia`.
- **Material awareness:** clearance-hole diameters follow the metric screw for
  each standard (M4 → 4.5 mm, M6 → 6.5 mm) so the fit tunes per material/printer;
  `tolerance_by_material` is declared.
- **Societal benefit:** VESA FDMI is the universal display-mount interface; this
  adapter lets any monitor or TV bolt to any mount regardless of pattern size,
  keeping working hardware in service and diverting proprietary brackets from
  landfill.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Holes are cut with bores that overshoot both faces, so every shipped preset and
  default renders **watertight**.
