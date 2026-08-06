# Refillable Spice Jar

A refillable spice jar generated with **CadQuery** (B-Rep). The jar mouth carries
a **real single-start helical thread**, and the lids (shaker / pour / solid) carry
the mating internal thread. Jar and lid threads are cut from the **same nominal
envelope** (`mouth_dia`, `pitch`), so any lid screws onto any jar of the same mouth
size.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Jar** | `jar` | The vessel: solid floor, open threaded mouth (external thread). |
| **Shaker Lid** | `shaker_lid` | Screw lid with a centered hole + ring of shaker holes. |
| **Pour Lid** | `pour_lid` | Screw lid with a single larger pour-spout opening. |

The `lid_type` select (**Auto** by default) follows the chosen mode; set it to
`shaker-holes`, `pour-spout`, or `solid` to override the opening on either lid mode.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Jar Body | `jar_dia` / `jar_h` | 45 / 70 mm | Outer diameter and total height. |
| Jar Body | `wall` / `floor` | 2.4 / 2.4 mm | Wall (body + lid) and jar floor. |
| Mouth & Thread | `mouth_dia` | 34 mm | **Thread major Ø — set the SAME on jar and lid.** |
| Mouth & Thread | `pitch` / `turns` | 3.0 mm / 1.6 | Thread pitch and engagement turns. |
| Mouth & Thread | `clearance` | 0.4 mm | Per-side thread fit slop (lid). |
| Lid | `lid_h` | 14.0 mm | Lid skirt height. |
| Lid | `lid_type` | auto | `auto` / `shaker-holes` / `pour-spout` / `solid`. |
| Lid | `hole_dia` / `hole_ring` | 3.5 mm / 7 | Shaker hole size and count. |
| Lid | `spout_dia` | 12.0 mm | Pour-spout opening diameter. |

## Presets

- **Standard Spice Jar** — 45×70 mm body, 34 mm mouth.
- **Fine Shaker Top** — 34 mm mouth, seven 3 mm holes.
- **Pour Top** — 34 mm mouth, 14 mm pour opening.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Jar Screw Thread** (`thread`, internal) — the mating helical interface,
    defined by `mouth_dia`, `pitch`, `turns`, `clearance`. The jar carries the
    external (male) rib and the lid the internal (female) rib, both from one
    nominal envelope, so components printed at the same `mouth_dia`/`pitch`
    interoperate. Verified: at defaults, neck-to-bore radial clearance = the fit
    `clearance` (0.40 mm) and threads engage ~2.9 mm radially.
- **Material awareness:** thread `clearance` is exposed so the screw fit can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a refillable, print-at-home spice container that
  standardizes the shelf on one open thread instead of dozens of proprietary caps.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Threads** use the volumetric-rib idiom: a trapezoidal profile swept along a
  genuine `makeHelix` for ~1–2 turns, with the rib root pushed into the wall so
  the boolean union stays watertight. Render is fast (~3–6 s per part at defaults).
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
