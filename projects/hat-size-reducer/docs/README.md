# Hat Size Reducer

A printable **ribbed C-profile sizing strip** that clips inside a hatband and takes the
hat down a size or two. Generated with **CadQuery** (B-Rep).

Hat sizing arithmetic: one US/UK hat size is 1/8 inch of head *diameter*, which works out
to roughly 10 mm of head *circumference*. `reduction_mm` is stated in circumference, the
way a milliner actually measures, and the strip converts it to radial build-up
(`reduction_mm / 2π`) behind the sweatband.

The strip is struck on the head arc, so it lies flush inside the band rather than chording
across it. Its C cross-section hooks the sweatband's free edges top and bottom — friction
fit, no glue, fully removable. The head side carries vertical ribs, which is what commercial
foam sizing tape approximates: ribs spread the take-up over the skin and vent, so the fit
reads as snug rather than as a hard shelf.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Strip** | `strip` | One sizing strip. |
| **Fitting Pair (two strips)** | `pair` | Two strips laid out flat — the usual fitting, one over each temple. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Strip | `strip_length` | 90.0 mm | 40–200 | Arc length along the head curve. 80–100 mm covers one temple. |
| Strip | `strip_height` | 12.0 mm | 8–30 | Height across the sweatband; match the visible band height. |
| Fit | `reduction_mm` | 10.0 mm | 3–25 | Circumference take-up. ~10 mm = one hat size, ~5 mm = a half size. |
| Fit | `band_t` | 2.2 mm | 1.0–5.0 | Sweatband thickness the C grips; sets grip lip depth. |
| Fit | `head_circ` | 580.0 mm | 480–680 | The hat's current circumference; sets the arc. 580 mm ≈ US 7 1/4 / EU 58. |
| Ribs | `rib_count` | 7 | 0–20 | Vertical comfort ribs. Zero gives a plain smooth strip. |
| Ribs | `rib_depth` | 1.2 mm | 0.4–3.0 | How far each rib stands proud; part of the take-up. |

Two strips share the total reduction: for one full size down with the `pair` mode, set
`reduction_mm` to about 5 mm each rather than 10 mm each.

## Print notes

Print **on the flat end face**, the strip standing on its short radial section — the arc
lies in the build plane and every overhang is a lip under 3 mm, so no supports are needed.
TPU (95A) is the material of choice: it lets the C spring open onto the sweatband and gives
the ribs their compliance. PETG works if the band is stiff leather and you want a hard shim;
PLA is too brittle for the lips at these sections. 0.2 mm layers, 3 perimeters, 20 % infill.
If the strip will not spring on, raise `band_t` one step and reprint rather than prying the
lips. Every mode exports watertight; the `pair` mode returns an assembly of two separate
strips, not a fused body.

## Hyperobject Profile

Domain `wearable`. Two CDG interfaces:

- **`sweatband_clip`** (`custom`, parameters `strip_height`, `band_t`, `strip_length`) —
  the friction-fit C that grips the sweatband. Point-of-attachment hardware, not a sewn
  edge, so it is declared `custom` rather than flange.
- **`head_arc`** (`profile`, parameters `head_circ`, `reduction_mm`) — the arc the strip is
  struck on and the circumference it removes, which is the dimension a hat pattern speaks in.

## Fashion Cabinet bridge

Expected FC consumers: the **bucket hat**, **fedora / felt hat**, and **cap** garments, and
the **hatband / sweatband** notion that carries the finished head measurement.

FC drives `head_circ` from the garment's finished head circumference and `reduction_mm` from
the difference between that and the wearer's measured head — the whole point of the
cartridge is that FC already knows both numbers. `strip_height` follows the sweatband
notion's band height and `band_t` its material thickness.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "hat-size-reducer",
  "linked": true,
  "params_map": {
    "head_circ": "finished_head_circumference_mm",
    "reduction_mm": "(finished_head_circumference_mm - wearer_head_circumference_mm) / 2",
    "strip_height": "sweatband_height_mm",
    "band_t": "sweatband_thickness_mm",
    "strip_length": "finished_head_circumference_mm * 0.155"
  }
}
```

The **`head_arc`** interface is the dimensional handshake FC reads: it names the two params
that carry head circumference and take-up, so a size change on the FC garment resizes the
strip without a human retyping millimetres.

`CERN-OHL-W-2.0`.
