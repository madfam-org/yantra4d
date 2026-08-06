# Dev-Board Tray

A mounting tray that carries a microcontroller / SBC dev board on printed standoffs placed on the board's real mounting-hole pattern. Pick the board and the standoffs land on the correct hole coordinates so it bolts (or press-fits) down; then mount the plate to a wall, bolt it at the corners, or hang it on DIN rail.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `tray` | Bench Tray | CadQuery B-Rep | `main.py` |
| `din_tray` | DIN-Rail Tray | CadQuery B-Rep | `main.py` |
| `wall_tray` | Wall Tray | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

`board` is a `select` (Arduino Uno/Leonardo, Mega/Due, Nano, ESP32-DevKitC, Raspberry Pi Pico) whose published hole pattern places the standoffs. Standoff height/diameter, plate thickness and plate border are sliders; `mount_bore` sets the corner clearance bore. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Dev-Board Holes** (`bolt_pattern`, Arduino form factors) — standoffs on the selected board's real mounting-hole coordinates, driven by `board` / `boss_d`.
  - **DIN TS35 Foot** (`rail`, DIN EN 60715) — the clip foot on the `din_tray` underside.
  - **Keyhole Wall Mount** (`socket`, internal) — the two hang-on-screw slots on the `wall_tray`.
- **Material awareness:** tolerance-by-material (self-tapping bore tuned per filament).
- **Societal benefit:** Turns a loose dev board into a mounted, serviceable part that fits its exact hole pattern and mounts three ways, so makers build tidy, repeatable installs and reuse boards instead of gluing them down.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a Mega/max-standoff extreme) and render as distinct geometries.
