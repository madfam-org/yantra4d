# Drip-Irrigation Fitting

Barbed fittings for drip-irrigation tubing, generated with **CadQuery** (B-Rep):
**straight** couplers, **tees**, **elbows**, and **end caps**. The barbs are sized
to the tubing **inner** diameter and push in to grip from inside, so pressurized
water won't blow the joint apart. Sized for the two common drip tubes: 1/4" (~6 mm
ID) and 1/2" (~16 mm ID).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Straight Coupler** | `straight` | Two barbed prongs back-to-back through a collar. |
| **Tee** | `tee` | Straight run plus a 90° branch prong; cross channel. |
| **Elbow / End Cap** | `elbow_cap` | 90° elbow, or (via `fitting`) a sealed end cap. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on. The
`elbow_cap` part builds an elbow by default and an end cap when `fitting = end_cap`.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tubing | `tube_id` | 6.0 mm | Tube inner diameter (1/4" ≈ 6, 1/2" ≈ 16). |
| Fitting Shape | `fitting` | straight | In Elbow mode: elbow vs end_cap. |
| Barb & Fit | `barb_count` | 3 | Ridges per prong. |
| Barb & Fit | `prong_len` | 14.0 mm | Insertion length per prong. |
| Barb & Fit | `grip` | 0.5 mm | Barb crest over-size beyond tube ID. |
| Barb & Fit | `wall` | 1.4 mm | Prong / collar wall. |

## Presets

- **1/4" Straight Coupler** — the everyday drip splice.
- **1/4" Tee** — branch a lateral line.
- **1/2" Elbow** — turn a corner on 1/2" mainline.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Drip Barb Fitting** (`socket`, 1/4in & 1/2in drip) — the barb-to-tube grip,
    defined by `tube_id`, `fitting`, `barb_count`, `grip`, `prong_len`. Any fitting
    at the same `tube_id` interchanges on the same tubing.
- **Material awareness:** `grip` and `wall` tune the interference fit per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** water-saving irrigation on demand — build or repair a drip
  system from standard tubing, cutting garden water use.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- All fittings share one `barb_spigot()` prong helper; prongs root into a solid
  collar (or a spherical hub for the elbow) before the channel is bored, so every
  part exports **watertight**.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
