# Battery Pocket Frame

A printable **stiffener frame for an in-garment battery pocket**. Generated with
**CadQuery** (B-Rep).

A soft pocket sewn into a heated jacket or a sensing vest sags around the pack, lets it
rotate, and lets it slide out the mouth — and a lithium pack that rotates chafes its own
leads until one of them opens. This frame is stitched into the pocket through perimeter sew
holes and gives the pack a defined bay: a rounded-rect ring sized to the pack footprint,
with a **retention lip** stepping inward at the mouth and a **depth skirt** the pack
registers against so it cannot rock.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Non-garment sibling: `battery-holder`

The existing **`battery-holder`** cartridge is the **rigid enclosure** cousin — printed
carriers that hold 18650 or AA cells captive with contact slots for bus strips or spring
contacts. They solve different problems:

| | `battery-holder` (sibling) | `battery-pocket-frame` (this one) |
| :--- | :--- | :--- |
| What it is | a structural box | a limp-pocket stiffener |
| Holds | individual cells on a pitch | one finished pack |
| Electrical | contact slots for bus strips | none — the pack keeps its own terminals |
| Mounts by | bolting or bonding into a device | stitching into a pocket bag |
| Sized by | cell diameter and count | `bay_w` × `bay_h` × `bay_t` of the pack |

Building a pack from bare cells? Use `battery-holder`. Fitting a finished pack into a
garment? Use this.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pocket Frame** | `frame` | The stiffener frame alone: ring, retention lip, depth skirt, stitch ring. |
| **Frame + Retainer Strap** | `frame_lid` | Frame plus one thin bar that spans the bay mouth — two bodies. |
| **Full Set (frame + 2 straps)** | `set` | Frame plus two straps, for a pack that needs restraint at both ends. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Battery Bay | `bay_w` | 62.0 mm | 20–140 | Bay opening width. Measure the pack, add ~1 mm. A 10000 mAh bank ≈ 62 mm. |
| Battery Bay | `bay_h` | 92.0 mm | 20–180 | Bay opening height — the long drop-in dimension. 10000 mAh bank ≈ 92 mm. |
| Battery Bay | `bay_t` | 12.0 mm | 4–40 | Pack thickness. Drives the depth skirt and caps the lip height. Slim banks 12–15 mm, pouch cells 6–10 mm. |
| Frame | `frame_w` | 6.0 mm | 4–20 | Rail width around the bay — the land the stitch holes live in. Auto-raised so holes keep wall on both sides. |
| Frame | `frame_t` | 2.4 mm | 1.4–6.0 | Frame plate thickness. |
| Frame | `lip` | 2.0 mm | 0–8 | Retention lip inward step. The pack pushes past it and is then held. **0 gives a plain open frame.** |
| Frame | `corner_r` | 5.0 mm | 1–20 | Bay corner radius; match the pack's own corner. Clamped to a third of the shorter bay dimension. |
| Sewing | `sew_pitch` | 12.0 mm | 5–40 | Perimeter stitch-hole spacing. 10–14 mm suits a mid-weight shell. |
| Sewing | `hole_dia` | 1.8 mm | 1.0–3.0 | Stitch hole diameter. A battery pocket carries real weight — do not go finer. |

## Sizing the bay

Measure the pack, not the marketing spec — banks are consistently a millimetre or two off
their listed size and the moulded seam adds more. Add about **1 mm to each of `bay_w` and
`bay_h`**, and set `bay_t` to the real pack thickness. Then set `lip` to roughly **15–20 %
of `bay_t`**: enough to catch a rounded pack edge, not so much that you have to fight the
pack out one-handed with cold fingers. If the pack has a hard shell and square corners, run
`lip` lower and lean on the depth skirt instead.

## Print notes

Print **flat, lip up** — the skirt walls print as vertical fins below the frame plane, so
orient the frame lip-up and the skirt bridges nothing. No supports. PETG at 0.2 mm layers,
4 perimeters, 30 % infill; the frame is a stiffener, so perimeters matter more than infill.
Avoid PLA next to a warm pack. If the garment is a soft knit, a TPU print at
`frame_t` 3 mm reads more comfortably against the body and still stops the sag.

Every mode exports watertight. The bay is cut clear through the whole stack including the
skirt and overshoots both faces; the lip ring is unioned onto the frame with real Z overlap
before that cut; every fillet is applied to a clean blank, never after a complex cut.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewn Pocket-Bag Edge** (`flange`, internal) — **the sewn flange for the dimensional
    handshake**: the frame rail footprint and stitch ring that land on the pocket bag,
    defined by `bay_w`, `bay_h`, `frame_w`, `sew_pitch`, `hole_dia`.
  - **Battery Bay** (`pocket`, internal) — the pack seat, defined by `bay_w`, `bay_h`,
    `bay_t`, `corner_r`. Driven by the pack, not the garment.
  - **Retention Lip** (`snap`, internal) — the push-past catch at the mouth, defined by
    `lip`, `bay_t`, `frame_t`.

## Fashion Cabinet bridge

Expected FC consumers: **heated jackets, vests and gilets**, **sensing vests** and
**wearable-electronics outerwear**, plus **utility and tactical garments** whose
battery-pocket notion needs a stiffened bay. Downstream of it, `seam-conduit-clip` routes
the harness out of the pocket and `seam-strain-relief` handles the exit through the seam.

FC-side `hardware_ref` block on the battery-pocket notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "battery-pocket-frame",
      "linked": true,
      "params_map": {
        "bay_w": "battery_pack_w_mm + 1.0",
        "bay_h": "battery_pack_h_mm + 1.0",
        "bay_t": "battery_pack_t_mm",
        "frame_w": "min(pocket_seam_allowance_mm * 0.8, 20)",
        "frame_t": "shell_fabric_thickness_mm + 1.6",
        "lip": "battery_pack_t_mm * 0.17",
        "corner_r": "battery_pack_corner_r_mm",
        "sew_pitch": "12.0",
        "hole_dia": "1.8"
      }
    }
  }
}
```

The mating geometry is sized by **`bay_w`, `bay_h` and `frame_w`** — together they set the
frame's outside footprint, which is what FC's pocket-bag pattern piece has to enclose — with
**`sew_pitch` and `hole_dia`** setting the stitch pattern. The pack dimensions
(`bay_w`/`bay_h`/`bay_t`) come from the battery spec; the pocket bag is drafted around the
resulting outside footprint, so this is the one wearables cartridge where hardware drives
the pattern rather than the reverse.

`CERN-OHL-W-2.0`.
