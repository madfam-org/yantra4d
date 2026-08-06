# DIN Rail Terminal Comb

Terminal-block accessories for standard top-hat **DIN rail (TS35, DIN EN 60715 —
35 mm across the lips, 7.5 mm deep)**, generated with **CadQuery** (B-Rep), that
index against the terminal-block pitch. Part of the **Yantra4D Hyperobjects
Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Feed / Jumper Comb** | `feed_comb` | A bar above the DIN clip with a row of `poles` prongs at terminal `pitch` that bridge adjacent terminals into one potential. |
| **End Stop Bracket** | `end_bracket` | A compact block that clips on the rail and presses against the end of a terminal row so blocks can't slide; a locking screw pilot runs through it. |
| **Marker Carrier** | `marker_carrier` | A low strip that clips on the rail and presents a row of `poles` label windows at terminal `pitch`. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Terminal Pitch | `pitch` | 5.2 mm | Centre-to-centre terminal-block spacing. |
| Terminal Pitch | `poles` | 6 | How many terminals the comb bridges / strip labels. |
| Features | `prong_d` | 2.6 mm | Jumper prong diameter (`feed_comb`). |
| Features | `comb_h` | 10.0 mm | Body height above the clip. |
| Features | `label_w` | 4.2 mm | Label window width (`marker_carrier`). |
| DIN Clip | `plate_th` | 4.0 mm | Mount-plate thickness of the clip back. |
| Features | `screw_d` | 3.4 mm | End-stop locking screw (M3, `end_bracket`). |

## The DIN clip (why it grips, and stays watertight)

The clip back is the proven **DIN TS35 idiom**: a mount plate with a **rigid
reference hook** on one lip and a **compliant spring hook** on the other, each an
XZ cross-section extruded symmetrically about the rail axis and **unioned with
overlap** into the plate. The spring hook flexes over the rolled lip and springs
back to grip. Combs, blocks and label frames are **unioned overlapping solids**
(never tangent); prongs are **solid posts** (no trapped voids); screw pilots and
label windows are **through-cuts that vent to outside**. Blanks are filleted
before feature cuts.

## Presets

- **6-Pole Comb (5.2 mm)** — the reference jumper for a common terminal block.
- **12-Pole Marker Strip** — a label carrier for a wider terminal row.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **DIN TS35 Rail Clip** (`rail`, *DIN EN 60715*) — the top-hat clip back.
    Mates `din-module`, `busbar-support`, `devboard-tray`, `din-rail-clip`.
  - **Terminal-Block Pitch** (`profile`, *internal*) — the terminal indexing
    defined by `pitch`, `poles`.
- **Material awareness:** `tolerance_by_material` is declared — the spring-hook
  grip and prong fit tune per material/printer.
- **Societal benefit:** DIN rail is the universal open backbone of control panels,
  but terminal-block accessories are proprietary and easily lost; a printed comb,
  end bracket or marker strip at the right pitch keeps a panel serviceable with
  commodity parts.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All shipped modes and per-mode extreme parameter cases render **watertight**,
  single-body, in well under 20 s.
