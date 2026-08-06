# Hopper / Funnel Feeder

A hopper generated with **CadQuery** (B-Rep) that funnels bulk material (pellets,
granules, powder, small parts) down to an outlet. The taper wall angle is exposed
so it can be set **steeper than the material's angle of repose**, ensuring
reliable flow. Built as a genuine **watertight hollow shell** — a solid outer
funnel with an inner cavity and outlet bore cut away.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Round Hopper** | `round_hopper` | A conical funnel: round top → round outlet. |
| **Square Hopper** | `square_hopper` | A pyramidal funnel: square top → round outlet. |
| **Trough Feeder** | `trough_feeder` | A linear wedge trough narrowing to a slot outlet. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Top Opening | `top_w` / `top_d` | 120 / 120 mm | Top opening width (X) and depth (Y, square). |
| Outlet | `outlet_dia` | 20 mm | Round outlet diameter (slot width for the trough). |
| Outlet | `outlet_len` | 15 mm | Straight spout below the taper (0 = none). |
| Outlet | `slot_len` | 80 mm | Trough length (trough mode). |
| Taper & Wall | `height` | 100 mm | Minimum body height (raised if the wall angle needs it). |
| Taper & Wall | `wall_angle` | 60° | Taper angle from horizontal. |
| Taper & Wall | `wall` | 2.4 mm | Shell wall thickness. |
| Taper & Wall | `rim` | on | Top stiffening rim (round / square). |

## Presets

- **Pellet Funnel** — Ø120 → Ø20, 60° walls.
- **Steep Powder Hopper** — Ø100 → Ø12, 75° walls for fine powder.
- **Square Feed Bin** — 150×150 → Ø25.
- **Line Trough Feeder** — 120 wide, 120 long trough → 16 mm slot.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Hopper Taper** (`profile`, internal) — the flow-critical taper, defined by
    `outlet_dia` and `wall_angle`. Setting `wall_angle` above the material's angle
    of repose prevents bridging.
  - **Outlet Spout** (`socket`, internal) — `outlet_dia`, `outlet_len`, `wall`;
    the spout that mates to downstream tubing or a valve.
- **Material awareness:** `tolerance_by_material` is declared; the wall angle can
  be raised for stickier / recycled feedstock.
- **Societal benefit:** reliable bulk-material handling for makerspaces, farms,
  and small production — a flow-correct funnel keeps pellets, seed, or powder
  moving without bridging or store-bought hoppers.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`. `target_part`
  dispatches which mode part is built.
- Each hopper is a **hollow shell** built by cutting an inner cavity and the outlet
  bore from a solid funnel, so all modes and presets render **watertight**.
