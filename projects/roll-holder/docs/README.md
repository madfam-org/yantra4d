# Paper-Towel Roll Holder

Holds a paper-towel or wrap roll on a **spindle** generated with **CadQuery**
(B-Rep), sized to the roll's cardboard **core** inner diameter (`core_dia`). The
spindle is the shared interface; swap only the mount to move between wall, cabinet,
and counter.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wall Holder** | `wall_holder` | Screw-hole back plate; spindle cantilevers out. |
| **Under-Cabinet** | `under_cabinet` | L-bracket that screws up under a shelf; roll tucks beneath. |
| **Counter Stand** | `counter_stand` | Weighted disc base + post + top spindle for one-handed tear-off. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Roll & Spindle | `core_dia` | 44 mm | **Roll core INNER diameter (typ. 38–45 mm).** |
| Roll & Spindle | `spindle_len` | 130 mm | Roll width the spindle spans. |
| Roll & Spindle | `clearance` | 0.6 mm | Per-side gap so the roll spins freely. |
| Mount | `mount` | wall | Reference mount style select (wall holder). |
| Mount | `screw_dia` | 4.5 mm | Mounting screw clearance hole. |
| Structure | `plate_w` | 60 mm | Back-plate width / counter base diameter. |
| Structure | `post_h` | 180 mm | Counter-stand post height. |
| Structure | `wall` | 3.0 mm | Structural wall thickness. |

## Presets

- **Kitchen Wall Roll** — 44 mm core, 130 mm width, wall plate.
- **Under-Shelf Roll** — under-cabinet L-bracket.
- **Counter Tear Stand** — weighted base, 190 mm post.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Roll Core Spindle** (`socket`, internal) — the spindle, defined by
    `core_dia`, `spindle_len`, `clearance`, `wall`. **Verified fit:** at defaults
    the spindle radius (21.4 mm) slides into the 22 mm core with 0.6 mm/side
    clearance, and a 25 mm shoulder flange stops the roll sliding off. Every mount
    reuses this spindle unchanged.
- **Material awareness:** spindle `clearance` is exposed so the spin fit can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** one spindle fits every household roll measured at the core,
  and swapping only the mount replaces three bought products with one printable family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The spindle root is fused into each mount with an overlap for a watertight
  boolean; the free tip is chamfered so the roll starts on easily.
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
