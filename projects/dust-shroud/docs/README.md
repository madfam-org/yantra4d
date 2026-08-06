# Fan Dust Shroud

A snap-on dust filter frame for a PC / equipment fan. It clips a mesh or foam filter over the fan intake on the standard fan screw square, keeping dust out of enclosures and 3D-printer electronics bays. Pick the fan size and the frame lands on the correct corner-hole spacing; variants add an integral printed grille (no separate mesh) or corner magnet pockets for tool-free removal. Complements the fan adapter cartridge.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `filter_frame` | Filter Frame | CadQuery B-Rep | `main.py` |
| `grille_filter` | Grille Filter | CadQuery B-Rep | `main.py` |
| `magnetic_frame` | Magnetic Frame | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

`fan_size` is a `select` (40 / 60 / 80 / 120 / 140 mm) whose published screw square, bore and screw diameter size the frame. Thickness, rim, snap-skirt depth are common; grille ring/spoke counts and bar width drive the printed grille; `magnet_d` sets the corner magnet pockets. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Fan Pattern** (`bolt_pattern`, PC fan 40-140mm) — the frame + screw square on the chosen fan size, driven by `fan_size` / `thickness`.
  - **Printed Grille** (`grid`, internal) — the integral rings + spokes filling the bore, set by `ring_count` / `spoke_count` / `bar_w`.
  - **Bore Locating Skirt** (`snap`, internal) — the skirt that tucks into the fan bore to snap the frame on, set by `snap_depth`.
- **Material awareness:** tolerance-by-material (skirt/magnet-pocket fit tuned per filament).
- **Societal benefit:** Keeps dust out of the machines that overheat when clogged — PCs, 3D printers, amplifiers — on the universal fan screw square. A washable printed filter frame replaces disposable filters and extends equipment life.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a 40 mm max-grille extreme) and render as distinct geometries.
