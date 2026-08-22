# Veil Comb

A printable **hair comb whose spine is a veil-gathering bar**. Generated with **CadQuery**
(B-Rep).

Veil attachment is the part of bridal millinery nobody sells a tool for. The tulle of a
birdcage veil, a blusher or a mantilla is gathered onto a plain plastic comb by eye, a few
tacking stitches hold it, and if the fullness comes out uneven the veil is remade. Here the
spine carries a row of **sew slots on a stated pitch**: the tulle between two slots becomes
one pleat, so the gather pitch is a number rather than a guess, and each opening is a *slot*
rather than a hole so the gathering thread can be drawn along it as the pleat is set.

The comb itself follows the real article: 25–40 mm teeth on a 35–50 mm spine, tapering to a
rounded flat tip that parts hair instead of catching it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Veil Comb** | `comb` | One comb. |
| **Comb Pair (wide veil)** | `pair` | Two combs side by side — the standard fitting for a wide veil, one each side of the head. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Gathering Bar | `bar_length` | 44.0 mm | 20–120 | Spine length; the length the veil's gather is compressed into. |
| Gathering Bar | `bar_h` | 7.0 mm | 4–18 | Bar height above the tooth roots; must hold the slots with a rail above and below. |
| Gathering Bar | `bar_t` | 2.4 mm | 1.4–5.0 | Spine thickness. 2.4 mm sits flat against the head. |
| Gather Slots | `slot_count` | 7 | 0–24 | Sew slots down the bar. Each is one anchored gather point. |
| Gather Slots | `slot_pitch` | 5.5 mm | 2.5–20 | Slot centre spacing — the gather pitch. Auto-reduced to fit the bar. |
| Gather Slots | `slot_w` | 1.6 mm | 0.8–4.0 | Slot width along the bar; 1.6 mm passes a millinery needle. |
| Teeth | `teeth` | 7 | 2–24 | Tooth count. Seven on a 44 mm bar matches a stock bridal comb. |
| Teeth | `tooth_len` | 30.0 mm | 8–70 | Tooth length below the bar. Heavy veils want long teeth. |
| Teeth | `tooth_w` | 2.2 mm | 1.2–6.0 | Root width; tapers to ~45 % at the tip. Clamped to 80 % of tooth pitch. |

## Print notes

Print **flat on the bar's back face**, teeth lying in the plane — the whole comb is one
plane of material, so nothing overhangs and no supports are needed. Print the teeth *along*
the layer direction, never across it: a tooth whose layer lines run across its length snaps
the first time it is combed into thick hair.

**PETG** at 0.15 mm layers, 4 perimeters, 40 % infill is the material for a comb that will
be worn once but must not fail on the day. Nylon or PA-CF is better for a comb meant to
outlive several veils. PLA teeth will break. If the comb feels sharp on the scalp, raise
`tooth_w` rather than shortening the teeth — a shorter comb levers out under a veil's
weight.

Every mode exports watertight; the `pair` mode returns an assembly of two separate combs,
not a fused body.

## Hyperobject Profile

Domain `wearable`. Two CDG interfaces:

- **`veil_gather_bar`** (`flange`, parameters `bar_length`, `slot_count`, `slot_pitch`,
  `slot_w`, `bar_t`) — a genuine sewn/gathered edge. The tulle is gathered *along* this bar
  and stitched through the slot row, so the bar length and the slot pitch are exactly the
  dimensions a veil's gather pattern is computed from. This is the FC dimensional handshake.
- **`hair_engagement`** (`custom`, parameters `teeth`, `tooth_len`, `tooth_w`) — the tooth
  row that grips hair. Not a mating geometry with any other part, so `custom`.

## Fashion Cabinet bridge

Expected FC consumers: the **birdcage veil**, **blusher veil**, **cathedral veil** and
**mantilla** garments, and the **veil gather** notion that owns the gather ratio.

The handshake runs on the gather. FC's veil pattern knows the raw tulle width and the
gather ratio, which together give the finished gathered width — that finished width is
`bar_length`, and the number of pleats it is broken into is `slot_count`, with
`slot_pitch = bar_length / (slot_count − 1)`. Get those three to agree and the veil gathers
onto the comb exactly as patterned instead of by eye.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "veil-comb",
  "linked": true,
  "params_map": {
    "bar_length": "veil_gathered_width_mm",
    "slot_count": "veil_pleat_count + 1",
    "slot_pitch": "veil_gathered_width_mm / veil_pleat_count",
    "slot_w": "1.6",
    "bar_t": "2.4",
    "teeth": "round(veil_gathered_width_mm / 6.3)",
    "tooth_len": "30.0",
    "tooth_w": "2.2"
  }
}
```

The sibling **`fascinator-base`** cartridge covers the case where trim sews to a base brim
rather than gathering onto a comb bar; its `comb_slot` interface is sized to accept this
comb's `bar_length` / `bar_t` spine, so a veil comb and a fascinator base from this commons
mate directly.

`CERN-OHL-W-2.0`.
