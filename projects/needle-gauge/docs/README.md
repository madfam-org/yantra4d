# Crochet / Knitting Needle Gauge

A **needle and hook sizing gauge**, generated with **CadQuery** (B-Rep): a plate
of precisely-sized through-holes. Push a needle through; the smallest snug hole
is its size. The **holes are the interface** — each diameter is a real
US/metric knitting size.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ruler Gauge** | `ruler_gauge` | A flat stick with an in-line row of graduated holes and a small hang hole — the classic needle gauge. |
| **Disc Gauge** | `disc_gauge` | A round disc with the holes arranged radially like a clock, compact for a project bag, with a centre hang hole. |
| **Gauge Swatch** | `gauge_swatch` | A plate with a large square window you lay over knitting to count stitches, plus a column of needle holes on one edge. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Size Range | `size_min` | 2.0 mm | Smallest hole (2.0 mm = US0). |
| Size Range | `size_max` | 10.0 mm | Largest hole (12.0 mm = US17). |
| Size Range | `clear` | 0.15 mm | Per-side oversize so holes measure true after printing. |
| Plate | `plate_th` | 3.0 mm | Gauge plate thickness. |
| Plate | `window` | 25.0 mm | Square gauge-window side (swatch). |

## The size ladder (why it's a standard)

The holes are drawn from the real metric needle ladder — **2.0, 2.25, 2.75, 3.0,
3.25, 3.5, 3.75, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 8.0, 9.0, 10.0, 12.0 mm** — which
maps directly to US knitting sizes (5.0 mm = US8, 6.5 mm = US10.5, 12.0 mm =
US17) and to crochet-hook metric sizes. Because metric is defined by actual
diameter, a gauge built to this ladder sizes any needle to the same standard
anywhere. `clear` is a per-side oversize so a hole prints to true diameter on a
given printer.

## Presets

- **Full-Range Ruler (2-12 mm)** — the complete US0-US17 stick.
- **Project-Bag Disc** — a compact round gauge.
- **Stitch-Gauge Swatch** — a window counter with a few needle holes.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Needle Size Holes** (`profile`, *US / metric knitting
  needle sizes 2.0-12.0 mm*) — the graduated hole set, defined by `size_min`,
  `size_max`, `clear`. Any gauge built to this ladder measures to one standard.
- **Material awareness:** `tolerance_by_material` is declared — `clear` is exposed
  so holes measure true per material/printer.
- **Societal benefit:** needles lose their printed size and US/metric labels are
  inconsistent; a gauge whose holes are the real metric ladder restores any
  orphan needle's size to a shared standard.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Every hole is a **through-hole** (open both faces, vented); no embossed text
  (thin glyphs crack meshes) — holes are graduated in size, self-documenting.
  Blanks are fillet-cleaned before holes are cut. All modes render **watertight**
  and single-body.
