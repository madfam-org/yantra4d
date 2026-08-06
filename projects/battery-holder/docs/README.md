# Battery Cell Holder

Cell holders that keep a set of cells captive in a printed carrier for a battery pack, with open contact slots at each end so bus strips or spring contacts can reach the terminals. Pick the cell and the bores land on the real cell diameter, spaced on a pitch that leaves a printable wall between cells.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `holder` | Cell Holder | CadQuery B-Rep | `main.py` |
| `spacer` | Spacer Grid | CadQuery B-Rep | `main.py` |
| `series_holder` | Series Pack Holder | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

`cell` is a `select` (18650, 21700, AA, AAA) whose real outer diameter/length sizes the bores and block. Cell count, bore clearance, cradle fraction, wall, floor and contact-slot width are sliders. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Cell Array** (`grid`, 18650/21700/AA) — the row of cell cradles on the chosen cell's diameter, driven by `cell` / `count` / `clearance`.
  - **Terminal Contact Windows** (`pocket`, internal) — the end windows that let bus strips reach the cell terminals.
- **Material awareness:** tolerance-by-material (bore clearance tuned per filament).
- **Societal benefit:** Lets anyone build a safe, serviceable pack from salvaged or new cells without spot-welded proprietary trays. Correct diameters and open contact windows mean packs are repairable and cells replaceable, keeping cells out of landfill.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a 12× 21700 extreme) and render as distinct geometries.
