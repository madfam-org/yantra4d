# Cable Drag Chain (e-chain)

A printable **cable drag chain** (cable carrier / energy chain) generated with
**CadQuery** (B-Rep). One link pins to identical links to form a flexible carrier
that guides cables and hoses on moving axes — 3D printers, CNC gantries, and
linear stages — while a built-in stop limits how tightly the chain can bend.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Link** | `link` | One rigid closed-frame segment: two side plates + top & bottom cross-bars, a peg on the +X end and a socket on the −X end, plus a pivot-stop lug. |
| **Openable Link** | `link_open` | Same frame with a separate snap-on top bar (retention tabs into side-plate notches) so cables can be laid in. |
| **End Bracket** | `end_bracket` | A flat mounting foot with two countersunk bolt holes rising into a short frame stub that presents a link-compatible peg end. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cable Channel | `inner_w` / `inner_h` | 18 / 16 mm | Interior Y / Z space for cables. |
| Link Geometry | `pitch` | 30 mm | Link length along travel (X). Clamped to ≥ `pin_dia`·3.5 + 6. |
| Link Geometry | `wall` | 2.4 mm | Side-plate and cross-bar thickness. |
| Pin Joint | `bend_radius` | 40 mm | Minimum bend radius; drives the pivot-stop angle. |
| Pin Joint | `pin_dia` | 4.0 mm | Peg/socket nominal diameter. |
| Pin Joint | `clearance` | 0.35 mm | Per-side pin-in-socket gap for a printable pivot. |

## Presets

- **3D-Printer Axis (15×15)** — compact link for a typical printer cable run.
- **CNC Gantry (40×30)** — larger channel, thicker walls, gentler bend.
- **Frame Mount Bracket** — the End Bracket sized to the default channel.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Drag-Chain Link Pin** (`snap`, internal) — the peg/socket pivot that joins
    links, defined by `pitch`, `bend_radius`, `pin_dia`, `clearance`. Any link (or
    the end bracket stub) built at the same `pin_dia` + `clearance` pins to any
    other, and `bend_radius` sets the stop-lug rake so a run curves consistently.
- **Material awareness:** the pin fit is exposed (`clearance`) so the pivot can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** cable carriers wear out and are rarely stocked in the exact
  size a repair needs — an on-demand printable e-chain keeps machines running
  without proprietary catalog parts.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Each link is one closed-frame solid (front/back open as the cable channel); pins
  union into the plates and sockets are cut, with small overlaps so every boolean
  is volumetric. **All shipped presets, all modes, and both size extremes render
  watertight.**
