# Pattern Weight

A 3D-printed **stackable tailor's pattern weight** — generated with **CadQuery** (B-Rep).
The wide, low disc that pins a paper pattern to cloth without a single pin hole, so slippery
silks, knits, and anything that shows a pin mark get cut on the true grain.

Part of the **Yantra4D Hyperobjects Commons** (an atelier-tools shelf finding).
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part |
| :--- | :--- |
| **Single Weight** | `weight` |
| **Stacked Pair** | `stack` |
| **Set of Four** | `set` |

`stack` shows the registration working: the lower weight's boss sits inside the upper
weight's socket, which is how a dozen of these store in a column instead of sliding off the
shelf. `set` is a four-up plate layout.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Stacking Register (`socket`) and Table Face (`surface`). The register
  is a point-fitted boss-in-socket, not a sewn edge, so it is a `socket`.

## Fabrication notes

The rim chamfer is applied to a **clean blank before any cut** — chamfering after the recess
and socket are cut is the uncatchable OCCT segfault. The stacking boss is formed by cutting
a moat around a raised land rather than unioning a separate disc onto the top face, so there
is no coplanar seam to crack. The finger recess opens upward and the stacking socket opens
downward: nothing here is a sealed internal void.

### Heavy infill

This part only works if it is heavy — a hollow print slides and defeats the point. Print it
**solid, or at 90–100 % infill**, and prefer the densest material you have: PETG and PLA are
about 1.25 g/cm³, so the 62 mm default at 16 mm tall lands near 48 g. If your slicer supports
it, the better move is a **pause-and-insert**: print to the top of the stacking socket, drop
in steel shot, washers, coins, or a slug of lead-free sinker, and resume. `weight_h` is the
parameter to raise for mass; widening `weight_dia` mostly adds footprint, not grip.

`CERN-OHL-W-2.0`.

## Fashion Cabinet bridge

Every Fashion Cabinet garment reaches the cutting table, so this is a shelf-wide tool rather
than a per-garment one — but it earns its keep specifically on FC's **bias-cut** pieces
(slip dresses, cowl-neck tops), **knit** blocks, and any **napped or coated fabric**
spec where a pin hole is permanent. The mating dimensions are `weight_dia` and `weight_h`,
which FC's cutting-layout module reads to place weights along a pattern edge, and
`boss_h` + `stack_clear`, which fix the storage column height for a given weight count.
