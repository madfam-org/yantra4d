# TPU Scale Mail

A **print-in-place flexible scale-mail panel** — generated with **CadQuery** (B-Rep).
The additive-manufacturing textile that Fashion Cabinet's `articulated-scale-mail`
notion describes and bridges to **here** for its geometry. Rows of overlapping scales,
each tied to a thin backing by a narrow flexure neck, print flat and articulate like a
dragon-scale garment: **rigid scale, flexible neck.**

Part of the AM-fashion capsule (with `tpu-chainmail-panel`, the pleat / flexure /
lattice objects). One material identity, **Bambu TPU 95A** (`materials/bambu-tpu-95a`),
spans the FC notion and this cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Scale Panel** | `panel` | The full scale field (`rows` × `cols`), print-in-place. |
| **3×3 Swatch** | `swatch` | A small sample for a print / articulation test. |
| **Single Scale** | `scale` | One scale + neck, for tuning the shape. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Field | `rows` | 7 | Scale rows down the panel. |
| Field | `cols` | 6 | Scale columns across. |
| Field | `overlap` | 0.45 | Fraction each row overlaps the one below; more = tighter coverage. |
| Scale | `scale_w` | 20 mm | Scale width across. |
| Scale | `scale_h` | 26 mm | Scale height along the drop. |
| Scale | `scale_t` | 2.0 mm | Scale thickness; thicker = more protection. |
| Flexure | `neck_w` | 5 mm | Flexure neck width; narrower = each scale lifts more freely. |
| Flexure | `back_t` | 0.8 mm | The thin sheet the scales anchor to; thinner = more drape. |

## Presets

- **Dragon Scale** — 20 mm scales, 0.45 overlap (classic scalework).
- **Tight Coverage** — 0.6 overlap (closer protection).
- **Print Test Swatch** — a 3×3 to dial in the scale + neck articulation first.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewable Panel Edge** (`flange`, internal) — the finished edge a Fashion Cabinet
    garment sews to, defined by `rows`, `cols`, `scale_w`, `scale_h`, `overlap`.
  - **Scale-and-Neck Cell** (`snap`, internal) — the flex geometry, defined by
    `scale_w`, `scale_h`, `neck_w`, `back_t`.

## Fabrication notes

Each scale is a box with a chamfered leading edge; scales overlap the row below (offset
alternate rows by half a scale) and are tied to a thin backing plate by a narrow neck.
Scales, necks, and backing **overlap** and are returned as an Assembly — the print fuses
the overlaps into one articulating sheet, avoiding the O(n²) blow-up of fusing every
scale. Print flat in TPU; run the swatch first and thin `neck_w` / `back_t` until each
scale lifts freely while the sheet drapes.
