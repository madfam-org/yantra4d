# Stackable Tray / Sorting Bin

An open-front stacking sorting bin generated with **CadQuery** (B-Rep) — the
classic parts / hardware bin. Sized by its **interior** dimensions. An angled
open front lets you see and scoop the contents, a stacking lip nests the bin
above squarely, and an optional recessed label slot sits on the front face.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bin** | `bin` | Plain open-front stacking bin with lip and optional label slot. |
| **Bin + Dividers** | `bin_with_divider` | The same bin with one or two internal partitions. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Interior Size | `inner_w` / `inner_d` / `inner_h` | 90 / 120 / 70 mm | Usable interior X / Y / Z. |
| Open Front & Label | `front_cut` | 35 mm | Height of the standing front wall (angled opening above). |
| Open Front & Label | `label` | on | Recessed label pocket on the front face. |
| Stacking | `lip` | 4.0 mm | Raised rim that nests the bin above (0 = flat top). |
| Stacking | `lip_clear` | 0.4 mm | Per-side clearance for a printable stack fit. |
| Walls & Dividers | `wall` | 2.0 mm | Wall and floor thickness. |
| Walls & Dividers | `dividers` | 1 | Internal partitions across the width (0–2). |

## Presets

- **Small Hardware Bin** — 70×100×50, low front for screws and fasteners.
- **Sorted Bin (2 cells)** — 120×120×70 with one internal divider.
- **Deep Stacking Bin** — 100×150×140, tall front, deep stacking lip.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Stacking Lip** (`snap`, internal) — the mating geometry between stacked
    bins. `inner_w`, `inner_d`, `lip`, `lip_clear` and `wall` define a raised rim
    on top and a matching recess underneath, so any two bins printed at the same
    interior footprint and clearance nest into a square stack.
- **Material awareness:** `tolerance_by_material` is declared so the stacking
  clearance can be tuned per material/printer for a firm but separable stack.
- **Societal benefit:** on-demand, space-efficient, stackable parts storage that
  replaces bought bin systems and their packaging.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The bin is a closed solid (solid outer minus cavity, front opening and lip
  recess cut cleanly); all shipped modes and presets export **watertight**.
