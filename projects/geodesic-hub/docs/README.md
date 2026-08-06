# Geodesic / Strut Hub Connector

A parametric **strut hub** generated with **CadQuery** (B-Rep) — the central
vertex node that joins several struts (dowels, tubes, or pipes) at defined angles
to build domes, shelters, trellises, tensegrity frames, and geodesic structures.
Each strut plugs into a cylindrical socket on an arm radiating from a solid core;
an optional pin/screw cross-hole locks every strut in place.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Flat Hub** | `flat_hub` | All struts lie in one plane at equal angular spacing — a planar hub-and-spoke node. |
| **Dome Hub** | `dome_hub` | The strut arms tilt **up** out of the plane by the cone/rise angle — the classic geodesic-dome vertex. |
| **Ground Anchor** | `ground_anchor` | Struts point up from a flat, stake-able base plate with a ring of peg holes to pin the frame down. |

The studio dispatches the active part via `target_part`.

## Hub styles (`hub_style`)

| Style | Effect |
| :--- | :--- |
| `radial_flat` | All struts in a single plane at `360°/struts` spacing. |
| `cone` | Arms tilt up by `cone_angle`. |
| `custom_5v` | A preset 5-way **2V geodesic dome vertex** (fixes `struts` = 5, `cone_angle` ≈ 12°). A buildable approximation, not a survey-grade node. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Struts & Sockets | `strut_dia` | 12.0 mm | Nominal dowel/tube diameter (socket bore = this + clearance). |
| Struts & Sockets | `struts` | 5 | Number of struts meeting at the hub (2–12). |
| Struts & Sockets | `socket_depth` | 22.0 mm | How deep each strut seats. |
| Struts & Sockets | `socket_wall` | 3.0 mm | Wall around each socket bore. |
| Struts & Sockets | `clearance` | 0.4 mm | Added to the strut diameter for a printable slip fit. |
| Hub Geometry | `hub_style` | `radial_flat` | Radial / cone / custom 5V. |
| Hub Geometry | `cone_angle` | 25° | Arm rise above the plane (Dome / Ground Anchor). |
| Fixing | `pin_holes` | on | Cross-drill each socket for a locking pin/screw. |
| Fixing | `pin_dia` | 3.5 mm | Pin hole diameter (auto-clamped below the strut). |
| Ground Anchor | `anchor_dia` | 70.0 mm | Base plate diameter. |
| Ground Anchor | `anchor_thick` | 5.0 mm | Base plate thickness. |

The central core auto-sizes to the strut count and diameter so neighbouring arm
roots space cleanly around the rim (watertight union at any setting).

## Presets

- **Trellis Node (5 × 12 mm)** — a flat 5-way garden-trellis node.
- **Geodesic 5V Dome Vertex** — the preset dome vertex at 16 mm struts.
- **Shelter Ground Anchor (3-leg)** — a steep 3-leg tripod foot on a 90 mm staked base.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Strut Socket** (`socket`, internal) — the strut-to-hub interface, defined by
    `strut_dia`, `struts`, `socket_depth`, `clearance`, and the pin params. Any
    strut cut to length seats in a socket generated at the same diameter + clearance.
  - **Ground Stake Pattern** (`bolt_pattern`, internal) — the base-plate peg ring
    (`anchor_dia`, `anchor_thick`) for tent pegs or ground screws.
- **Material awareness:** the fit clearance is exposed (`clearance`) so the socket
  slip fit tunes per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** one printable node turns cheap dowels, bamboo, or conduit
  into domes, trellises, and emergency shelters — democratizing large-span
  structures without proprietary connector kits.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Arms fuse into a short **cylindrical** core (flat faces union far more reliably
  than a sphere); every shipped preset, mode, and extreme renders **watertight**.
