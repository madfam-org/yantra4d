# Frog Closure 盤扣

The **Chinese knotted frog** (盤扣 *pánkòu*) — generated with **CadQuery** (B-Rep). A
knot-button on one side of a closure and a loop on the other, each carried on a sewn
tail. The fastener of the changpao, the qipao, the magua and the tangzhuang, and the
hard good Fashion Cabinet's `changpao` notion (FC-300 rank 299) bridges to **here**.

In cloth a pánkòu is a single bias strip hand-knotted into a ball at one end and bent
into a loop at the other. Printed rigid it becomes a two-part finding sized by `span` —
knot centre to loop centre — the same quantity a robe's finished frog measures.

Part of the AM-fashion capsule. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Frog Pair** | `pair` | Knot half + loop half at their finished span, joined by a snip-off sprue so the closure prints as one body. |
| **Knot Half** | `knot` | Ball + neck + sew tail, alone. |
| **Loop Half** | `loop` | Open C ring + sew tail, alone. |

## Parameters

| Parameter | Default | Notes |
| :--- | :--- | :--- |
| `span` | 56 mm | Knot centre to loop centre — FC's `frog_width` drives this. |
| `knots` | 1 | Complete frogs in one joined print run — FC's `frog_count`. |
| `knot_dia` | 11 mm | Knot-ball diameter. |
| `loop_id` | 12 mm | Loop inner diameter; widened automatically to admit the knot. |
| `gap` | 0.4 mm | Knot-to-loop print clearance. |
| `tail_w` | 7 mm | Sew-tail width — the stitched mating edge. |
| `tail_t` | 2 mm | Tail and ring-wall thickness. |

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Sewn Tail Edge (`flange` — `span`, `tail_w`, `tail_t`) and
  Knot-and-Loop Catch (`snap` — `knot_dia`, `loop_id`, `gap`).
- **Commons license:** CERN-OHL-W-2.0

### The Fashion Cabinet bridge

Fashion Cabinet's `changpao` notion carries
`hardware_ref → { project_slug: "frog-closure", params_map: { span: frog_width, knots: frog_count } }`.
Both mapped keys are real parameters of this cartridge, and `span` drives the
`sew_tail` **flange** interface — the dimensional handshake the
[hardware-ref spec](https://github.com/madfam-org/fashion-cabinet/blob/main/docs/spec/v1/hardware-ref.md)
requires, so the same span flows to the garment's dajin edge and to this finding's
sewn edge.

**Division of labour.** Fashion Cabinet owns *where* the frogs sit — spaced by ARC
LENGTH along the measured 大襟 dajin curve, and how much bias strip each eats in the
BOM. This cartridge owns *what a frog is*: the knot, the loop, and their sew tails.

## Fabrication notes

Two house lessons are load-bearing in this geometry:

- **The knot ball is a flat-capped loft, never a sphere.** A sphere meets its stem at a
  pole, and a pole is a degenerate vertex that turns the union into a non-manifold
  shell. Three ruled sections (flat base → full-diameter equator → flat top) give a
  watertight barrel that also prints capless-of-support and reads as the flattened ball
  a real pánkòu actually is.
- **The loop is a `makeTorus` box-cut to an open C, never a swept `radiusArc`.** At the
  small radii a garment frog uses, swept arcs degenerate outright ("Arc radius is not
  large enough").

The loop's mouth is kept well inside the bore. Cut as wide as the bore, the notch
severs the ring into two arcs that nothing rejoins. The sew tail starts *inside* the
ring's solid material — at the far arc, which the mouth never touches — and runs back
past both horns, so one strip fuses the C into a single watertight body regardless of
how wide the mouth is cut. Starting it at the near rim instead leaves the horns joined
only through the arc and the tail bridging nothing, which is how this part first
rendered as two bodies.

### The tangential-union trap (the lesson worth carrying)

The loop's tail is built inline rather than through `_tail`, because it must **straddle
the ring's tube in Z**. The tube spans `z ∈ [z_mid ± ring_w/2] = [0, ring_w]`; a plain
tail spans `z ∈ [0, tail_t]`. Whenever `ring_w == tail_t` — which the defaults very
nearly hit and `knot_dia=min` hit exactly — those two spans are **identical**, so the
tail's top and bottom faces are coplanar with the tube's extremes and OCC fuses them
tangentially into an open shell.

This is worth stating plainly because the symptom pointed somewhere else entirely: the
failing case was labelled `knot_dia=min(5.0)`, yet `build_loop` uses `knot_dia` for
nothing but the mouth width. The knot size was a red herring; `ring_w` merely happened
to equal `tail_t` at that setting. Bisecting the booleans one at a time (torus → mouth
cut → tail → union) is what located it: every piece was watertight alone, and only the
final union opened. Extending the tail slightly past the tube on both sides makes the
intersection volumetric for every combination of `ring_w` and `tail_t`.

`tail_w` is separately capped against the **final** `loop_id` and `ring_w`, which is why
that clamp sits last in the block: `loop_id` is adjusted twice further up, and capping
against the earlier value lets a max-width tail outgrow the ring it mounts.

In `pair` mode the two halves are joined by a thin sprue at their tail ends, the way a
printed findings card holds its pieces until they are cut apart: the part is one
watertight solid, and snips into a working two-part closure.

## Related cartridges

- `epaulette-board` — the other rigid AM-fashion finding sized by a garment dimension.
- `toggle`, `hook-and-eye`, `sew-on-snap` — the wearables-campaign closure family this
  cartridge joins.
