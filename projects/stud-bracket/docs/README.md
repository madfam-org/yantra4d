# Stud-Mount Bracket Kit

Wall-stud mounting hardware, built with **CadQuery** (B-Rep). Every part fastens
to the US framing standard — studs on **16 in (406.4 mm)** centres, driven with
**#8/#10 wood or drywall screws** — and shares that stud-pitch interface, so the
kit interoperates with `bike-wall-rack` and grows the **wall-stud** family.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Stud Backing Plate** | `stud_plate` | A flat plate spanning one or two stud bays, with countersunk fixing screws and a keyhole hanging slot per stud — screws down *and* hangs. |
| **Stud Shelf Bracket** | `stud_shelf` | A gusseted right-angle shelf into a single stud; the triangular web carries the load out from the wall. |
| **Stud J-Hook** | `stud_hook` | A stout swept J-arm on a stud plate for hanging tools, hoses, cable or a bike off the framing. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Stud Interface | `stud_pitch` | 406.4 mm | Centre-to-centre stud spacing (16 in US standard; 24 in = 610 mm). |
| Stud Interface | `bays` | 1 | Stud bays spanned: 1 → two studs, 2 → three studs. |
| Stud Interface | `screw_dia` | 4.5 mm | Screw shank clearance (#8 ~4.2, #10 ~4.8 mm). |
| Stud Interface | `screw_head` | 9.0 mm | Countersink diameter for a flush flat head. |
| Plate | `plate_h` | 90 mm | Vertical plate height. |
| Plate | `plate_t` | 6.0 mm | Plate / wall thickness. |
| Shelf | `shelf_depth` | 120 mm | Shelf projection from the wall. |
| Hook | `hook_len` | 70 mm | Hook arm length before it turns up. |
| Hook | `hook_dia` | 20 mm | Solid hook-arm diameter (load capacity). |

## Presets

- **Single-Bay Backing Plate** — a 6 mm plate spanning two studs at 16 in.
- **Heavy Shelf Bracket** — an 8 mm gusseted shelf projecting 150 mm.
- **Tool / Hose Hook** — a 20 mm J-hook arm on a 6 mm stud plate.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **16 in Wall Stud Mount** (`bolt_pattern`, standard **16in wall stud**) — the
    stud-spaced screw pattern (`stud_pitch`, `bays`, `screw_dia`, `screw_head`).
    Compatible with **bike-wall-rack**, which mounts on the same 16 in pitch.
  - **Keyhole Hanging Slot** (`snap`, internal) — the drop-on keyhole
    (`screw_dia`, `screw_head`) that lets the plate hang on a proud screw head.
- **Material awareness:** screw and countersink clearances are printable values
  tunable per material/printer; `tolerance_by_material` is declared. Plate
  thickness is clamped to a load-appropriate minimum (≥4 mm).
- **Societal benefit:** the 16 in wall-stud pitch is the load-bearing skeleton of
  nearly every North American home. Printable stud brackets, shelves and hooks
  let a renter or homeowner hang real weight off the framing — shelving, tools,
  bikes, cable — without a proprietary rail system per fixture.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Watertight construction: the blank is filleted before any feature cut;
  keyhole slots are obround + bored-circle cuts that vent through the plate; the
  shelf gusset unions into the plate with real overlap; the J-hook is a circle
  **swept along a tangent-arc L-path** (a sharp 90° corner in a round-transition
  sweep tessellates non-watertight — the arc avoids it). All three modes and the
  min/max parameter extremes export watertight, single-body.
