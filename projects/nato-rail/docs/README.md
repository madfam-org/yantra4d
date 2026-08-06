# NATO Accessory Rail

The **NATO accessory rail**, generated with **CadQuery** (B-Rep): a dovetail
cross-section with ~44° flanks and safety notches, shared across camera cages,
handles and accessory ecosystems for quick-release mounting. Build a rail
length, a quick-release clamp that grips the dovetail, or a 1/4-20 adapter.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **NATO Rail Section** | `nato_rail_section` | A length of dovetail rail on a base plate, with transverse safety notches across the top and centred mounting holes. |
| **NATO Quick-Release Clamp** | `nato_clamp` | A clamp body with a matching dovetail channel, a flex slit and a cross bolt — tighten to grip any NATO rail. Carries a 1/4-20 face on top. |
| **Rail Adapter (1/4-20)** | `rail_adapter` | A short rail section with a perpendicular back face carrying a horizontal 1/4-20 hole — bridges a NATO device to a 1/4-20 arm. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| NATO Rail | `rail_w` | 21.2 mm | Rail top platform width. |
| NATO Rail | `flank_ang` | 44° | Dovetail flank undercut angle from vertical. |
| NATO Rail | `rail_h` | 6.0 mm | Dovetail block height. |
| NATO Rail | `rail_len` | 50.0 mm | Rail length. |
| NATO Rail | `notch_w` / `notch_count` | 1.5 mm / 3 | Transverse safety notches. |
| NATO Rail | `base_th` | 4.0 mm | Base plate thickness under the dovetail. |
| NATO Rail | `mount_hole_d` | 4.5 mm | Rail mounting hole (M4). |
| Clamp | `clamp_clear` | 0.35 mm | Per-side clamp↔rail fit clearance. |
| Clamp | `wall` | 4.0 mm | Clamp wall / jaw thickness. |
| Clamp | `clamp_bolt_d` | 5.2 mm | Clamp bolt clearance (M5). |
| Adapter Face | `face_th` | 6.0 mm | Perpendicular accessory face thickness. |
| Adapter Face | `face_hole_d` | 6.6 mm | 1/4-20 face hole. |

## The dovetail (why the clamp self-centres)

The rail is a **dovetail** — wider at the bottom than the top because the flanks
undercut at `flank_ang`. The bottom width is
`rail_w + 2·rail_h·tan(flank_ang)`. The clamp mills the same dovetail (grown by
`clamp_clear` per side) as a through-channel; its angled jaws hook under the
undercut. A flex slit lets one jaw open, and a cross bolt pulls it in, so
tightening wedges the rail down into the fixed jaw — a self-centring grip. The
channel is open at both rail ends, so the clamp slides onto a rail and the
cavity always vents to outside.

## Presets

- **Standard NATO Rail (50mm)** — the reference rail with 3 safety notches.
- **Quick-Release Clamp** — the matching clamp at nominal fit clearance.
- **NATO-to-1/4-20 Adapter** — a 40 mm rail with a 1/4-20 back face.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **NATO Rail** (`rail`, *NATO accessory rail*) — the dovetail cross-section,
    defined by `rail_w`, `flank_ang`, `rail_h`, `notch_w`. Any rail, clamp and
    adapter built at the same width and flank angle interoperate.
  - **1/4-20 Accessory Face** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the
    clamp/adapter face hole, defined by `face_hole_d`, for the camera-accessory
    thread.
- **Material awareness:** `tolerance_by_material` is declared — `clamp_clear`
  and the dovetail dimensions are exposed so the grip fit tunes per
  material/printer.
- **Societal benefit:** the NATO rail is an open quick-release standard shared
  across camera cages and accessory ecosystems; on-demand rail sections, clamps
  and adapters let a maker add mounting points anywhere on a rig from stock
  parts and repair a snapped clamp on set.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The rail, clamp jaws and dovetail channel are extruded 2D cross-sections;
  channels are through-slots (vented), notches are open grooves, and every 1/4-20
  pocket is drilled from an open face (vented). Fillets are applied to clean
  blanks before feature cuts and wrapped in try/except. All shipped modes and
  presets render **watertight** in well under 20 s.
