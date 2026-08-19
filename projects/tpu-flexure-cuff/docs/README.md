# TPU Flexure Cuff

A **print-in-place flexible cuff band** — generated with **CadQuery** (B-Rep). The
additive-manufacturing trim that Fashion Cabinet's `printed-flexure-cuff` notion
describes and bridges to **here** for its geometry. A cylindrical band, printed thin in
TPU and perforated by a staggered lattice of through-slots (a rolled-up living hinge),
flexes open to pass over the hand and springs back to grip the wrist — a sleeve or hem
finish with **no separate elastic**.

This is the **soft-goods ↔ hard-goods seam made physical** — one of the AM-fashion
capsule that follows `tpu-chainmail-panel` and `tpu-pleat-panel`. One material identity,
**Bambu TPU 95A** (`materials/bambu-tpu-95a`), spans the FC notion and this cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Flexure Cuff** | `cuff` | The full flexure band (`cuff_circum` × `cuff_height`), print-in-place. |
| **Arc Swatch** | `swatch` | A short arc for a print / flex test. |
| **Plain Band** | `band` | An un-slotted band, to compare stiffness. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Fit | `cuff_circum` | 180 mm | Relaxed inner circumference; flexes larger to pass the hand. |
| Fit | `cuff_height` | 60 mm | Band height along the limb. |
| Print | `wall` | 2.0 mm | Band wall; thinner + more slots = more stretch. |
| Flexure | `slot_rows` | 3 | Rows of flexure slots up the band. |
| Flexure | `slot_cols` | 16 | Slots around the band per row. |
| Flexure | `slot_w` | 2.0 mm | Slot opening around the band. |

## Presets

- **Wrist Cuff** — 180 mm, 3 slot rows (a sleeve finish).
- **Ankle Cuff** — 260 mm, 80 mm tall, 4 rows (a jogger/hem finish).
- **Flex Test Swatch** — a short arc to dial in the wall + slot flex first.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewable Cuff Edge** (`flange`, internal) — the finished edge a Fashion Cabinet
    garment sews to, defined by `cuff_circum`, `cuff_height`, `wall`.
  - **Flexure Slot Cell** (`snap`, internal) — the flex geometry, defined by
    `slot_rows`, `slot_cols`, `slot_w`, `wall`.

## The cross-commons material identity

Fashion Cabinet's `printed-flexure-cuff` notion describes this cuff's *behavior as a
trim* — stretch by slot geometry, no elastic, sewn to the sleeve/hem edge, circumference
sized to the wrist/ankle. Its solid federates to Yantra4D; this cartridge is that solid.
Both agree on the material `bambu-tpu-95a`.

## Fabrication notes

The band is a hollow cylinder (outer minus inner) with vertical slots box-cut through
the wall. Each slot leaves a **land at top and bottom** so the ring is always one
watertight solid; alternate rows offset by half a slot so the ligaments stagger like a
rolled living hinge. Print upright in TPU; run the arc swatch first and thin the `wall`
or widen the slots until it flexes over the hand yet springs back.
