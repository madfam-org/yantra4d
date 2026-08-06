# Pi HAT Case

A case sized around a Raspberry Pi plus its HAT / screen stack. The base carries the Pi on standoffs at the official 58 × 49 mm hole pattern; a raised lid clears a HAT sitting on the GPIO header; a bezel frames a screen mounted on top. Stack height sets how much room the lid leaves for the boards above the Pi. Complements the SBC case cartridge.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `base` | Base | CadQuery B-Rep | `main.py` |
| `hat_lid` | HAT Lid | CadQuery B-Rep | `main.py` |
| `screen_bezel` | Screen Bezel | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

`stack` sets the clearance the lid/bezel leaves above the Pi for a HAT or screen. Pi standoff height/diameter (base), wall, floor, corner radius and the screen window width/height (bezel) are sliders. The Pi standoffs are fixed on the official 58 × 49 mm HAT hole pattern. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Pi HAT Stack** (`bolt_pattern`, RPi HAT) — Pi standoffs on the 58 × 49 mm pattern with the lid sized to the stack, driven by `stack` / `standoff_h` / `boss_d`.
  - **Screen Window** (`pocket`, internal) — the bezel viewing window, set by `screen_w` / `screen_h`.
- **Material awareness:** tolerance-by-material (self-tapping standoff bore tuned per filament).
- **Societal benefit:** Encloses a Pi with whatever it is actually wearing — a HAT or a screen — on the exact official hole pattern, with a lid sized to the stack. A protected, mountable Pi lasts longer and becomes a finished appliance instead of a bare board.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a 60 mm-stack extreme) and render as distinct geometries.
