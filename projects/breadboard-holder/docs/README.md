# Breadboard Holder

A base that holds a solderless breadboard (or perfboard) flat and captive on the bench so it stops sliding while you wire a circuit. A recessed pocket sized to the standard breadboard footprint receives the board, retaining lips hold it down, and corner ears bolt it to a project base. Variants add flanking power-rail channels for the clip-off DC rails, or an angled easel that tilts the board toward you.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `base_tray` | Base Tray | CadQuery B-Rep | `main.py` |
| `rail_base` | Tray + Power Rails | CadQuery B-Rep | `main.py` |
| `angled_holder` | Angled Easel | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the values the code builds, so the platform renders each mode distinctly.

## Parameters

Board footprint is chosen from a `select` (`bb_size`: 830-point 165×55, 400-point 83×55, mini 170-pt 46×35). Pocket clearance, wall, floor, retaining-lip height and board thickness are sliders. `screw_ears` toggles corner bolt-down tabs (bore set by `ear_bore`). `tilt_deg` sets the easel angle. All labels and tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Breadboard Footprint** (`grid`, 830-pt breadboard) — the pocket sized to the chosen board, driven by `bb_size` / `clearance` / `board_th`.
  - **Power Rail Channel** (`rail`, internal) — the flanking troughs that seat the clip-off DC power rails.
  - **Corner Mounting Ears** (`bolt_pattern`, internal) — the corner screw tabs that bolt the tray to a base.
- **Material awareness:** tolerance-by-material (pocket clearance can be tuned per filament).
- **Societal benefit:** Keeps a breadboard and its power rails still so learners build reliable circuits on any surface — a few grams of filament removes a real friction from learning electronics.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and an extreme min/max preset) and render as distinct geometries.
