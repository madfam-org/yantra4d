# Garment Stand

A family of **non-body display solids** — the honest rigid mounts the
[Fashion Cabinet](https://github.com/madfam-org/fashion-cabinet) catalog stages
its accessories and hardware findings on. Where
[`body-form`](../../body-form/docs/README.md) stages what is worn *on* a body,
this cartridge stages what hangs off a body's edges — a hat, a bag, a belt —
and what is not worn at all: a finding, sitting on a plinth as an object.

## Why it lives in Yantra4D

Sixteen of the collection's accessory pieces and eighteen of its hardware
findings have no torso to hang on. A hat on a dress form reads as a decapitated
mannequin; a zipper on one reads as a joke. Both need their own mount, and a
mount is a rigid solid, so it belongs to the CAD kernel.

It is a **hyperobject in the CDG sense** for the same reason `body-form` is: its
value is its *interfaces*. The head block's dome is sized at ISO-8559
`head_girth`, the ring at `waist_girth`, the yoke at `shoulder_width` — the same
measurement vocabulary
(`fashion-cabinet/packages/schemas/body-measurements.schema.json`) that drafts a
flat pattern. A hat drafted for a 570 mm head and a block regenerated at 570 mm
cannot disagree.

## The four mounts, and what each stages

| mode | what it is | garment families it stages |
|------|-----------|---------------------------|
| `head_block` | a milliner's dome + neck cylinder on the post/base, at `head_girth` | hats, caps, bucket hats, balaclavas, hoods |
| `t_rack` | a bust-less shoulder yoke — a gently curved T-bar with rounded tips and a slight fall | bags, totes, aprons, harnesses, scarves, stoles |
| `waist_ring` | a horizontal ring at `waist_girth`, carried off the post on a bridge arm | belts, sashes, waist-hung pouches and chains |
| `mini_plinth` | a small stepped pedestal with a shallow top recess — **no post** | hardware findings: zippers, buckles, cord-locks, D-rings |

## One visual language

All four share the DNA of `body-form`'s `torso_stand`: a plain cylindrical
**post** rooted into a **weighted round base** whose lower edge carries a built
chamfer skirt. Three modes are that post/base under a different top; the plinth
is the base's own idea of itself, with no post. Photograph a hat, a bag, and a
belt from this cartridge side by side and they read as one shop's window — which
is the whole point of authoring a family instead of a prop closet.

## How it's built

- **The dome** is a *revolve* of a super-ellipse half-profile (exponent 2.4 —
  flatter at the crown, fuller at the brow than a hemisphere, which is what a
  real hat block looks like), walked as a closed loop from the axis: neck
  underside → neck wall → up → over the flank → across the crown → back to the
  axis. The crown is **truncated to a small flat**, never taken to a point.
- **The yoke** is two mirrored lofts through elliptical sections stepped along
  the bar, each tapered toward the tip (rounded shoulders) and dropped by a
  quadratic fall (flat where it leaves the post, sloping near the shoulder —
  how a shoulder actually falls). No end caps booleaned on.
- **The ring** is `cq.Solid.makeTorus`, bridged to the post by a plain box arm
  that starts at the post axis and ends past the ring's centreline, so it is
  fully buried in both.
- **The plinth** is a foot, a lofted chamfer frustum, and a straight shaft, with
  one shallow recess cut into the top — the only cut in the file.

## Watertightness

Every mode renders as **one watertight printable solid**, verified through the
real CadQuery sandbox at defaults, at a wide perturbed parameter set, and at the
clamp extremes. Three traps were hit for real while authoring and then designed
out — they are documented in `main.py`'s header, and are worth restating:

1. **The pole singularity.** A revolve profile whose apex touches the axis at a
   single point produces a zero-volume shell riding along the solid. The crown
   flat is the fix, and it is the same loft-to-flat discipline `body-form` uses
   at the neck.
2. **The revolved small circle.** Revolving a tube profile about a distant axis
   degenerates in OCCT (`BRep_API: command not done`). `makeTorus` is the
   documented workaround.
3. **The re-pended loft wire.** `.loft().faces(">Z").wires().toPending()`
   leaves the loft's top wire pending; drawing a fresh coincident wire on it
   extrudes *two* overlapping solids into one invalid compound, which meshes as
   hundreds of shells and only shows up as `is_watertight False` far downstream.
   Both stepped solids here are instead built as two clean solids unioned with a
   real overlap.

Beyond that, the standing rules: every unioned solid **overlaps** its neighbour
(the post roots into the base, the neck sleeves over the post, the post spears
the yoke), the one cutter **overshoots** the face it opens, and nothing is
filleted or chamfered after a boolean — both chamfers are lofted frusta, built
on clean blanks.

## Interfaces (CDG)

The manifest's `hyperobject.cdg_interfaces` expose `head_ring` and `waist_ring`
as `surface` interfaces and the yoke's `shoulder_line` as a `profile`, each
mapped to the ISO-8559 landmark it carries; the shared `post_socket` declares
the post-to-base joint, and `plinth_recess` the staging pocket.

## Measurements

Drive it with `head_girth`, `shoulder_width`, and `waist_girth` (ISO-8559 mm
circumferences and widths), plus the shared stand knobs — `post_dia`,
`post_height`, `base_dia`, `base_th` — and the plinth's own `plinth_w` /
`plinth_d` / `plinth_h`. Presets ship for an adult and a child hat block, a bag
yoke, a belt ring, and a findings plinth. It renders to **GLB/GLTF** (the web-3-D
format the studio consumes) as well as STL / STEP / 3MF / OBJ for fabrication.

Official visualizer and configurator: **Yantra4D**.
