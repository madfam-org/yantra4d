# GT2 / HTD Timing Pulley

A parametric synchronous-belt timing pulley generated with **CadQuery** (B-Rep).
The canonical drive pulley for 3D printers, CNC gantries, and small robotics.
Pick a belt standard and a tooth count; the pulley geometry is derived from the
standard so the printed pulley meshes a real belt.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Pitch-diameter math

The pulley **pitch diameter** is `PD = teeth × pitch ÷ π`. A synchronous belt
rides on the pitch line, which sits one *pitch-line differential* (PLD) below
the tooth tips, so the tooth-tip / outside diameter is `OD = PD − 2 × PLD`.

| Belt | Pitch | 20T Pitch Ø | 20T Outside Ø |
| :--- | :--- | :--- | :--- |
| GT2-2mm | 2.0 mm | 12.732 mm | 12.224 mm |
| GT2-3mm | 3.0 mm | 19.099 mm | 18.337 mm |
| HTD-3M | 3.0 mm | 19.099 mm | 18.337 mm |
| HTD-5M | 5.0 mm | 31.831 mm | 30.689 mm |

The belt's teeth sit in valleys cut into the pulley rim. Each valley is
approximated by a circular arc of a standard-specific radius centred on the
pitch circle — a close, watertight stand-in for the exact GT2 curvilinear / HTD
rounded profile.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pulley** | `pulley` | Toothed pulley with an optional set-screw hub. |
| **Flanged Pulley** | `pulley_flanged` | Adds retaining flanges above and below the belt. |
| **Idler** | `idler` | Smooth (toothless) flanged wheel bored for a bearing. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Belt & Teeth | `belt_type` | GT2-2mm | Belt standard → pitch. |
| Belt & Teeth | `teeth` | 20 | Tooth count → pitch/outside diameter. |
| Belt & Teeth | `width` | 6.0 mm | Rim width (6 mm GT2 belt). |
| Body & Bore | `bore` | 5.0 mm | Shaft hole (5 mm NEMA-17). |
| Flanges | `flange_h` | 1.2 mm | Retaining-flange thickness. |
| Hub & Set Screw | `hub` / `hub_dia` / `hub_height` | on / 12 / 6 mm | Set-screw hub. |
| Hub & Set Screw | `setscrew` / `setscrew_dia` | on / 3.2 mm | Radial M3 set screw. |
| Idler | `bearing_od` | 13.0 mm | Idler bearing press-fit seat. |

## Presets

- **GT2 20T · NEMA-17 (5 mm)** — the standard desktop-printer drive pulley.
- **GT2 16T Flanged (5 mm)** — a small flanged idler/drive pulley.
- **HTD-5M 30T · 8 mm bore** — a heavier CNC-scale pulley.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Timing Belt Tooth** (`profile`, GT2 (2mm) / HTD 3M/5M) — the meshing
    interface, defined by `belt_type`, `teeth`, `width`. Any belt of the same
    standard meshes a pulley printed at the correct pitch.
  - **Shaft Bore & Set Screw** (`socket`, internal) — `bore`, `setscrew`,
    `setscrew_dia`.
  - **Idler Bearing Seat** (`socket`, ISO 15 623/625/6900) — `bearing_od`,
    `width`.
- **Material awareness:** `tolerance_by_material` is declared; bore and bearing
  seat carry a small print clearance for tuning per material/printer.
- **Societal benefit:** GT2/HTD pulleys are the motion backbone of desktop 3D
  printers and CNC machines — an on-demand pitch-correct pulley keeps a machine
  running without waiting for a shipment.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
