# Raspberry Pi / SBC Case

A case for a single-board computer, generated with **CadQuery** (B-Rep). A board
table gives the correct PCB footprint and 4-hole mounting spacing for the
Raspberry Pi 4, Pi 5, and Pi Zero (or a fully parametric generic board); the case
models the mounting standoffs at the right hole rectangle, a base tray with
walls, a large port-edge opening, and a vented lid.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Boards

| `board` | PCB (mm) | Hole rectangle (mm) | Hole Ø |
| :--- | :--- | :--- | :--- |
| `rpi4` | 85 × 56 | 58 × 49 | 2.7 |
| `rpi5` | 85 × 56 | 58 × 49 | 2.7 |
| `rpi_zero` | 65 × 30 | 58 × 23 | 2.75 |
| `generic` | `gen_pcb_w` × `gen_pcb_d` | `gen_hole_x` × `gen_hole_y` | 2.75 |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Base** | `base` | Tray + walls, standoffs at the board holes, and a port-edge opening for USB / HDMI. |
| **Lid** | `lid` | A cover that drops over the base walls, optionally vented. |
| **Tray Only** | `tray` | The bottom tray (floor + standoffs), no walls. |

Render each mode with `target_part` set to that mode's part id to see the
distinct part.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Board | `board` | rpi4 | Board selector (or `generic`). |
| Generic Board | `gen_pcb_w` / `gen_pcb_d` | 80 / 55 mm | Generic board outline. |
| Generic Board | `gen_hole_x` / `gen_hole_y` | 70 / 45 mm | Generic hole spacing. |
| Shell | `wall` / `floor` | 2.4 / 2.4 mm | Wall and floor/lid thickness. |
| Shell | `clearance` | 1.5 mm | Board-edge to wall gap, per side. |
| Shell | `standoff_h` | 4.0 mm | Board height above the floor. |
| Shell | `wall_h` | 18 mm | Base wall height. |
| Openings & Vents | `port_cutout` | on | Port-edge opening (base). |
| Openings & Vents | `vents` | on | Lid cooling slots. |

## Presets

- **Pi 4 Case** — rpi4, 20 mm walls, port opening.
- **Pi Zero Slim** — rpi_zero, low walls, thin shell.
- **Pi 5 Vented Lid** — the matching vented cover.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **SBC Mounting Holes** (`bolt_pattern`, *RPi 40-pin form factor*) — the
    board's 4-hole rectangle, selected by `board` (or the generic spacing). Any
    board of that family drops onto the same standoffs.
  - **Port-Edge Opening** (`profile`, internal) — `port_cutout`, `wall_h`,
    `standoff_h`: the connector-edge window.
  - **Lid Slip Fit** (`snap`, internal) — `wall`, `clearance`, `floor`: the
    base/lid mating interface.
- **Material awareness:** `tolerance_by_material` is declared so the lid slip fit
  and standoff bores can be tuned per filament/printer.
- **Societal benefit:** SBCs ship as bare PCBs; a case built to the exact board
  keeps millions of Pis housed, cooled, and out of e-waste.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`
  and the active part is selected through `target_part`.
- All shipped presets and defaults render **watertight**.
