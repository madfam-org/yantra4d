# Arca-Swiss QR Plate

The **Arca-Swiss** tripod quick-release standard, generated with **CadQuery**
(B-Rep): a **38 mm dovetail** with ~45° flanks that most ball heads, plates and
L-brackets share. Build an Arca QR plate with a 1/4-20 camera slot, a clamp jaw
that grips the dovetail, or an L-bracket for instant portrait mounting.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **QR Plate** | `qr_plate` | The 38 mm dovetail plate (dovetail down) with an elongated 1/4-20 slot on the flat top — a camera bolts on anywhere along the slot. |
| **Arca Clamp** | `arca_clamp` | A clamp block with a matching dovetail channel, a flex slit and a cross bolt, plus a 1/4-20 hole underneath — grips any Arca plate. |
| **L-Bracket** | `l_bracket` | An Arca base plate with a vertical leg rising on one side, the leg's outer face carrying its own Arca dovetail — landscape from the base, portrait from the leg, no re-levelling. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Arca Dovetail | `plate_w` | 38.0 mm | Dovetail platform width (Arca standard). |
| Arca Dovetail | `flank_ang` | 45° | Dovetail flank undercut angle from vertical. |
| Arca Dovetail | `plate_h` | 9.0 mm | Dovetail block height / plate thickness. |
| Plate & Slot | `plate_len` | 60.0 mm | Plate length (`qr_plate`). |
| Plate & Slot | `slot_w` / `slot_len` | 6.6 / 24.0 mm | 1/4-20 camera slot width and travel. |
| Clamp | `clamp_clear` | 0.35 mm | Per-side clamp↔plate fit clearance. |
| Clamp | `wall` | 5.0 mm | Clamp wall / jaw thickness. |
| Clamp | `clamp_bolt_d` | 5.2 mm | Clamp bolt clearance (M5). |
| L-Bracket | `leg_h` / `leg_len` | 55.0 / 40.0 mm | Vertical leg height and base length. |

## The dovetail (why it holds and self-centres)

The Arca plate is a **38 mm dovetail** — wider at the bottom than the top because
the flanks undercut at `flank_ang`. The bottom width is
`plate_w + 2·plate_h·tan(flank_ang)`. The clamp mills the same dovetail (grown by
`clamp_clear` per side) as a through-channel; its angled jaws hook under the
undercut, so tightening the cross bolt wedges the plate down and centres it. The
camera slot and clamp channel are through-features that vent to outside, so no
trapped voids form. The L-bracket puts a second dovetail on a vertical leg, so
rotating the camera 90° into the clamp gives instant portrait framing.

## Presets

- **Standard Arca Plate (38mm)** — the reference plate at spec dimensions.
- **Screw-Knob Clamp** — the matching clamp at nominal fit clearance.
- **Portrait L-Bracket** — a 55 mm leg for instant portrait mounting.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Arca-Swiss Dovetail** (`profile`, *Arca-Swiss 38mm*) — the 38 mm dovetail
    cross-section, defined by `plate_w`, `flank_ang`, `plate_h`. Any plate,
    clamp and L-bracket built at the same width and flank interoperate with the
    Arca-Swiss ecosystem.
  - **1/4-20 Camera Slot** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the plate's
    camera slot, defined by `slot_w`, `slot_len`, for the tripod screw.
- **Material awareness:** `tolerance_by_material` is declared — `clamp_clear`
  and the dovetail dimensions are exposed so the grip fit tunes per
  material/printer.
- **Societal benefit:** the Arca-Swiss 38 mm dovetail is the de-facto open
  tripod quick-release; on-demand plates and clamps let a photographer fit any
  camera or accessory to any head from printed parts and repair a lost plate in
  the field.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Plate, clamp jaws and the L-bracket leg are extruded 2D dovetail
  cross-sections; the 1/4-20 slot (`slot2D`) and clamp channel are through-cuts
  (vented). Fillets are applied to clean blanks before feature cuts and wrapped
  in try/except. All shipped modes and presets render **watertight** in well
  under 20 s.
