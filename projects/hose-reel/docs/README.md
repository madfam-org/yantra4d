# Hose & Cord Reel

A parametric winder for garden hose, extension cord, string-trimmer line, or
rope, generated with **CadQuery** (B-Rep). A hollow-core drum with two lightened
retaining flanges holds the coil; the **core hub** is an open socket that accepts
an axle or a printed crank shaft.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Reel** | `reel` | The bare drum: hollow barrel, two flanges, axle bore. |
| **Wall Reel** | `wall_reel` | Reel plus a back plate with keyholes and a stub axle to hang on a wall. |
| **Hand Winder** | `hand_winder` | Reel plus a crank arm and turning knob for winding by hand. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Drum & Hub | `hub_dia` | 40 mm | Barrel the coil winds onto. |
| Drum & Hub | `axle_dia` | 12 mm | Central axle / crank-shaft bore. |
| Drum & Hub | `drum_width` | 90 mm | Winding width between flanges. |
| Drum & Hub | `hub_wall` | 4.0 mm | Barrel wall thickness. |
| Flanges | `flange_dia` | 150 mm | Retaining disk diameter. |
| Flanges | `flange_th` | 5.0 mm | Flange thickness. |
| Flanges | `spokes` | 6 | Lightening holes per flange (0 = solid). |
| Mount & Crank | `crank_len` | 70 mm | Crank arm reach (hand winder). |
| Mount & Crank | `crank_th` | 10 mm | Crank arm / knob thickness. |
| Mount & Crank | `mount_gap` | 28 mm | Wall keyhole spacing reference. |

## Presets

- **Garden Hose (wall)** — wide drum, 220 mm flanges, wall-mounted.
- **Extension Cord Winder** — compact drum with an 80 mm crank.
- **Trimmer Line Spool** — small bare reel for cutting line.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Reel Core Hub** (`socket`, internal) — the open barrel bore defined by
    `hub_dia`, `axle_dia`, `hub_wall`, `drum_width`. Any 12 mm axle, threaded rod,
    or the printed crank drops straight through, so the same drum works stationary,
    wall-mounted, or hand-cranked.
- **Material awareness:** `axle_dia` is exposed so the bore can be tuned to the
  chosen rod and material shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** kinked hoses and tangled cords drive premature
  replacement — an on-demand reel sized to the exact line extends its life.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. Lightening cuts and
  rim chamfers are wrapped in try/except so extreme inputs still build watertight.
- All shipped presets and every mode render **watertight**.
