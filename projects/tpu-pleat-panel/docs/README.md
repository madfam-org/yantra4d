# TPU Pleat Panel

A **print-in-place accordion-pleated textile panel** — generated with **CadQuery**
(B-Rep). The additive-manufacturing fabric that Fashion Cabinet's `tpu-pleat-panel`
fabric card describes as *cloth* and bridges to **here** for its geometry. A run of
alternating knife folds prints flat and concertinas like a pleated skirt panel: rigid
facet, flexible crease.

This is the **soft-goods ↔ hard-goods seam made physical** — the second object (after
`tpu-chainmail-panel`) that is simultaneously a Fashion Cabinet fabric and a Yantra4D
solid. One material identity, **Bambu TPU 95A** (`materials/bambu-tpu-95a`), spans the
FC fabric card and this cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Pleat Panel** | `panel` | The full pleated run (`pleats` folds), print-in-place. |
| **3-Pleat Swatch** | `swatch` | A small sample for a print / fold / stiffness test. |
| **Single Pleat** | `pleat` | One fold, for tuning depth + wall thickness. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pleating | `pleats` | 8 | Knife-fold count; with the pitch, sets the run length. |
| Pleating | `pleat_depth` | 12 mm | Peak-to-valley depth; deeper = more compression range. |
| Pleating | `pleat_pitch` | 16 mm | Crease-to-crease spacing along the run. |
| Panel | `panel_width` | 200 mm | Width across the pleats (the un-pleated span). |
| Print | `wall` | 1.2 mm | Facet wall; thin walls flex at the folds like a living hinge. |

## Presets

- **Fine Pleats** — 12 folds, 10 mm deep, 12 mm pitch (a supple garment panel).
- **Deep Accordion** — 24 mm deep, 20 mm pitch (large compression range).
- **Print Test Swatch** — a 3-pleat to dial in your printer's wall + fold behaviour.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewable Panel Edge** (`flange`, internal) — the finished edge a Fashion Cabinet
    garment sews to, defined by `pleats`, `pleat_pitch`, `panel_width`, `wall`.
  - **Knife-Fold Cell** (`snap`, internal) — the unit fold, defined by `pleat_depth`,
    `pleat_pitch`, `wall`.

## The cross-commons material identity

Fashion Cabinet's `tpu-pleat-panel` fabric card (a `printed_textile`, weave
`accordion-pleat`, 100% `tpu-95a`) describes this panel's *behavior as cloth* — pleat
drape by fold geometry, no separate pleating step, joins by sewn tape edges, width
bounded by the print bed. Its solid "federates to Yantra4D"; this cartridge is that
solid. Both agree on the material `bambu-tpu-95a`.

## Fabrication notes

The panel is a fused run of angled slabs following a zig-zag centre-line — **straight
line segments only** (arcs degenerate under sweep). Overlap at the creases keeps the
solid watertight; the thin printed walls act as living hinges so the panel concertinas.
Print flat in TPU; run the swatch first and thin the `wall` (start 1.2 mm) until it
folds freely without cracking.
