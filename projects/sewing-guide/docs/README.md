# Sewing Machine Foot / Guide

Seam guides and simple presser-foot aids, generated with **CadQuery** (B-Rep).
The functional interface is the machine **shank** — low-shank machines sit
**3/4 in (19 mm)** from bar to needle plate, high-shank **1-1/4 in (32 mm)**.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Shank Seam Guide** | `shank_guide` | A split screw-clamp collar that grips the presser-bar shank and carries an adjustable seam finger beside the needle. |
| **Bed Seam Gauge** | `seam_gauge` | A plate that bolts to the needle plate through an obround slot, giving an adjustable straight seam fence. |
| **Edge Guide** | `edge_guide` | A right-angle edge fence with a thumbscrew slot; fabric runs along the fixed vertical edge for even topstitching / quilting. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shank | `shank_type` | `low` | Low (19 mm) or high (32 mm) bar-to-plate. |
| Shank | `bar_clear` | 0.3 mm | Per-side clamp-bore clearance on the presser bar. |
| Seam | `seam_dist` | 12.0 mm | Distance from needle line to the fabric-edge fence. |
| Body | `screw_d` | 4.2 mm | Set-screw / mount-bolt hole. |
| Body | `wall` | 4.0 mm | Body / plate / fence wall thickness. |
| Seam | `fence_h` | 16.0 mm | Edge-guide fence-wall height. |

## The shank interface (why it snaps on)

Household machines split almost universally into **low shank** and **high shank**
— the distance from the presser bar to the needle plate (19 mm vs 32 mm). The
shank guide is a **split collar**: a through-bore takes the presser bar, a saw
slit lets it flex, and a cross set-screw pinches it tight — the same clamp
principle as a snap-on foot adapter. Fabric rides a seam finger set at
`seam_dist` from the needle. The bed gauge and edge guide instead bolt to the
needle plate and slide along an **obround slot** to set the seam allowance
(e.g. the quarter-inch quilting seam).

## Presets

- **Low-Shank Seam Guide** — the shank-clamp guide for a low-shank machine.
- **Quarter-Inch Seam Gauge** — a 6.4 mm bed fence for quilting.
- **Quilting Edge Guide** — a tall edge fence for even margins.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Shank + Seam Guide** (`snap`, *low / high shank, 19 / 32 mm
  bar-to-plate*) — the collar bore + seam finger, defined by `shank_type`,
  `bar_clear`, `seam_dist`.
- **Material awareness:** `tolerance_by_material` is declared — `bar_clear` is
  exposed so the shank clamp fit tunes per material/printer.
- **Societal benefit:** even seam allowances make garments fit, yet branded guides
  are sold per machine and task; a printed shank-clamp or bolt-on fence gives any
  sewist a repeatable seam allowance without buying a foot per width.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The shank collar bore is a **through-hole** (vented); the saw slit opens the
  collar to a set-screw hole (no trapped void); seam fences use **obround** slots
  (mesh-robust vs arc-fan slots). Blanks are fillet-cleaned before cuts. All
  modes render **watertight**, single-body.
