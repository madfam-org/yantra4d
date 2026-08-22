# Headband Blank

A printable **fabric-coverable headband arc** — the rigid blank a milliner or costume maker
covers in fabric to build a padded headband. Generated with **CadQuery** (B-Rep).

An adult head measured ear to ear (bitragion) is not a circle. A circular blank pinches at
the temples and gaps at the crown, which is why cheap headbands hurt after an hour. This
blank is struck as an **elliptical half-arc**: `head_width` sets the ear-to-ear span and the
crown rise follows at 0.9 of the half span, the usual head proportion for a band that sits
behind the ears.

The ends taper in **both** the band width and — because the taper is cut off all four Z
faces — the visual thickness of the covered end. That taper is what lets a covered headband
disappear behind the ear instead of ending in a square stub. Each tapered end carries sew
holes bored through the band wall, so the fabric casing is stitched to the blank the way a
milliner actually finishes one, rather than glued.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Headband Blank** | `blank` | One blank. |
| **Nested Pair** | `pair` | Two blanks, the second flipped so the arcs nest on the plate. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Head Arc | `head_width` | 145.0 mm | 110–180 | Ear-to-ear span. 145 mm typical adult, 120–130 mm child. |
| Band | `band_w` | 22.0 mm | 10–45 | Width at the crown — the dimension the casing is cut to. |
| Band | `band_t` | 2.4 mm | 1.2–5.0 | Arc wall thickness. ~2.4 mm in TPU flexes and springs back. |
| Ends | `taper_len` | 32.0 mm | 8–60 | Taper run from each tip; clamped to 35 % of `head_width`. |
| Ends | `tip_w` | 9.0 mm | 4–25 | Band width at the tip; clamped to `band_w − 1.5`. |
| Ends | `sew_holes` | 3 | 0–6 | Stitch holes per tapered end. Zero for a glued or heat-shrink cover. |
| Ends | `hole_dia` | 2.0 mm | 1.0–3.5 | Stitch hole diameter; clamped to keep wall inside `tip_w`. |

## Print notes

Print **flat, the arc lying in the build plane** — the blank sits on one of its Z faces and
every surface is either vertical or a shallow taper, so no supports are needed and the
layer lines run along the band rather than across it (which matters: cross-layer bending is
how a thin arc snaps).

**TPU 95A** is the right material for a band meant to spring onto the head; print it at
0.2 mm layers, 3 perimeters, 25 % infill. **PETG** at the same settings gives a rigid
blank for a structured fascinator-style band. PLA works only above `band_t` 3 mm and will
crack at the tips eventually. If the band grips too hard, raise `head_width` 4 mm rather
than thinning the wall.

Every mode exports watertight; the `pair` mode returns an assembly of two separate blanks,
not a fused body.

## Hyperobject Profile

Domain `wearable`. Two CDG interfaces:

- **`casing_sew_edge`** (`flange`, parameters `band_w`, `band_t`, `tip_w`, `sew_holes`,
  `hole_dia`) — the genuine sewn edge: the fabric casing is stitched along the band through
  these holes, so the band width and thickness are the dimensions the casing pattern is cut
  from. This is the FC dimensional handshake.
- **`head_arc`** (`profile`, parameters `head_width`, `band_t`) — the elliptical arc the
  blank is struck on, which is the dimension a headwear pattern speaks in.

## Fashion Cabinet bridge

Expected FC consumers: the **fabric-covered headband** and **turban band** garments, and
the **headband casing** notion that owns the covering pattern.

FC drives `head_width` from the wearer's measured ear-to-ear span and `band_w` from the
finished casing width minus seam allowance — the casing pattern and the blank must agree or
the fabric either bags or will not close. `band_t` follows the intended stiffness, and
`sew_holes` follows how many anchor stitches the casing pattern calls for at each end.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "headband-blank",
  "linked": true,
  "params_map": {
    "head_width": "wearer_bitragion_mm",
    "band_w": "casing_finished_width_mm",
    "band_t": "blank_stiffness_mm",
    "taper_len": "casing_finished_width_mm * 1.45",
    "tip_w": "casing_finished_width_mm * 0.4",
    "sew_holes": "3",
    "hole_dia": "2.0"
  }
}
```

The **`casing_sew_edge`** interface is the flange FC reads: its parameters name the band
width, tip width and hole pattern the casing must match, so a change to the FC casing
pattern resizes the blank without anyone retyping millimetres.

`CERN-OHL-W-2.0`.
