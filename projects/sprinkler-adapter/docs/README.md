# Sprinkler & Nozzle Adapter

Puts a real **Garden-Hose-Thread (GHT 3/4")** interface on the front of a hose so
any sprinkler, spray nozzle, or drip line screws on. Generated with **CadQuery**
(B-Rep). The thread is a genuine single-start helical rib, dimensionally matched
to the NH garden-hose finish (~26.4 mm major, 11.5 TPI).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **GHT Coupler** | `ght_coupler` | Female GHT thread on both ends — join two hoses or a hose to a GHT-tailed sprinkler. |
| **Nozzle Adapter** | `nozzle_adapter` | Female GHT socket to a reduced barbed push spout for tubing or a spray head. |
| **Y-Splitter** | `y_splitter` | One GHT inlet feeding two GHT outlets fanned out at ±`split_ang`. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread & Fit | `turns` | 2.0 | Thread engagement turns (capped at 2.5). |
| Thread & Fit | `clearance` | 0.35 mm | Per-side printed-thread slop. |
| Body & Bore | `wall` | 3.0 mm | Wall around the thread. |
| Body & Bore | `bore_dia` | 14 mm | Fluid channel diameter. |
| Body & Bore | `grip_knurl` | on | Knurl the hub for grip. |
| Outlet | `spout_dia` | 13 mm | Barbed spout OD (nozzle adapter). |
| Outlet | `barb_count` | 3 | Barb ridges (nozzle adapter). |
| Outlet | `split_ang` | 35° | Half-angle of each Y outlet. |

## Presets

- **Hose Join (GHT×GHT)** — straight coupler for two hoses.
- **Drip Tube Feed** — narrow barbed spout for 1/4" drip line.
- **Two-Way Splitter** — one tap into two hoses.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Garden Hose Thread** (`thread`, GHT 3/4") — the functional helical interface,
    defined by `turns`, `clearance`, `wall`, `bore_dia`. Every mode presents this
    same GHT geometry, so couplers, nozzle adapters, and splitters interchange with
    each other and with any commercial GHT hose end.
- **Material awareness:** `clearance` is exposed so the printed thread fit can be
  tuned per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** cracked, lost sprinkler fittings drive constant repurchase
  in fixed bundles — an on-demand GHT adapter reconnects a hose to whatever head is
  on hand and enables cheap drip irrigation.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- **Threads** use the volumetric-rib idiom — a trapezoidal profile swept along a
  real-radius `makeHelix`, unioned into the wall with an `overlap` so the mesh
  stays watertight. Turns are capped at 2.5 to keep renders fast (~5–19 s).
- All shipped presets and every mode render **watertight**.
