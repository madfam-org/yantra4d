# Busbar / DIN Bus Support

Insulated supports and spacers for rectangular copper busbars in panels. The bar slot lands on standard flat-bar cross-sections and the base seats on a DIN rail (TS35, EN 60715) or bolts flat to the backplate.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `bar_support` | Bar Support | CadQuery B-Rep | `main.py` |
| `bar_clamp` | Captured Clamp | CadQuery B-Rep | `main.py` |
| `spreader` | Phase Spreader | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`bar_size` is a `select` whose real cross-section sizes the slot; slot clearance, centerline height, insulator wall, base width and fixing-screw diameter are sliders, plus parallel-bar count and phase pitch (spreader mode). All labels/tooltips are bilingual (en/es).

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| Bar cross-sections (W × T) | 12×2, 15×3, 20×5, 25×5, 30×5, 30×10 mm |
| DIN rail TS35 (EN 60715) | 35.0 mm wide × 7.5 mm deep top-hat |

The bar slot is a single box cut from a solid, filleted blank; stacked bodies overlap (never tangent). The slot floor is clamped so a wall-thick bridge always stays under the bar — a short standoff with a tall bar can never sever the block in two.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Busbar Profile Slot** (`rail`, DIN EN 60715) — the slot sized to the bar cross-section at the correct centerline height.
  - **Backplate Screw** (`bolt_pattern`, internal) — the fixing screw bore.
- **Material awareness:** tolerance-by-material (slot fit tuned per filament).
- **Societal benefit:** Lets off-grid and workshop builders route copper busbar safely with correct clearances and phase spacing, instead of resting live bars on improvised blocks. Captured clamps add mechanical retention; spreaders organize multi-phase layouts.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and full min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
