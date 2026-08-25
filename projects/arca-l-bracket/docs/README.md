# Arca-Swiss L-Bracket

An **L-bracket** for the **Arca-Swiss** 38 mm tripod quick-release standard,
generated with **CadQuery** (B-Rep). An Arca plate that wraps up the camera's
left side so the same body drops into any Arca clamp in **landscape** (base
dovetail down) or **portrait** (wing dovetail out) with no re-levelling. Every
clamping face carries the same **38 mm dovetail** with ~45° flanks, so it mates
every Arca clamp, plate and ball head.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **L-Bracket** | `l_bracket` | A base dovetail plate plus a vertical wing on the +X side whose outer face carries its own Arca dovetail — landscape from the base, portrait from the wing. |
| **Flat QR Plate** | `flat_plate` | A plain 38 mm Arca dovetail plate (platform down) with an elongated 1/4-20 slot — a camera bolts on anywhere along the slot. |
| **Long Lens Foot** | `long_lens_foot` | A long Arca dovetail foot bar with twin 1/4-20 through-holes to replace a telephoto-lens tripod foot. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Arca Dovetail | `plate_w` | 38.0 mm | Dovetail platform width (Arca standard). |
| Arca Dovetail | `flank_ang` | 45° | Dovetail flank undercut angle from vertical. |
| Arca Dovetail | `plate_h` | 9.0 mm | Dovetail block height / plate thickness. |
| Arca Dovetail | `base_len` | 70.0 mm | Flat QR plate length (`flat_plate`). |
| 1/4-20 Slot & Holes | `slot_w` / `slot_len` | 6.6 / 30.0 mm | 1/4-20 camera slot/hole width and travel. |
| L Wing | `wing_h` / `wing_len` | 55.0 / 40.0 mm | Vertical wing height and base length (`l_bracket`). |
| Lens Foot | `foot_len` | 100.0 mm | Telephoto dovetail foot length (`long_lens_foot`). |

## The dovetail (why it holds and self-centres)

The Arca plate is a **38 mm dovetail** — wider at the bottom than the top because
the flanks undercut at `flank_ang`. The bottom width is
`plate_w + 2·plate_h·tan(flank_ang)`. A clamp jaw hooks under that undercut, so
tightening wedges the plate down and centres it. The L-bracket adds a second
identical dovetail on a vertical wing, unioned into the base with real material
overlap, so rotating the camera 90° into the clamp gives instant portrait
framing. Slots and holes are through-features that vent to outside — no trapped
voids form.

## Presets

- **Portrait L-Bracket (38mm)** — the reference bracket with a 55 mm wing.
- **Standard QR Plate** — the plain plate at spec dimensions.
- **Telephoto Lens Foot** — a 110 mm dovetail foot for a heavy lens.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Arca-Swiss Dovetail** (`profile`, *Arca-Swiss 38mm*) — the 38 mm dovetail
    cross-section, defined by `plate_w`, `flank_ang`, `plate_h`. **Mates:**
    [`arca-plate`](../../arca-plate/) (its clamp jaw and QR plate grip this
    dovetail).
  - **1/4-20 Camera Slot** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the plate's
    camera slot, defined by `slot_w`, `slot_len`. **Mates:**
    [`arca-plate`](../../arca-plate/) (shared tripod-screw slot).
- **Material awareness:** `tolerance_by_material` is declared — the dovetail
  dimensions are exposed so the clamp grip fit tunes per material/printer.
- **Societal benefit:** an Arca L-bracket lets a photographer switch a camera
  between landscape and portrait on any Arca-Swiss head without dropping the lens
  axis off-centre, and print one shaped to their exact body. It thickens the
  open `arca-swiss` family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All parts are extruded 2D dovetail cross-sections; the 1/4-20 slot (`slot2D`)
  and holes are through-cuts (vented); the wing is a vertical dovetail bar
  unioned with real overlap. All shipped modes and extreme-parameter cases
  render **watertight**, single-body, in well under 20 s.
