# LED Strip Channel

A mounting channel and diffuser for adhesive LED strip (5050 / 2835 tape). The U-channel holds and protects the strip and gives it a surface to sit proud of; a snap-on cover clips into the channel lips to diffuse the LEDs; a corner piece turns a run through 90°. Sized by the strip width so common tapes drop straight in.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `channel` | U-Channel | CadQuery B-Rep | `main.py` |
| `diffuser_cover` | Diffuser Cover | CadQuery B-Rep | `main.py` |
| `corner` | 90° Corner | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

`strip_width` (default 10 mm for 5050) sizes the bed and cover; run length, interior depth, wall, floor and the snap `lip` are sliders. `screw_pilots` toggles countersunk floor pilots. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **LED Strip Channel** (`profile`, 5050/2835 strip) — the U cross-section sized to the tape, driven by `strip_width` / `depth` / `wall`.
  - **Cover Snap Lip** (`snap`, internal) — the inward lips the diffuser cover clips under, set by `lip` / `wall`.
- **Material awareness:** tolerance-by-material (strip/cover clearance tuned per filament).
- **Societal benefit:** Makes tidy, durable LED lighting from cheap adhesive tape — the channel protects the strip, a diffuser hides the raw diodes, and corners route cleanly — without buying proprietary aluminium extrusion.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a 20 mm-wide / 400 mm-long extreme) and render as distinct geometries.
