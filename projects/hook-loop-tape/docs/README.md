# Hook-and-Loop Tape

A printable analogue of hook-and-loop tape — generated with **CadQuery** (B-Rep).
Two mating strips that peel apart and re-close: the **hook strip** carries a field
of mushroom-headed pins, the **loop strip** carries a waffle grid of thin walls
whose square cells those heads snag on. It stands in for the sewn-on woven tape at
a vest front, a cuff tab, a flap or a pocket.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

Manifest labels ship in **en / es / fr / pt**.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pair** | `set` | Hook strip and loop strip side by side, joined by two snip-off sprue rails so the pair prints as **one body**. |
| **Hook Strip** | `hook_strip` | Base plate + mushroom-pin field. |
| **Loop Strip** | `loop_strip` | Base plate + waffle wall grid. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Strip | `strip_length` | 50 mm | 20–120 | Length along the closure run. |
| Strip | `strip_width` | 20 mm | 10–120 | Width across the closure. Overridden by `overlap_mm` when that is non-zero. |
| Strip | `overlap_mm` | 0 mm | 0–120 | **The Fashion Cabinet handshake.** The garment's *finished* closure overlap; drives the strip width. `0` = not garment-driven. |
| Strip | `base_t` | 1.2 mm | 0.8–2.0 | Flat sewable base plate thickness. |
| Strip | `sew_margin` | 3 mm | 2–6 | Plain border free of pins/walls so the strip can be stitched down. |
| Engagement | `pin_pitch` | 3.5 mm | 2.5–6.0 | Pin centre-to-centre spacing; also the waffle cell size. Opened automatically when the head plus its clearance will not fit a cell. |
| Engagement | `pin_dia` | 1.2 mm | 0.8–2.0 | Mushroom stem diameter — thinner peels more easily. |
| Engagement | `head_dia` | 2.0 mm | 1.2–3.0 | Mushroom cap diameter. Exposed on the loop strip too, because the cell opening is sized to admit it. |
| Engagement | `pin_h` | 2.0 mm | 1.0–4.0 | Pin height above the base, and matching waffle wall height. |
| Engagement | `tolerance` | 0.15 mm | 0.05–0.6 | Print clearance between a head and the cell it drops into. |

Pin count is capped at **400 features**; past that the effective pitch grows
automatically so the field stays visually identical without blowing the mesh budget.

### `overlap_mm` — the garment drives the strip

A closure has one authoritative number: the **finished overlap** the two halves
carry across each other. That is what a vest front, a placket or a cuff tab
measures, and the tape has to span it. `overlap_mm` is that number, and when it is
set it *drives* `strip_width` rather than sitting beside it as a second,
contradictory width. `0` means "not garment-driven" — the strip width is used
exactly as given, which is how every existing Fashion Cabinet notion that maps
`strip_width` directly keeps behaving unchanged.

`strip_width`'s upper bound is **120 mm** so that the widest overlap a Fashion
Cabinet garment can ask for (the `hi-vis-vest` front, up to 110 mm) is
representable instead of being silently clamped. That widening also un-clamps two
bridges that were already live: `dog-coat` maps `tape_width` (up to 70 mm) and
`hook-loop-closure` maps `strip_width` (up to 60 mm), and both used to be quietly
cut back to the old 50 mm ceiling.

### `tolerance` — the clearance that makes the pair a pair

`tolerance` is the print clearance between a mushroom head and the cell it drops
into, and it is load-bearing rather than decorative. The loop strip's wall is
thinned — and the pitch opened if that is not enough — so that

```
cell opening = pitch − wall_t  ≥  head_dia + 2 · tolerance
```

always holds, with the wall never thinner than one 0.4 mm nozzle trace. That is
what makes `material_awareness.tolerance_by_material` a claim the geometry
actually honours: TPU squashes under the nozzle and prints its walls fat, so it
wants 0.3–0.4 mm; rigid PLA wants 0.1–0.15 mm. The head diameter is the visible
feature, so when a setting is impossible the *pitch* opens — the head is never
shrunk and the clearance is never eaten.

## Print notes

Print both strips flat on the bed, base down — the mushroom caps are a short
self-supporting overhang at these diameters, and the waffle walls bridge nothing.
**TPU (95A) or a flexible PETG** gives the peel-and-re-close behaviour: a flexible
filament lets the stems bend out of the cell instead of snapping, which is what
makes the closure reusable. Rigid PLA works as a one-shot latch but the pins break
rather than flex. Fine layers (0.12 mm) keep the cap overhang crisp; run flexible
filament slowly (< 25 mm/s) with retraction near zero. Recycled and offcut flexible
filament prints this part well — there are no fine tolerances outside the
engagement pair (`recycled_material_toggle` in the profile).

In `set` mode the two strips are joined by two thin sprue rails at the base, the
way a printed findings card holds its pieces until they are cut apart. Snip them
with flush cutters. Each rail buries about a millimetre into **both** base plates
so the fuse is volumetric, and each is deliberately *thinner* than the base plate —
partly so it snips cleanly, and partly so its top face can never land coplanar with
the plate's top face, which is the tangential-union trap that opens an OCC fuse into
a shell. Without the rails the pair exported as two disjoint solids, which is the
RFC 0038 §7 body-count failure this cartridge originally shipped with: every
`set` render was watertight and every one of them was two bodies.

## Hyperobject profile

- **Domain:** wearable
- **CDG interfaces:** Sew Face (`flange` — `strip_length`, `strip_width`,
  `overlap_mm`, `sew_margin`) and Engagement Field (`surface` — `pin_pitch`,
  `pin_dia`, `head_dia`, `pin_h`, `tolerance`).
- **Commons license:** `CERN-OHL-W-2.0`

## The Fashion Cabinet bridge

`hi-vis-vest` (FC-100 rank #89) is the garment this cartridge was authored for: a
breakaway hook-and-loop centre-front closure, and Fashion Cabinet's only
`hardware_ref` that could not be linked. It carries

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "hook-loop-tape",
  "params_map": { "overlap_mm": "overlap" }
}
```

`overlap_mm` is now a real parameter of this cartridge and it drives the `sew_face`
**flange** interface — the dimensional handshake the
[hardware-ref spec](https://github.com/madfam-org/fashion-cabinet/blob/main/docs/spec/v1/hardware-ref.md)
requires — so the vest's centre-front overlap flows straight into the tape that
fills it. The `hivis_vest_front` preset is that garment's default configuration
(`overlap` 60 mm). Flipping `linked` to `true` is Fashion Cabinet's edit to make.

Other Fashion Cabinet notions already bridge here through the plain strip
dimensions (`boot-shaper-sleeve`, `boxing-fight-short`, `dog-coat`,
`hook-loop-closure`, `seated-wear-trouser`, `side-opening-trousers`,
`wrap-recovery-top`); none of their mapped keys changed.

**Division of labour.** Fashion Cabinet owns *where* the tape sits and how long a
run each closure eats. This cartridge owns *what the tape is*: the base, the pins,
the cells, and the clearance between them.

## Related cartridges

- `frog-closure`, `toggle`, `hook-and-eye`, `sew-on-snap` — the wearables-campaign
  closure family this cartridge joins.
- `tpu-scale-mail`, `tpu-chainmail-panel` — the other flexible-filament wearables.
