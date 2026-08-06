# Parametric Project Enclosure

A Hammond-style two-part project box for electronics, generated with
**CadQuery** (B-Rep) and sized by its **interior** cavity to a PCB. The base
carries corner PCB standoffs bored for the chosen screw, optional rectangular
side ports, and optional vent slots; the lid closes with either screw tabs or a
printed snap lip.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Base** | `base` | Hollow shell, PCB standoffs at the board corners, side-port cutouts, vents, and (in snap mode) a top-rim lip. |
| **Lid** | `lid` | The cover: screw-tab holes with counterbores, or a downward snap skirt that nests into the base. |

The lid geometry mirrors the base closure: pick `screw` for a bolted lid or
`snap` for a hardware-free press fit. Render each mode with `target_part` set to
that mode's part id to see the distinct part.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Interior Size | `inner_w` / `inner_d` / `inner_h` | 90 / 60 / 35 mm | Usable interior X / Y / Z. |
| Shell | `wall` | 2.4 mm | Side wall thickness. |
| Shell | `floor` | 2.4 mm | Base floor and lid plate thickness. |
| Shell | `corner_r` | 3.0 mm | Outer corner rounding. |
| PCB Mounting | `pcb_w` / `pcb_d` | 70 / 50 mm | Board size → corner standoff positions. |
| PCB Mounting | `standoff_h` | 5.0 mm | Height the board sits above the floor. |
| PCB Mounting | `screw_size` | M3 | M2.5 or M3 — sets standoff bore and lid head recess. |
| Lid Closure | `lid_mount` | screw | `screw` tabs or `snap` lip. |
| Ports & Vents | `port_count` | 0 | Rectangular cutouts through the front wall. |
| Ports & Vents | `port_w` / `port_h` / `port_z` | 16 / 8 / 4 mm | Port width, height, and bottom offset above floor. |
| Ports & Vents | `vents` | off | Cooling slots through the side walls. |

## Presets

- **Arduino Uno Case** — 75×58×28, board 68×53, two front ports.
- **Sensor Node (snap)** — 50×40×22, M2.5, snap lid, vented.
- **Vented Power Box** — 120×80×45, thick walls, one wide port, vented.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **PCB Standoff Mount** (`pocket`, internal) — the corner standoff array,
    defined by `pcb_w`, `pcb_d`, `standoff_h`, `screw_size`. Any board matching
    that footprint drops onto the same bored pillars.
  - **Side Port Cutout** (`profile`, internal) — `port_count`, `port_w`,
    `port_h`, `port_z`: the rectangular connector openings on the front wall.
  - **Lid Closure Seam** (`snap`, internal) — `lid_mount`, `inner_w`, `inner_d`,
    `wall`, `screw_size`: the base/lid mating interface. A lid built at the same
    interior size and closure type fits the base.
- **Material awareness:** the screw bore is sized slightly under nominal so
  thread-forming screws bite plastic directly; `tolerance_by_material` is
  declared so the snap clearance can be tuned per filament.
- **Societal benefit:** a print-on-demand enclosure sized to the exact board and
  ports, keeping DIY electronics housed, protected, and repairable.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`, and the active
  part is selected through `target_part`.
- All shipped presets and defaults render **watertight**.
