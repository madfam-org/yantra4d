# TPU Chainmail Panel

A **print-in-place flexible chainmail panel** — generated with **CadQuery** (B-Rep).
The additive-manufacturing fabric that Fashion Cabinet's `tpu-panel-impreso` fabric
card describes as *cloth* and bridges to **here** for its geometry. A grid of
interlocked rings (the 4-in-1 European weave) prints in one job as separate,
already-linked solids and drapes like a textile: rigid link, flexible sheet.

This is the **soft-goods ↔ hard-goods seam made physical** — the first object that is
simultaneously a Fashion Cabinet fabric and a Yantra4D solid. One material identity,
**Bambu TPU 95A** (`materials/bambu-tpu-95a`), spans the FC fabric card and this
cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Chainmail Panel** | `panel` | The full interlocked ring grid (`rows` × `cols`), print-in-place. |
| **3×3 Swatch** | `swatch` | A small sample for a print / fit / clearance test. |
| **Single Ring** | `ring` | The unit cell, for tuning cross-section + clearance. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Weave | `rows` | 10 | Ring rows down the panel; with ring size, sets finished height. |
| Weave | `cols` | 8 | Ring columns across; the width follows. |
| Ring | `ring_id` | 9.0 mm | Ring inner diameter; larger = looser, drapier weave. |
| Ring | `wire_d` | 2.4 mm | Ring cross-section; thicker = stiffer, stronger. |
| Print Fit | `clearance` | 0.45 mm | Gap between linked rings so they print free and articulate. |

## Presets

- **Fine Drape** — 12×10, 9 mm rings, 2.4 mm wire (a supple garment panel).
- **Armor Grade** — thicker 3.4 mm wire (stiffer, protective).
- **Print Test Swatch** — a 3×3 to dial in your printer's clearance first.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewable Panel Edge** (`flange`, internal) — the finished edge a Fashion Cabinet
    garment sews to, defined by `rows`, `cols`, `ring_id`, `wire_d`.
  - **4-in-1 Link Cell** (`snap`, internal) — the interlock geometry, defined by
    `ring_id`, `wire_d`, `clearance`.

## The cross-commons material identity

Fashion Cabinet's `tpu-panel-impreso` fabric card (a `printed_textile`, weave
`interlocked-chainmail`, 100% `tpu-95a`) describes this panel's *behavior as cloth* —
drape by link geometry, no cutting, joins by printed clasps or sewn tape edges,
width bounded by the print bed. It states its solid "federates to Yantra4D"; this
cartridge is that solid. Both agree on the material `bambu-tpu-95a`, so a garment can
plan the cut/drape from the card while the printable geometry comes from here.

## Fabrication notes

Every ring is a watertight torus; rings are **not fused** — they interlink by
placement, exactly as real chainmail does, so the panel exports as a set of separate,
already-linked solids the slicer prints in place. Print flat in TPU; run the swatch
first and tune `clearance` (start 0.45 mm) so the links articulate freely but don't
slop. Even/odd rows offset by half a column and the ring tilt alternates so every
interior ring links its four diagonal neighbours.
