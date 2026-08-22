# Hook-and-Loop Tape

A printable analogue of hook-and-loop tape — generated with **CadQuery** (B-Rep).
Two mating strips that peel apart and re-close: the **hook strip** carries a field
of mushroom-headed pins, the **loop strip** carries a waffle grid of thin walls
whose square cells those heads snag on. It stands in for the sewn-on woven tape at
a vest front, a cuff tab, a flap or a pocket.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Both Strips** | `set` | Hook strip and loop strip side by side, ready to print as a pair. |
| **Hook Strip** | `hook_strip` | Base plate + mushroom-pin field. |
| **Loop Strip** | `loop_strip` | Base plate + waffle wall grid. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Strip | `strip_length` | 50 mm | Length along the closure run. 20–120 mm. |
| Strip | `strip_width` | 20 mm | Width across the closure — usually the garment's finished overlap. |
| Strip | `base_t` | 1.2 mm | Flat sewable base plate thickness. |
| Strip | `sew_margin` | 3 mm | Plain border free of pins/walls so the strip can be stitched down. |
| Engagement | `pin_pitch` | 3.5 mm | Pin centre-to-centre spacing; also the waffle cell size. |
| Engagement | `pin_dia` | 1.2 mm | Mushroom stem diameter — thinner peels more easily. |
| Engagement | `head_dia` | 2.0 mm | Mushroom cap diameter; clamped to stay above `pin_dia + 0.4` and below `pin_pitch - 0.6` so heads never merge. |
| Engagement | `pin_h` | 2.0 mm | Pin height above the base, and matching waffle wall height. |

Pin count is capped at **400 features**; past that the effective pitch grows
automatically so the field stays visually identical without blowing the mesh budget.

## Print notes

Print both strips flat on the bed, base down — the mushroom caps are a short
self-supporting overhang at these diameters, and the waffle walls bridge nothing.
**TPU or a flexible PETG** gives the peel-and-re-close behaviour; rigid PLA works
as a one-shot latch but the pins snap rather than flex. Fine layers (0.12 mm) keep
the cap overhang crisp. Prints well in recycled and offcut material
(`recycled_material_toggle` in the profile).

## Fashion Cabinet bridge

The `sew_face` CDG interface (`flange`, from `strip_length` / `strip_width` /
`sew_margin`) is the sewn/set flange for the dimensional handshake — a garment's
finished closure overlap drives it. `engage_field` (`surface`) is the mating side
and only needs to agree between the two strips of one pair.

Suggested FC-side `hardware_ref` (e.g. on `hi-vis-vest`, whose front closure this
cartridge fills):

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "hook-loop-tape",
  "linked": true,
  "params_map": {
    "strip_width": "overlap",
    "strip_length": "tape_width * 2.5",
    "sew_margin": "seam_allowance"
  }
}
```

`CERN-OHL-W-2.0`.
