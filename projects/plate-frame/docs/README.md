# License Plate Frame

A parametric **license-plate frame** and trim fillers generated with **CadQuery**
(B-Rep), for the two dominant plate formats: **US** (12 × 6 in) and **EU**
(520 × 110 mm).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Frame** | `frame` | A full border frame with a recessed window and a retaining lip over the plate edge. |
| **Slim Frame** | `tag_frame_slim` | The same frame with a minimal low-profile border. |
| **Panel Filler** | `panel_filler` | A blank panel that plugs an oversized factory recess so a plate sits flush. |

The studio dispatches the active part via `target_part`; each mode carries the
same standard mounting-slot pattern.

## Plate standards

| `plate` | Size | Bolt pattern | Slot |
| :--- | :--- | :--- | :--- |
| `US` | 304.8 × 152.4 mm (12 × 6 in) | 4 slots — 177.8 mm horizontal, ±47.6 mm vertical | 8 mm |
| `EU` | 520 × 110 mm | 2 slots — 200 mm horizontal, on centre | 7 mm |

Mounting holes are **vertical slots** (`slot_len` travel) so the frame slides on
the studs for alignment; the bores overshoot both faces for a clean cut.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Plate Format | `plate` | `US` | US or EU plate. |
| Frame | `frame_thick` | 5.0 mm | Overall thickness. |
| Frame | `border` | 14.0 mm | Border beyond the plate (full frame). |
| Frame | `slim_border` | 7.0 mm | Border for the slim frame. |
| Frame | `lip` | 2.5 mm | Front lip overlapping the plate edge. |
| Frame | `corner_r` | 6.0 mm | Outer corner rounding. |
| Mounting | `slot_len` | 10.0 mm | Vertical slack in the mounting slots. |
| Mounting | `filler_inset` | 0.0 mm | Shrink the filler panel per side (Filler mode). |

## Presets

- **US Standard Frame** — a 14 mm-border US frame.
- **EU Slim Frame** — a 6 mm-border low-profile EU frame.
- **US Filler Panel** — a blank US filler, inset 1 mm per side.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Plate Bolt Pattern** (`bolt_pattern`, ISO/US plate) — the standard US
    4-slot / EU 2-slot mounting pattern selected by `plate`, with `slot_len`
    travel. Every mode carries it, so any frame bolts to the same studs.
  - **Plate Retaining Window** (`pocket`, internal) — the recessed window and
    lip that capture the plate, defined by `plate`, `border` / `slim_border`,
    and `lip`.
- **Material awareness:** slot and window clearances tune the fit per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** license plates share two global formats and a handful of
  bolt patterns; a printable frame or filler adapts any plate to any recess and
  covers dealer branding, so a cracked factory frame is a five-gram reprint, not
  a dealership part.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The window and back-relief are cut with overshooting boxes and the mount holes
  use `slot2D` extrusions, so every shipped preset renders **watertight**.
