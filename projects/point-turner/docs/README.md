# Point Turner

A 3D-printed **collar point turner and seam presser** — generated with **CadQuery** (B-Rep).
One flat blade: a blunt point at one end for pushing out collar, cuff, and lapel corners
without bursting the stitching, and a broad rounded paddle at the other for holding a seam
open under the iron.

Part of the **Yantra4D Hyperobjects Commons** (an atelier-tools shelf finding).
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part |
| :--- | :--- |
| **Full Turner** | `turner` |
| **Pocket Point** | `point` |
| **Both Tools** | `set` |

`point` is a short version at 55 % length — the one that lives in a project bag. `set` lays
both out as a compound of two genuinely separate pieces.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Corner Point (`profile`) and Seam Presser Face (`surface`). The point
  is a working profile pressed into a stitched corner, not a sewn-along edge, so it is a
  `profile` rather than a threading interface.

## Fabrication notes

One planar outline — a symmetric polyline from rounded presser paddle through a waisted grip
to a tapered blade and blunt point — extruded to `tool_t` and then **bevelled on the clean
blank**, before the thumb pockets are cut. Chamfering after a complex cut is the uncatchable
OCCT segfault; this is the whole reason the operation order looks backwards.

The outline is **straight segments only**. Arcs on a mirrored polyline are where these
profiles usually go non-manifold, and the bevel gives the eye the roundness anyway. Thumb
dishes are cut into both faces so the tool is reversible, each cutter overshooting 1 mm out
of the face so the pocket is unambiguously open.

Keep `point_w` blunt — 3 mm by default. A sharp printed point is what goes through the
stitching, which is the exact failure the tool exists to prevent. Prints flat, no supports.

`CERN-OHL-W-2.0`.

## Fashion Cabinet bridge

Fashion Cabinet garments with turned corners consume this: **shirt collars and collar
stands**, **notched and peaked lapels**, **cuffs and plackets**, **welt and flap pockets**,
and any **faced hem corner**. The mating dimension is `point_w` against the corner angle
FC's pattern piece carries — a sharp 45° collar point needs a narrower turner than a blunt
club collar — and `tool_t` couples to the seam allowance FC specifies, since the blade has
to fit inside the turned corner without stretching it.
