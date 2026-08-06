# Loom / Warp Comb

Weaving tools whose functional interface is the **dent spacing** — the pitch of
teeth/slots that hold warp threads evenly — generated with **CadQuery** (B-Rep).
Pitch is derived from **dents-per-inch**: `pitch = 25.4 / dpi`.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rigid Heddle** | `rigid_heddle` | The classic rigid-heddle reed — a frame whose vertical bars alternate a drilled **hole** (thread through) with an open **slot** (thread floats); lifting/lowering opens the weaving shed. |
| **Raddle** | `raddle` | A spreading comb — a bar with a row of upright pegs that space the warp across the loom width before beaming. |
| **Pick-up Stick** | `pickup_stick` | A flat weaving sword / pick-up comb — a tapered beater with a toothed working edge for packing weft and lifting pattern threads. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Dent Spacing | `dpi` | 8.0 | Dents per inch; `pitch = 25.4 / dpi`. |
| Dent Spacing | `width_in` | 6.0 in | Working width (capped to a printable dent count). |
| Frame / Body | `frame_h` | 60.0 mm | Rigid-heddle frame height. |
| Frame / Body | `thick` | 4.0 mm | Plate / bar thickness. |
| Dent Spacing | `hole_d` | 2.5 mm | Thread-eye diameter (auto-clamped below the bar width). |
| Frame / Body | `peg_h` | 20.0 mm | Raddle peg height. |

## Dent spacing (the standard)

A reed's job is to hold warp threads at an exact, repeatable pitch. **Dents per
inch (dpi)** is the weaver's unit; the physical tooth pitch is `25.4 / dpi` mm
(8 dpi → 3.175 mm). Rigid-heddle looms commonly run 7.5, 8, 10 and 12 dpi. The
rigid heddle alternates a **drilled eye** with an **open slot** at that pitch —
threads in the eyes stay put while threads in the slots ride up and down, which
is exactly what opens and closes the shed. The thread eye is auto-clamped below
the bar width so the frame stays one connected piece at any dpi.

## Presets

- **8-Dent Rigid Heddle** — a 6-inch, 8-dpi reed.
- **Warp Raddle** — a peg raddle for spreading the warp.
- **Weaving Sword** — a toothed pick-up beater.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Dent Spacing Teeth** (`profile`, *internal*) — the tooth /
  slot / eye pitch, defined by `dpi`, `width_in`, `hole_d`. Reeds, raddles and
  swords built at the same dpi share one sett.
- **Material awareness:** none declared — spacing is geometric, not material
  dependent.
- **Societal benefit:** reeds are expensive per-width purchases; deriving pitch
  from dpi lets a weaver print a reed at any sett and width, making a loom usable
  without a drawer of bought reeds.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The heddle is **one frame solid** (picture-frame with mullions) — holes are
  vented through-holes, slots are exterior gaps (no cavities); the thread eye is
  clamped below the bar width so the frame never severs. Raddle pegs are **solid**
  cylinders; the pick-up blade taper is a **loft** (no fragile face chamfer). Dent
  counts are capped for render speed. All modes render **watertight**,
  single-body.
