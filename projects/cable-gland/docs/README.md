# Cable Gland / Strain Nut

Threaded cable glands that seal a cable where it passes through an enclosure wall and take the strain off the terminations inside. The panel thread is a real PG (DIN 40430) or metric-ISO gland thread, so the printed body screws into off-the-shelf knockouts and lock nuts.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `gland_body` | Gland Body | CadQuery B-Rep | `main.py` |
| `lock_nut` | Lock / Strain Nut | CadQuery B-Rep | `main.py` |
| `sealing_reducer` | Sealing Reducer | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`gland_size` is a `select` (PG7-PG21, M12-M25) whose real thread major diameter and 1.5 mm pitch drive the panel thread; `cable_dia` is clamped to the size's standard sealing range. Thread clearance, wall, engagement turns and hex wrench flats round it out. All labels/tooltips are bilingual (en/es); see `project.json` → `parameters`.

## Standards encoded

| Size | Thread major Ø (mm) | Cable range (mm) |
| :--- | :--- | :--- |
| PG7 | 12.5 | 3.0–6.5 |
| PG9 | 15.2 | 4.0–8.0 |
| PG11 | 18.6 | 5.0–10.0 |
| PG13.5 | 20.4 | 6.0–12.0 |
| PG16 | 22.5 | 10.0–14.0 |
| PG21 | 28.3 | 13.0–18.0 |
| M12–M25 | 12.0–25.0 | (ISO metric, 1.5 mm pitch) |

Threads are swept from a trapezoidal profile along a genuine `makeHelix` path, with the rib root pushed into the surrounding material so every union is volumetric (watertight), never a tangent kiss. Engagement is capped at 4 turns for render speed.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **PG / Metric Gland Thread** (`thread`, PG7-PG21 / M12-M25) — the panel thread that mates enclosure knockouts and lock nuts.
  - **Sealed Cable Bore** (`socket`, internal) — the clearance-cored cable opening.
- **Material awareness:** tolerance-by-material (thread clearance tuned per filament).
- **Societal benefit:** Puts a standards-matched strain relief on any enclosure penetration for a few grams of filament, giving field-built control boxes, off-grid battery boxes and irrigation cabinets a sealed, snag-free cable entry.
- **License:** CERN-OHL-W-2.0

## Verification

All three modes are verified watertight through the render sandbox (default, each mode, and PG21 min/max slider extremes) and render as distinct geometries (`body_count == 1`, no negative-volume bodies).
