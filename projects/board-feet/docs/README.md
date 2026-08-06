# Cutting-Board Non-Slip Feet

Clip-on feet generated with **CadQuery** (B-Rep) that lift a cutting board off the
counter and stop it sliding. Each foot is a **C-clip** whose channel is sized to
the board thickness (`board_t`) with a textured pad underneath. Retrofit any board
you already own — no adhesive.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Edge Clip Foot** | `clip_foot` | Straight edge clip + foot pad (print 4). |
| **Corner Foot** | `corner_foot` | L-shaped clip that wraps a board corner, gripping two edges. |
| **Riser Foot** | `riser_set` | A taller riser (draining / airflow) on the same edge clip. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Board Fit | `board_t` | 18 mm | **Board thickness — the channel is sized to this.** |
| Board Fit | `clearance` | 0.3 mm | Per-side channel fit for a slide-on grip. |
| Board Fit | `grip_depth` | 14 mm | How far the lips reach onto the board faces. |
| Foot | `foot_h` | 10 mm | Lift height (clip / corner foot). |
| Foot | `riser_h` | 22 mm | Lift height (riser foot). |
| Foot | `pad_grip` | on | Anti-slip grooves on the pad base. |
| Clip | `clip_len` | 30 mm | Length of the foot along the board edge. |
| Clip | `wall` | 3.0 mm | Wall thickness of the C-clip. |

## Presets

- **Standard Board Feet** — 18 mm board, 10 mm lift, four edge clips.
- **Thick Board Corners** — 30 mm board, corner-wrapping feet.
- **Draining Risers** — 30 mm riser lift for airflow under the board.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Board Edge Clip** (`snap`, internal) — the edge-gripping channel, defined by
    `board_t`, `clearance`, `grip_depth`, `wall`. Any board whose thickness equals
    `board_t` (± clearance) is held; the same clip carries the pad or riser.
- **Material awareness:** channel `clearance` is exposed so the grip fit can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** retrofit any existing board with non-slip lift instead of
  replacing it, extending the life of boards households already own.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The C cross-section is extruded once (watertight); the lip-tip bevel is applied
  **before** the pad union so the chamfer only sees the clean lip edges (a
  post-union `>X` chamfer over the pad edges crashes the OCCT kernel). The pad is
  fused with an overlap for a clean boolean.
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
