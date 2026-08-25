# Drip Irrigation Manifold

A multi-outlet distributor for US micro-drip irrigation, built with **CadQuery**
(B-Rep). It takes one supply feed and splits it to several **1/4 in barbed
outlets**. That barb (nominal 1/4 in tubing: ID ~4.3 mm / 0.170 in, OD ~6.4 mm)
is the same interface the `drip-fitting` cartridge produces, so hoses and
fittings interoperate across the **drip-irrigation** family.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Inline Bar Manifold** | `manifold_bar` | A supply plenum with N barbed outlets in a row along the top, inlet barb at one end — the field workhorse. |
| **Radial Star Hub** | `manifold_cross` | A compact chamber with N barbs radiating in-plane and a bottom inlet — a point distributor for a cluster. |
| **Y-Splitter** | `manifold_wye` | One inlet feeding two barbed legs — the minimal branch for a single line. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Outlet Layout | `outlets` | 6 | Number of 1/4 in barbed outlets (bar / star). |
| Outlet Layout | `spacing` | 16 mm | Pitch between adjacent outlets. |
| 1/4in Barb Outlet | `barb_od` | 6.0 mm | Barb ridge OD (grips 1/4 in tube ID ~4.3 mm). |
| 1/4in Barb Outlet | `barb_lumen` | 3.6 mm | Through-bore flow passage per outlet. |
| 1/4in Barb Outlet | `barb_len` | 12 mm | Barb spigot length. |
| Supply Body | `inlet_od` | 16 mm | Supply body / inlet OD (~1/2 in poly tubing). |
| Supply Body | `wall` | 3.0 mm | Wall around the internal plenum. |

## Presets

- **6-Outlet Bar** — an inline bar with six 1/4 in outlets at 16 mm pitch.
- **6-Way Star Hub** — a radial hub feeding six lines from a point.
- **Simple Y-Splitter** — one inlet branching to two 1/4 in barbs.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **1/4 in Drip Barb Outlet** (`socket`, standard **1/4in drip**) — the ribbed
    barb spigot (`barb_od`, `barb_lumen`, `barb_len`). Compatible with
    **drip-fitting**, which produces the same 1/4 in barb.
  - **Supply Plenum** (`socket`, internal) — the internal distribution chamber
    (`inlet_od`, `wall`) fed from the inlet barb.
- **Material awareness:** barb and lumen dimensions are printable values tunable
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** micro-drip saves water at the root, but off-the-shelf
  manifolds come in fixed outlet counts. A manifold sized to the exact number of
  drip lines a bed needs lets a gardener branch a watering system on demand from
  a single 1/4 in barb standard, and repair a cracked distributor in the field.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Watertight construction: the body is solid, then the plenum is bored **open at
  the inlet only** and stopped short of the far end (a closed chamber — a bore
  open at both ends around the barb lumens tessellates non-watertight). Barbs are
  **volumetric fused frusta** unioned with overlap; each outlet lumen is bored
  through its barb into the plenum **last**, so the interior is one connected air
  space venting through inlet + outlets — a closed, watertight surface with no
  trapped void. All three modes and the min/max extremes export watertight,
  single-body.
