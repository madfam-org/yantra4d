# Cabinet Organizer Bin

A fits-anything cabinet and drawer organizer bin generated with **CadQuery**
(B-Rep), sized by its **interior** dimensions so the printed cavity matches the
space it must fill. Plain, angled-front, or divided — with a stacking lip so
bins nest together.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bin** | `bin` | Plain open-top bin with a stacking lip; optional front pull handle. |
| **Angled-Front Bin** | `angled_bin` | Front wall sloped down for scoop-in access (pantry pull bin). |
| **Divided Bin** | `divided_bin` | The bin plus an interior partition grid (X and/or Y). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Interior Size | `inner_w` / `inner_d` / `inner_h` | 90 / 140 / 80 mm | Usable interior X / Y / Z. |
| Walls & Style | `wall` | 2.0 mm | Wall and floor thickness. |
| Walls & Style | `corner_r` | 3.0 mm | Outer corner rounding (0 = sharp). |
| Walls & Style | `style` | open | `open` or `handled` (front pull tab). |
| Stacking & Front | `lip` / `lip_clear` | 4.0 / 0.4 mm | Stacking lip height and per-side fit. |
| Stacking & Front | `front_cut` | 40.0 mm | Open-front sill height (angled bin). |
| Dividers | `div_x` / `div_y` / `div_thick` | 1 / 0 / 1.6 | Partition counts and thickness. |

## Presets

- **Spice Drawer Bin** — 60×120×50, tall lip for stacking in a drawer.
- **Pantry Scoop Bin** — 120×180×110 angled-front for open shelving.
- **Junk-Drawer Sorter (3×1)** — 150×100×45 with two X dividers.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Adjustable Bin** (`grid`, internal) — the parametric bin envelope and
    stacking lip, defined by `inner_w`, `inner_d`, `inner_h`, `wall`, `lip`,
    `lip_clear`. Any bin printed at the same footprint + lip stacks squarely.
  - **Interior Divider Grid** (`grid`, internal) — `div_x`, `div_y`, `div_thick`.
- **Material awareness:** the stacking clearance (`lip_clear`) is exposed so the
  nest fit can be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** on-demand cabinet/drawer organization sized to the exact
  space, cutting the waste of ill-fitting store bins.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**; the `shell()` +
  `divider_grid()` body idiom is shared across the kitchen batch.
