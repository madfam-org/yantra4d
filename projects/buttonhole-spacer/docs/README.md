# Buttonhole Spacer

A 3D-printed **buttonhole spacing gauge** — generated with **CadQuery** (B-Rep). A graduated
rail and a detented slider that step equal button intervals down a placket, so a shirt front
never ends up with the gap that gapes at the bust.

Part of the **Yantra4D Hyperobjects Commons** (an atelier-tools shelf finding).
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part |
| :--- | :--- |
| **Graduated Rail** | `rail` |
| **Slider** | `slider` |
| **Rail + Slider** | `set` |

`set` is the printable pair — a compound of two separate pieces, laid out flat on one plate.

## Why not the scissoring expander

The classic buttonhole spacer is a lazy-tongs linkage: a dozen slats on a dozen rivets that
expand to divide any distance into equal parts. It is elegant and it prints badly — every
joint is a clearance gamble and a failure point. This is the printable equivalent of the same
arithmetic: set `pitch` to the interval you want, and step the slider down the rail, marking
at each detent. Two pieces, no rivets, no joints to seize.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Dovetail Track (`rail`) and Placket Edge Reference (`profile`). The
  track is a `rail` because the slider rides it as a linear guide; the placket reference is
  a `profile` — the rail is laid along a folded placket edge, not sewn to it.

## Fabrication notes

The rail's dovetail track is a single trapezoidal prism cut the full length and overshooting
both ends, so the slider threads on from either end. Detent scallops are batched into one
compound cutter and subtracted in a single boolean.

The slider's detent tongue is a **compliant** feature: relief slots free it on both sides and
it is thinned from above to a **generous land** (≈45 % of deck thickness, never below
1.2 mm). No knife edges — a thin printed tongue delaminates at the first click. The tongue
relief opens upward, and the slider's throat is open at both ends, so nothing is a sealed
void.

`slide_clr` is the running fit; 0.35 mm suits a well-tuned FDM machine. Raise it to 0.5 mm
if your first slider binds — it is far easier to reprint the small part than the rail.

`CERN-OHL-W-2.0`.

## Fashion Cabinet bridge

Fashion Cabinet garments with a button placket consume this: **button-front shirts and
blouses**, **coat and cardigan fronts**, **waistbands**, and **cuff plackets**. The mating
parameter is `pitch` — FC's pattern piece carries a button count and a placket length, and
`pitch = placket_length / (count − 1)` is exactly what this rail is set to. `rail_len`
couples to that placket length, and `rail_w` to the placket width, so the rail's edge
registers against the folded edge FC's pattern draws.
