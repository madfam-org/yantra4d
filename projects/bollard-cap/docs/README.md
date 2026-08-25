# Bollard Cap

Caps that close the open top of a steel pipe bollard, sized to the pipe the bollard is actually made from.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

An uncapped bollard is a slow structural failure nobody budgets for. It collects rain, holds it against the inside wall where no paint reaches, and rusts outward from the bore until the post has to be replaced rather than repainted; in freezing climates the trapped water splits the pipe outright. Replacement caps are proprietary per-manufacturer parts that a small municipality or a property owner often cannot source at all for an older bollard, so the top simply stays open.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `dome_cap` | Domed Cap | CadQuery B-Rep | `main.py` |
| `flat_cap` | Flat Cap | CadQuery B-Rep | `main.py` |
| `reflect_cap` | Reflective-Band Cap | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`pipe` selects the bollard's steel pipe size and `clearance` sets the slip fit over it — open it up for a painted or rusted post. `wall` and `skirt` size the cap body; a longer skirt shadows the joint better. `dome_rise` shapes the domed variant. `band_depth` and `band_width` set the retroreflective tape recess, and `drain_count` / `drain_w` cut slots so any water that does get in escapes again. All labels and tooltips are bilingual (en/es).

## Reuses the commons pipe-OD series

The skirt bore is **not** a new standard. It lands on NPS schedule 40 steel pipe outside diameters — the same pipe-OD-series convention the published `pipe-clip` and `pipe-fitting` families already use, extended to the structural sizes bollards are made from rather than the plumbing sizes. One diameter convention across the commons means a bollard measured for a cap is measured in the same terms as a pipe measured for a clip.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| NPS 3 sch 40 OD | 88.90 mm (3.500 in) |
| NPS 4 sch 40 OD | 114.30 mm (4.500 in) |
| NPS 5 sch 40 OD | 141.30 mm (5.563 in) |
| NPS 6 sch 40 OD | 168.28 mm (6.625 in) |
| NPS 8 sch 40 OD | 219.08 mm (8.625 in) |
| Skirt bore radius | pipe OD/2 + `clearance` |
| Band recess depth | `band_depth`, capped at `wall`/2 |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Steel Pipe OD Slip Fit** (`socket`, NPS schedule 40 OD) — compatible with `pipe-clip`, `pipe-fitting`, `sign-post-bracket`.
  - **Retroreflective Tape Recess** (`profile`, internal) — a recessed band so tape sits below the surface and is not scuffed off.
- **Material awareness:** recycled-material toggle, tolerance-by-material (slip fit tuned per filament).
- **Societal benefit:** closes the water path that rusts bollards from the inside, using a part that is otherwise unobtainable for older posts.
- **License:** CERN-OHL-W-2.0

## Printing and material notes

Print the flat caps upside down (open end up) so the skirt needs no support and the top face is the smooth first layer. The domed cap prints dome-up with light support under the shoulder, or dome-down on a raft if surface finish on top matters more than the seat.

These live outdoors permanently: **ASA** is the right default, with **ABS** or pigmented **PETG** acceptable. Do not use PLA — it embrittles in UV and creeps in summer sun, and a cap that cracks is worse than no cap because it holds water against the pipe rather than shedding it. Black or a saturated pigment resists UV far better than natural filament.

Measure the actual pipe before printing rather than trusting the nominal size: an old bollard may be heavily painted, galvanised, or a metric tube that is close to but not exactly an NPS size. Start at `clearance` 0.8 mm and open it up if the cap binds.

This is a weather cap. It is not a structural or impact component, carries no load, and does not change the bollard's protective rating.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider plus all five pipe options — 54/54 cases, each `is_watertight == True` with `body_count == 1`.

Derived dimensions are clamped in `main.py` rather than trusted from the UI. The domed cap's revolve profile deliberately ends on a **small flat apex** instead of running to a point on the rotation axis: a profile that touches the axis at a single point revolves into a pole singularity, and the mesh comes back as two shells that fail watertight — this was caught during authoring and cost a few tenths of a millimetre of plateau to fix. The band recess is capped at half the wall so it can never break through into the bore, and drain-slot width is auto-narrowed to `2·pi·bore_r / (count × 2.2)` so a wide slot at a high count can never sever the skirt into loose arcs.
