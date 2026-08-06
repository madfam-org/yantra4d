# Shelf Bracket

A right-angle L-bracket generated with **CadQuery** (B-Rep) that supports a
shelf, **load-aware**: the plate thickness is bounded to roughly a quarter of the
shorter arm so the part can't be configured into a flimsy load path. An optional
diagonal gusset braces the corner, and screw holes sit on both arms to bolt into
the wall and up into the shelf.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Bracket** | `bracket` | One L-bracket with optional gusset and screw holes. |
| **Mirrored Pair** | `bracket_pair` | A left + right pair laid side by side on the plate. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Arms & Size | `arm_h` / `arm_v` | 80 / 80 mm | Horizontal (under-shelf) and vertical (up-wall) arm lengths. |
| Arms & Size | `width` | 30 mm | Bracket width (X). |
| Structure | `thickness` | 5.0 mm | Plate thickness — clamped to ≤ ¼ of the shorter arm and < ½ width. |
| Structure | `brace` | on | Triangular gusset across the inside corner. |
| Screw Holes | `screw_d` | 4.5 mm | Clearance diameter (≈ #8 / M4). |
| Screw Holes | `holes_per_arm` | 2 | Screw holes on each arm (0–4). |
| Screw Holes | `gap` | 10 mm | Spacing between the two brackets (pair only). |

## Presets

- **Light Shelf (60 mm)** — 60×60, 4 mm plate, gusset on.
- **Heavy-Duty Pair** — 120×100, 10 mm plate, 3 holes/arm, mirrored pair.
- **Slim (no gusset)** — 90×70, narrow, gusset off.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Right-Angle Shelf Support** (`bolt_pattern`, internal) — the mounting
    interface. `arm_h`, `arm_v`, `width`, `thickness`, `screw_d` and
    `holes_per_arm` define the two orthogonal screw-hole fields, so a shelf and
    wall drilled to the bracket's hole spacing accept any bracket built at the
    same arm/width/hole settings, and the mirrored pair shares the pattern.
- **Material awareness:** `tolerance_by_material` is declared so the screw
  clearance can be tuned per material/printer. Thickness is deliberately bounded
  as a structural guard rather than left unlimited.
- **Societal benefit:** a load-aware, printed-to-fit shelf support that puts
  safe custom-length shelving within reach without a hardware-store trip.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The bracket is a single fused solid (two plates + optional gusset, holes bored
  through); all shipped modes and presets export **watertight**.
