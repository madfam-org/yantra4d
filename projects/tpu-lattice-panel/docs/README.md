# TPU Lattice Panel

A **print-in-place flexible armor lattice** — generated with **CadQuery** (B-Rep). The
additive-manufacturing textile that Fashion Cabinet's `lattice-armor-panel` notion
describes and bridges to **here** for its geometry. A grid of rigid tiles joined by thin
flexure bridges prints flat and drapes like a scale garment: **rigid plate where you
need protection, flexible seam where you need to move.**

Part of the AM-fashion capsule (after `tpu-chainmail-panel`, `tpu-pleat-panel`,
`tpu-flexure-cuff`). One material identity, **Bambu TPU 95A** (`materials/bambu-tpu-95a`),
spans the FC notion and this cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Lattice Panel** | `panel` | The full tile lattice (`rows` × `cols`), print-in-place. |
| **3×3 Swatch** | `swatch` | A small sample for a print / drape test. |
| **2×2 Cell** | `cell` | A minimal tile-and-bridge cell, for tuning stiffness. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Grid | `rows` | 8 | Tile rows down the panel. |
| Grid | `cols` | 6 | Tile columns across. |
| Tile | `tile` | 18 mm | Tile edge length; larger = stiffer, more armored. |
| Tile | `tile_thick` | 2.5 mm | Plate thickness; thicker = more protection. |
| Flexure | `gap` | 3 mm | Gap between tiles the bridge spans; more = more drape. |
| Flexure | `bridge_w` | 5 mm | Flexure bridge width; wider = stiffer seam. |
| Flexure | `bridge_t` | 0.8 mm | Thin bridge that flexes; thinner = softer drape. |

## Presets

- **Scale Armor** — 18 mm tiles, 2.5 mm thick (protective).
- **Fine Drape** — 10 mm tiles, thin 0.6 mm bridges (supple).
- **Print Test Swatch** — a 3×3 to dial in the tile + bridge stiffness first.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewable Panel Edge** (`flange`, internal) — the finished edge a Fashion Cabinet
    garment sews to, defined by `rows`, `cols`, `tile`, `gap`.
  - **Tile-and-Bridge Cell** (`snap`, internal) — the flex geometry, defined by `tile`,
    `gap`, `bridge_w`, `bridge_t`.

## Fabrication notes

Tiles and bridges **overlap** and are returned as an Assembly (like the chainmail rings)
— the slicer prints the overlapping geometry as one connected sheet, which avoids the
O(n²) blow-up of fusing dozens of boxes. Each bridge is thinner in Z than its tiles, so
the sheet flexes only at the bridges. Print flat in TPU; run the swatch first and thin
`bridge_t` (start 0.8 mm) until the panel drapes without the tiles themselves bending.
