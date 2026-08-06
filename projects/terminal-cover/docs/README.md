# Wire Nut / Terminal Cover

Insulating covers, guards and barriers for terminals and busbars on a DIN rail. The footprint follows DIN rail (TS35, EN 60715) and DIN feed-through terminal-block dimensions, so a printed hood drops over a real block row and a finger guard shrouds a busbar.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `block_cover` | Block Cover | CadQuery B-Rep | `main.py` |
| `busbar_guard` | Busbar Comb Guard | CadQuery B-Rep | `main.py` |
| `end_barrier` | End Barrier | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`pole_count` and `pitch` set how far the cover spans a terminal-block row; height, depth, wall and the wire-slot width control the shell. All labels/tooltips are bilingual (en/es).

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| DIN rail TS35 (EN 60715) | 35.0 mm wide × 7.5 mm deep top-hat |
| DIN feed-through block pitch | 3.5–16 mm (small to medium) |
| Block height above rail | ~30–40 mm |

The hood is a solid block hollowed **from below** (an open-bottom cavity, never sealed), the comb guard is a bar with single-box slot cuts, and the end barrier has a rail notch open to the bottom face. Blanks are filleted before cutting.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Terminal Block Pocket** (`pocket`, DIN terminal) — the hood cavity spanning the block row.
  - **DIN Rail Seat** (`rail`, DIN EN 60715) — the TS35 rail notch.
- **Material awareness:** tolerance-by-material (fit tuned per filament).
- **Societal benefit:** Restores touch-safe finger protection over exposed terminals and busbars in field panels, junction boxes and hobby power builds where original covers are lost or were never fitted.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and full min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
