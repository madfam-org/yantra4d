# Bike Wall Rack

Wall-mounted bicycle storage, built with **CadQuery** (B-Rep). A load-rated wall
plate screws to the studs; an arm projects from it to carry the bike
horizontally (by the top tube), vertically (by a wheel), or as a pedal shelf. The
tube/wheel contact is a **half-round cradle pocket** so the frame or rim rests
without point loads.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Horizontal Hook** | `horizontal_hook` | A J cradle on a horizontal arm: the bike's top tube drops into a half-round pocket with an up-turned lip, so the bike hangs level along the wall. |
| **Vertical Hook** | `vertical_hook` | A taller J whose cradle radius fits the tire, so the bike hangs nose-up by a wheel; a tall lip captures the wheel. |
| **Pedal Shelf** | `pedal_shelf` | A braced flat shelf with a central slot the pedal/crank drops into, so the bike stands with a pedal supported. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cradle & Arm | `tube_w` | 35 mm | Top-tube diameter cradled (also sizes the pedal slot). |
| Cradle & Arm | `tire_w` | 40 mm | Tire/rim width (Vertical Hook). |
| Cradle & Arm | `arm_len` | 90 mm | Arm / shelf projection from the wall. |
| Cradle & Arm | `arm_w` | 45 mm | Cradle / shelf width across the bike. |
| Cradle & Arm | `thickness` | 10.0 mm | Structural thickness (load-bearing — keep generous). |
| Cradle & Arm | `lip_h` | 20.0 mm | Up-turned retaining lip / hook. |
| Wall Plate | `plate_w` | 60 mm | Plate width (wide → splayed screws). |
| Wall Plate | `plate_h` | 120 mm | Plate height (taller resists tip-out). |
| Stud Mount | `stud` | `single` | Stud spacing: single / 16 in / 24 in. |
| Stud Mount | `screw_dia` | 6.5 mm | Lag/wood screw clearance. |

## Presets

- **Road Bike Horizontal** — a 32 mm top-tube cradle on a 90 mm arm, single stud.
- **MTB Vertical (wheel)** — a 60 mm tire hook on a tall plate, single stud, M8 lags.
- **Pedal Shelf (16 in studs)** — a braced pedal shelf splayed across 16 in studs.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Wall Stud Mount** (`bolt_pattern`, standard **Wall Stud Mount**) — the
    stud-spaced lag-screw pattern (`stud`, `screw_dia`, `plate_w`, `plate_h`).
    Single-stud stacks two screws vertically; 16 in / 24 in splay to two studs
    when the plate is wide enough, so the load always lands on framing.
  - **Tube / Wheel Cradle** (`pocket`, internal) — the half-round cradle that
    holds the tube or tire, defined by `tube_w`, `tire_w`, `arm_w`, `lip_h`.
- **Material awareness:** screw clearances are printable values tunable per
  material/printer; `tolerance_by_material` is declared. Thickness is clamped to
  a load-appropriate minimum (≥6 mm).
- **Societal benefit:** commercial bike hooks come in one size and one hanging
  style; a rack sized to the bike's own tube or tire and to the wall's real stud
  spacing puts a bicycle safely on the wall — horizontally, vertically, or by a
  pedal — reclaiming floor space without a fixed-fit hook per bike.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The cradle is a single horizontal cylinder cut wider than the arm, giving a
  smooth half-round trough that stays watertight. The plate, arm, lip, and brace
  fuse into one solid; all three modes export watertight. Thickness is
  deliberately clamped high because the part carries a bicycle.
