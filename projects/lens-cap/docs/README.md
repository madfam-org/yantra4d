# Lens & Filter Cap

Front lens caps, rear body caps and step rings for the universal photographic
**filter-thread** system, generated with **CadQuery** (B-Rep). Filter threads
run in a handful of nominal diameters (**49/52/58/67/72/77/82 mm**) at a fine
**0.75 mm** pitch; every lens front and screw-in filter shares them.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Snap Cap** | `snap_cap` | A pinch/press front cap sized to a lens's filter-thread OD, with an internal retaining bead that snaps over the outer thread crest. |
| **Step Ring** | `step_ring` | A step-up / step-down ring: a **female** filter thread on the bottom (`thread_a`, screws onto the lens) and a **male** thread on top (`thread_b`, accepts a filter of size B), with a clear light bore. |
| **Body Cap Blank** | `body_cap` | A rear body-cap disc with a locating lip and stiffening rib — a blank to plug a body or lens rear, sized by bayonet OD. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Filter Thread | `filter_thread` | 58 | Nominal filter size the snap cap fits. |
| Step Ring | `thread_a` / `thread_b` | 58 / 52 | Female (bottom) → male (top) filter sizes. |
| Step Ring | `thread_turns` | 4.0 | Thread engagement turns per side. |
| Filter Thread | `clearance` | 0.3 mm | Per-side thread/press fit slop. |
| Cap | `wall` | 2.4 mm | Side wall thickness. |
| Cap | `cap_depth` | 7.0 mm | Snap-cap skirt depth. |
| Cap | `top_th` | 2.2 mm | Cap top / step-ring web thickness. |
| Cap | `grip_teeth` | 0 | Optional grip flutes (0 = smooth). |
| Body Cap | `body_cap_d` | 42.0 mm | Rear body-cap bayonet OD. |

## Threads (cosmetic, on purpose)

Filter threads are **fit threads, not structural**, so this cartridge models
them as **cosmetic** solids of revolution: a serrated (sawtooth) radial profile
revolved 360°, so male crests trace the nominal major diameter and the female
bore relief traces a matching minor. One `revolve` per thread — fast (a few
seconds even at 8 turns) and inherently watertight, the right idiom for a light,
quick-screwing filter thread. The step-ring light bore runs all the way through
(vented); the snap-cap bead groove opens to the cap mouth.

## Presets

- **58 mm Lens Cap** — the most common front-cap size.
- **58→52 Step-Down Ring** — mount a 52 mm filter on a 58 mm lens.
- **67→77 Step-Up Ring** — mount a 77 mm filter on a 67 mm lens.
- **42 mm Body Cap** — a rear body-cap blank.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:**
  - **Filter Thread** (`thread`, *M49-M82 x 0.75*) — the photographic filter
    thread, defined by `filter_thread` (cap) and `thread_a` / `thread_b`
    (ring), at 0.75 mm pitch. Any cap or ring built to a listed size mates with
    every lens and filter that shares it.
- **Material awareness:** `tolerance_by_material` is declared — `clearance` is
  exposed so the thread/press fit tunes per material/printer.
- **Societal benefit:** the filter thread is a decades-old open standard; lost
  caps and missing step rings are a constant wasteful expense, and on-demand
  caps and rings replace a lost cap or bridge two filter sizes for pennies of
  filament, keeping filters and lenses in use.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Threads are single solids of revolution (no per-turn booleans). Bores are
  through-holes (vented); the step-ring is assembled from overlapping tubes and
  thread solids. All shipped modes and presets render **watertight** in well
  under 20 s, including the largest thread combinations.
