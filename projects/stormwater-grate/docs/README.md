# Stormwater Grate

The missing surface element of the commons drainage chain.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

The commons already drains water: `downspout-adapter` takes roof water out of a rectangular spout into a round outlet, and `drain-trap` seals the run against sewer gas. Nothing covered the point where water actually **enters** the system.

A grate is the one drainage part that is simultaneously a hydraulic aperture, a pedestrian surface and a debris filter — and it is the part that is missing, cracked or stolen most often. Cast grates are taken for scrap and cracked ones sit for months awaiting a municipal order, leaving a hole that is a flood risk, a trip hazard and something a child or a dog can fall into, all at once.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `slot_grate` | Slot Grate | CadQuery B-Rep | `main.py` |
| `round_grate` | Round Drop-In Grate | CadQuery B-Rep | `main.py` |
| `leaf_dome` | Leaf Guard Dome | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`frame_w` and `frame_l` set the footprint, `rim` the solid margin that carries load into the seat, and `plate_t` the thickness. `slot_w` and `slot_pitch` define the array. `outlet`, `clearance` and `spigot_len` fit the round grate into a pipe; `dome_rise` and `lip_drop` shape the leaf guard. All labels and tooltips are bilingual (en/es).

## Completes the published drainage chain

The drop-in bore is **not** a new series. It is the same round outlet set (50 / 68 / 75 / 87 / 100 / 110 mm) that `downspout-adapter` exposes as `outlet_dia` and that `drain-trap` accepts, so a printed grate, adapter and trap compose into a complete run without any of the three inventing its own pipe size. The grate was the only link missing.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| Round outlet series | 50 / 68 / 75 / 87 / 100 / 110 mm |
| Standard round downpipe | 68 mm (the default) |
| Heel- and bicycle-safe slot | ≤ 13 mm clear width |
| Minimum bar between slots | 2.0 mm (enforced, not advisory) |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Drop-In Outlet Bore** (`socket`, round outlet series 50–110 mm) — compatible with `downspout-adapter`, `drain-trap`, `condensate-fitting`.
  - **Grate Frame Footprint** (`profile`, internal) — the measured opening.
  - **Slot Array** (`grid`, pitch floored at slot width plus a 2 mm bar).
- **Material awareness:** shrinkage compensation, recycled-material toggle, tolerance-by-material.
- **Societal benefit:** closes an open gully the same week instead of leaving a hazard for months awaiting a non-standard casting.
- **License:** CERN-OHL-W-2.0

## Slot orientation, printing and load

**Orientation is a safety decision, not a style one.** Slots must run *across* the direction of travel wherever bicycles cross, or a wheel drops in and the rider goes over the bars — this is the classic and entirely avoidable grate injury. On a pedestrian surface keep the clear width at or under 13 mm so a heel, a cane tip or a small wheel cannot enter. The manifest raises a warning above 13 mm because the wider settings are meant for a yard or a soakaway, not a footway.

Print the grate flat, slots vertical through the plate, with high infill and many perimeters — the bars are beams and they carry in bending. **ASA** or pigmented **PETG**; PLA embrittles in UV and fails without warning under a foot load.

**Load scope — read this.** A printed grate is an **interim repair**, not a traffic-rated casting. It does not carry vehicle loads and must not be placed where a car or truck can run over it. Its proper use is exactly the gap that currently sits open and unguarded: closing a hole in a verge, a garden, a yard, a footway or a channel until a rated grate arrives. Nothing here is load-tested and this cartridge makes no engineering claim. Where a grate carries traffic, that is a specification question for the road authority.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode plus all six outlet options — 51/51 cases, each `is_watertight == True` with `body_count == 1`. An additional 93-case local grid covered the pathological combinations, including a 600 × 900 mm grate at minimum pitch and minimum rim.

A **patterned boolean array is the failure-prone shape in this whole domain**, and two specific traps are handled structurally rather than hoped over:

- **Slot count is derived, never taken from the UI.** `_slot_layout` computes how many slots fit in the space actually available after the rim, and clamps the first and last to keep a full bar to the frame. A slot landing flush with the frame edge would otherwise leave a knife-edge sliver or sever the bar outright.
- **Pitch is floored at `slot_w + 2 mm`.** A pitch smaller than the slot width leaves zero bar, which merges every slot into a single void and drops the frame's whole interior. Dialling pitch below width now silently yields the tightest legal array instead of a broken part.

One performance defect was also found and fixed: cutting 145 slots one at a time re-evaluated the solid on every cut and took **66 seconds**; collecting the cutters into a single compound and subtracting once takes **2.1 seconds** — a 31× speedup for an identical result. The cutters are disjoint by construction (the pitch floor guarantees it), so unioning them is exact rather than an approximation. The leaf dome, whose radial cutters *do* overlap at the axis, is safe under the same treatment because a compound cut is a union-then-subtract.

The dome itself ends on a small **flat apex** rather than running to a point on the rotation axis — a profile that touches the axis at a single point revolves into a pole singularity and returns two shells.
