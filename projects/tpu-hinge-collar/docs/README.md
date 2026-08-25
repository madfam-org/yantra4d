# TPU Hinge Collar

A **print-in-place stand-or-fold collar band** — generated with **CadQuery** (B-Rep).
The additive-manufacturing trim Fashion Cabinet's `printed-hinge-collar` notion
describes and bridges to **here**. A flat collar band with a printed **living-hinge fold
line**: the upper stand and the lower sewn band are stiff, the thin slotted line between
them lets the collar stand up or fold down and hold its crease — no interfacing, no
topstitched roll line.

Part of the AM-fashion capsule. One material identity, **Bambu TPU 95A**. Official
visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Hinge Collar** | `collar` | The full band with the fold line. |
| **Fold Swatch** | `swatch` | A short sample for a print / fold test. |
| **Plain Band** | `band` | No fold line, to compare stiffness. |

## Parameters

| Parameter | Default | Notes |
| :--- | :--- | :--- |
| `collar_len` | 400 mm | Length around the neckline. |
| `stand_h` | 35 mm | Height above the fold line. |
| `band_h` | 30 mm | Sewn band below the fold line. |
| `wall` | 2.0 mm | Plate thickness. |
| `fold_slots` | 28 | Slots along the fold line; more = softer fold. |
| `slot_w` | 6 mm | Slot length along the collar. |

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Sewn Collar Edge (`flange` — `collar_len`, `band_h`, `wall`) and
  Living-Hinge Fold Cell (`snap` — `fold_slots`, `slot_w`, `wall`).

## Fabrication notes

The band is one flat plate; the fold line is a row of through-slots that leave ligaments
between them, so the plate stays one watertight solid and flexes only on that line. Print
flat in TPU; run the swatch first and add slots (or thin the wall) until it folds and
holds.
