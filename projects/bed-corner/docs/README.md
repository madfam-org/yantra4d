# Raised-Bed Corner Bracket

Joins dimensional lumber into a raised garden bed or planter box with **no metal
brackets and no mitered cuts**. Generated with **CadQuery** (B-Rep). Each arm is a
three-sided channel — the **Board Slot** — that a board end slides into; screws
through the pilot holes lock it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **90° Corner** | `corner_90` | Two board channels meeting at a right angle over a solid corner post. |
| **Tall / Stackable Corner** | `corner_tall` | Same corner with an optional spigot + socket so a second course stacks. |
| **Tee Join** | `tee_join` | A straight through-run channel with a third channel branching at 90°. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Board Size | `board_t` | 38 mm | Board thickness (≈ 1.5"). |
| Board Size | `board_w` | 140 mm | Board width = bracket height (≈ 6"). |
| Bracket | `slot_depth` | 60 mm | How far each board end slides in. |
| Bracket | `wall` | 6.0 mm | Channel wall thickness. |
| Bracket | `clearance` | 0.6 mm | Per-side board slack. |
| Bracket | `corner_r` | 5.0 mm | Outer edge rounding. |
| Fastening | `screw_dia` | 4.5 mm | Pilot-hole diameter. |
| Fastening | `stack_lug` | on | Stacking spigot/socket (tall corner). |

## Presets

- **2×6 Bed Corner** — the classic 38×140 raised-bed corner.
- **Deep Bed (stackable)** — 2×8 board with stacking lugs for a two-course bed.
- **Long-Side Tee** — ties a cross board into the middle of a long side.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Board Slot** (`profile`, internal) — the board pocket cross-section defined
    by `board_t`, `board_w`, `slot_depth`, `clearance`, `wall`. Every mode presents
    the same slot profile, so corners, tall corners, and tees all accept the same
    board stock and interchange around one bed.
- **Material awareness:** `clearance` is exposed so the slot fit adapts to real,
  slightly-oversized lumber and to print shrinkage; `tolerance_by_material` is
  declared.
- **Societal benefit:** raised beds bring food growing within reach for renters
  and people who cannot bend to ground level; a screwless, sawless corner lets
  anyone build one from a board and a printer.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. Outer fillets are
  wrapped in try/except so extreme inputs still build watertight.
- All shipped presets and every mode render **watertight**.
