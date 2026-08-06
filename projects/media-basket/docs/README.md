# Filter Media / Bio-Ball Basket

A perforated basket that holds aquarium biological media, generated with
**CadQuery** (B-Rep): bio-balls, ceramic rings or foam sit in a sump or
hang-on-back filter while water flows through and the media stays put. Build the
basket, a snap grate lid, or a printable bio-media wheel. Complements the
`aquarium-fitting` cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in **aquarium-safe filament** (uncoloured PETG is a common choice) and
> rinse before use.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Media Basket** | `media_basket` | A rounded rectangular tub on feet, with a perforated floor and perforated walls, open top. |
| **Grate Lid** | `basket_lid` | A perforated grate lid with a locating skirt that caps the basket and keeps floating media submerged. |
| **Bio-Media Wheel** | `bio_media` | A printable high-surface-area bio-media wheel — a short cylinder pierced by axial and radial flow holes. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Basket Box | `length` | 90.0 mm | Footprint along X — size to your filter chamber. |
| Basket Box | `width` | 70.0 mm | Footprint along Y. |
| Basket Box | `height` | 60.0 mm | Basket wall height. |
| Basket Box | `wall` | 2.4 mm | Wall and floor thickness. |
| Flow | `hole_dia` | 5.0 mm | Perforation diameter (~4 mm retains small ceramic media; 5–8 mm suits large bio-balls). |
| Flow | `hole_pitch` | 10.0 mm | Center-to-center spacing of the perforation grid. |
| Bio-Media | `media_dia` | 32.0 mm | Bio-media wheel diameter (bio-balls run 16 / 25 / 38 mm). |

## Presets

- **Sump Media Tray** — 120×90×70, 5 mm holes.
- **Fine-Media Basket (4 mm)** — 4 mm holes for ceramic media.
- **Bio-Media Wheel (32 mm)**.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Media Flow Grid** (`grid`, internal) — the perforation grid, defined by
    `hole_dia`, `hole_pitch`, `wall`. Choose the hole size for the media you run
    (smaller than the smallest bead) and the same grid perforates any wall.
- **Material awareness:** `tolerance_by_material` is declared.
- **Societal benefit:** extends the life of aquarium equipment when a proprietary
  media basket is discontinued, and lets a fishkeeper tune biological filtration
  from printed parts instead of a whole new filter.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy (the mesh-basket rule): the basket is a solid rounded box
  shell hollowed into an open-top tub (a closed 2-manifold), then a grid of
  round holes is bored fully through each wall and the floor (open both faces).
  Feet are solid and overlap up into the floor; the lid is a solid plate with
  through-holes; the bio-media wheel is a solid cylinder with through-holes. No
  hollow bosses, no trapped voids.
- All shipped presets and defaults render **watertight**, single-body.
