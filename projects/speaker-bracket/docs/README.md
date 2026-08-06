# Speaker Wall Bracket

A wall bracket for bookshelf / satellite speakers and small soundbars, built with
**CadQuery** (B-Rep). Every mode mounts to the wall through the same **keyhole
slot** interface — it drops onto two screw heads, then settles down to lock — and
cradles the speaker on the other side.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Shelf Bracket** | `shelf_bracket` | An L shelf the speaker sits on: a wall plate with keyholes, a horizontal shelf with a front retaining lip, and two side gussets. Optional downward tilt. |
| **Strap Mount** | `strap_mount` | A wall plate plus an open C-band that cradles a satellite speaker body; the top mouth lets the speaker slide in. |
| **Keyhole Plate** | `keyhole_plate` | A flat plate with wall keyhole slots on one side and a square speaker-screw bolt pattern for a speaker with its own bracket boss. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Wall Plate | `wall_w` / `wall_h` | 70 / 70 mm | Wall-plate size. |
| Wall Plate | `thickness` | 5.0 mm | Plate / shelf / band thickness. |
| Speaker Fit | `speaker_w` / `speaker_d` | 90 / 90 mm | Speaker body — sets shelf width & band diameter/height. |
| Speaker Fit | `shelf_depth` | 80 mm | Shelf reach (Shelf mode). |
| Speaker Fit | `lip_h` | 10.0 mm | Front retaining lip (Shelf mode). |
| Speaker Fit | `tilt` | 0° | Downward shelf tilt (Shelf mode). |
| Keyhole Mount | `keyhole_dia` | 9.0 mm | Screw-head hole. |
| Keyhole Mount | `keyhole_slot` | 4.5 mm | Screw-shank slot width. |
| Keyhole Mount | `keyhole_drop` | 12.0 mm | Lock-on travel. |
| Speaker Screws | `speaker_screw` | 4.5 mm | Speaker-screw clearance (Keyhole Plate). |
| Speaker Screws | `speaker_bolt_span` | 50.0 mm | Speaker bolt square side (Keyhole Plate). |

## Presets

- **Bookshelf Shelf** — an L shelf with a lip and 5° tilt for a bookshelf speaker.
- **Satellite Strap** — an open band cradling a small satellite speaker.
- **Screw Plate (50 mm)** — a keyhole plate with a 50 mm speaker-screw square.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Wall Keyhole Pattern** (`bolt_pattern`, standard **Wall Keyhole**) — the
    two keyhole slots (`keyhole_dia`, `keyhole_slot`, `keyhole_drop`) that hang
    the bracket on two wall screws in every mode.
  - **Speaker Cradle Profile** (`profile`, internal) — the shelf / band that
    holds the speaker, defined by `speaker_w`, `speaker_d`, `shelf_depth`,
    `lip_h`, `tilt`.
  - **Speaker Screw Pattern** (`bolt_pattern`, internal) — the square
    speaker-screw pattern (`speaker_screw`, `speaker_bolt_span`) in Keyhole
    Plate mode.
- **Material awareness:** hole and slot clearances are printable values tunable
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** speakers ship without wall mounts and third-party
  brackets rarely fit an odd satellite or soundbar; a bracket sized to the exact
  body and the wall's own screw spacing keeps audio off the desk with no
  proprietary hardware.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- The Strap Mount fuses the plate, neck, and band's outer disc first, then
  subtracts the speaker bore and the top mouth last — ending the boolean tree on
  cuts keeps the C-cradle a clean watertight solid. All three modes export
  watertight.
