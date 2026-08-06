# DIN Module Carrier

Snaps a bare PCB or electronics module onto standard top-hat DIN rail (TS35, DIN EN 60715) — the backbone of control panels and consumer units. The carrier holds the board in a walled bay and grabs the two rolled rail lips from behind.

Why a compliant mechanism: printed snap clips that rely on the *material* bending fail over time from creep and fatigue. Here one hook is a rigid reference face and the opposite hook rides a cantilever **spring beam** — a folded flexure that stores energy in bending only while you snap it over the lip, then returns to shape. The working load lives in the geometry, not a permanently strained wall. `spring_thick` is the stiffness lever.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `module_carrier` | Module Carrier | CadQuery B-Rep | `main.py` |
| `terminal_block` | Terminal Block | CadQuery B-Rep | `main.py` |
| `wide_carrier` | Wide Carrier | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; `parts[]` ids match the built values so the platform renders each mode distinctly.

## Parameters

Bay width/height, PCB width/thickness, wall, base-plate thickness and the compliant `spring_thick` are sliders. The hooks always reference the 35 mm TS35 span regardless of bay width. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **DIN TS35 Rail Profile** (`rail`, DIN EN 60715) — the rail cross-section the hooks engage.
  - **Compliant Spring Hook** (`snap`, internal) — the sprung cantilever hook whose stiffness is set by `spring_thick`.
  - **PCB Retention Bay** (`pocket`, internal) — the walled bay + ribs that hold the board, driven by `bay_w` / `bay_h` / `pcb_w` / `pcb_th`.
- **Material awareness:** tolerance-by-material (snap clearance tuned per filament).
- **Societal benefit:** Puts any bare PCB onto the universal DIN rail without a proprietary carrier. The compliant hook survives creep, so the mount lasts and enclosures get repaired instead of scrapped.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and a max bay/spring extreme) and render as distinct geometries.
