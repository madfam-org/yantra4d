# Magnetic Pin Dish

A 3D-printed **magnetic pin dish** — generated with **CadQuery** (B-Rep). A shallow bowl
with a disc magnet in a pocket underneath, so dressmaker pins and machine needles jump to it
instead of ending up in the carpet — and a spilled tin gets swept up by waving the dish over
the floor.

Part of the **Yantra4D Hyperobjects Commons** (an atelier-tools shelf finding).
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part |
| :--- | :--- |
| **Single Dish** | `dish` |
| **Twin Dishes** | `twin` |
| **Sharps Cup** | `sharps` |

`twin` prints two — one for live pins, one for the bent ones you should have thrown out.
`sharps` is deeper and narrower: a cup for used machine needles and snapped-off blade
sections, which should never go loose into a bin.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Magnet Pocket (`pocket`) and Pin Bowl (`surface`). The magnet is
  point-fixed hardware dropped into a bore, so it is a `pocket` — not a sewn or threaded
  edge.

## Fabrication notes

The bowl is a **revolved dish profile**, not a cylinder unioned with a dome — that seam
cracks. The magnet pocket is bored **upward into the underside** and overshoots downward, so
it opens at the bottom: it drains, it is never a sealed internal void, and a magnet that
turns out to be the wrong grade can be pushed back out.

Retention is three small compliant nibs at the pocket mouth, each seated so it **overlaps**
the pocket wall and reaches up into the solid boss — a nib that merely kissed the wall
tangentially would weld into a crack. They are 1.1 mm radius posts, not a knife-edge lip,
because a thin printed lip just shears off on the first magnet.

A ring foot keeps the magnet off the table, so the dish does not drag on a steel cutting
table or a machine bed. Set `magnet_dia` and `magnet_t` to the disc you actually have —
20 × 3 mm is the common hardware-bin N35 size and is the default. `floor_t` is the material
left between magnet and bowl floor: thinner pulls harder, 1.6 mm is a good balance.

**Handle N-grade magnets with care** — they pinch hard, they shatter into sharp fragments if
allowed to snap together, and they will wipe a card or a mechanical watch.

`CERN-OHL-W-2.0`.

## Fashion Cabinet bridge

This is a cutting-room safety tool rather than a per-garment finding, so every Fashion
Cabinet pattern that calls for pinning consumes it — but it matters most on FC's
**pin-heavy** constructions: **set-in sleeves**, **gathered and eased seams**, **matched
plaids and stripes**, and any **fitting muslin**, all of which put dozens of loose pins on a
table at once. The mating dimensions are `magnet_dia` and `magnet_t`, which size the pocket
to a hardware disc rather than to a garment; `dish_dia` and `bowl_d` couple to the pin count
FC's construction spec implies for a given garment.
