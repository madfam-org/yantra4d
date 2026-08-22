# Figure Child

A parametric **child dress form** — the small sibling of [`body-form`](../../body-form/docs/README.md),
and the honest way to stage the `kids_baby` garments of the
[Fashion Cabinet](https://github.com/madfam-org/fashion-cabinet) soft-goods commons.
Like its parent it is deliberately an **abstract form, not a figure**: no head, no
face, no arms beyond a shoulder shelf — neutral, correct for pattern work, and
free of the uncanny-valley and representation problems a realistic child body
would carry, which matter more here, not less.

## Why it is a separate cartridge

A child is **not a scaled adult**, and re-lofting `body-form` at child girths
lies in three specific ways this cartridge fixes:

1. **Head-to-body ratio.** An adult stands about 7.5 head-lengths tall; a
   one-year-old about 4, a six-year-old 5.7, a ten-year-old 6.3. The form carries
   no head, but the ratio still governs everything below it: for a given stature
   the child's **torso is proportionally longer and the legs shorter**. Leg length
   is therefore a fraction of stature that *grows* with age, not the fixed adult
   value baked into `body-form`'s Z ladder.
2. **Waist definition.** Small children have essentially none — the toddler belly
   is at or wider than the chest, and a real waist indent only appears around
   five to seven years. `body-form` always cuts a waist; here the indent is
   age-driven and reaches zero under two years, so the toddler silhouette is the
   correct barrel.
3. **Belly projection.** The infant abdomen projects forward, so the depth:width
   ratio at the waist ring is *higher* (a rounder section) in the young and falls
   toward the adult value with age.

## The proportion model

One parameter, **`size_age`** (years, 0.5–10), drives a small age-response
family — waist indent, belly ratio, leg fraction — as linear blends on a single
normalised age, so the family is monotone and has no surprises between presets.

| age | waist indent | belly depth : width | leg : stature |
|----:|-------------:|--------------------:|--------------:|
| 0.5 | 0.00 | 0.92 | 0.34 |
| 2   | 0.13 | 0.89 | 0.36 |
| 4   | 0.31 | 0.85 | 0.39 |
| 8   | 0.67 | 0.76 | 0.44 |
| 10  | 0.85 | 0.72 | 0.47 |

The girths and lengths remain **independently settable ISO-8559 measurements**
and are never overwritten by age: the rings stay authoritative, and `size_age`
sets only the shape responses above plus the derived vertical ladder. The
anchors are standard growth-chart relations for stature-to-leg-length and the
classical head-count proportions; they are **proportion ratios only**, so no
population percentile is implied or claimed.

## How it's built

The same machinery as `body-form`: one **loft through named elliptical
cross-sections** stacked by height, each section's perimeter equal to its
landmark girth via a Ramanujan perimeter fit at a per-landmark depth:width
ratio. The **linear (ruled) loft** is deliberate — it can never bulge wider than
a bounding ring, so every measured ring is dimensionally exact (verified: neck,
chest and hip all measure their girth to within 0.02%).

Watertight throughout (Yantra4D scar tissue respected): a pure additive loft, no
cuts anywhere, so no sealed voids can exist; the neck is closed by a
loft-to-flat frustum (never a sphere pole); the legs start *above* the hip ring
so they are buried inside the seat solid before the union, never kissing it on a
coincident face; the foot blocks overlap the ankle loft on both faces; and there
is no fillet or chamfer after any feature.

## Modes — chosen from what the four garments actually measure

The mode set is not a guess. Reading the `kids_baby` manifests, the four
garments split cleanly by which landmarks they need:

| mode | what it is | serves |
|------|-----------|--------|
| `torso` | neck ring down to the hip ring, capped | `kids-t-shirt`, `school-polo` — they measure only chest / neck / body length / sleeve length |
| `bifurcated` | the torso continued past the hip through a **crotch ring** into two upper-thigh stumps | `baby-bodysuit` — its snap crotch measures `crotch_ext` and `crotch_width`, so it needs a real crotch surface to close under |
| `full_figure` | the legs continued through **knee and ankle rings** to a flat foot block | `baby-sleeper` — it is **footed** and measures `inseam_length`, `ankle_girth` and `foot_length`; staged on thigh stumps it would have nowhere to put its feet |

That footed sleeper is the whole reason this form is **torso + legs** rather than
torso-only. The feet are deliberately blunt rectangular blocks: a modelled toe
would add nothing a sock-foot pattern can use, and it would cost the watertight
guarantee.

## Landmark-ring interfaces (CDG)

The manifest's `hyperobject.cdg_interfaces` expose the measured rings as
`surface` interfaces — `neck_ring`, `chest_ring`, `waist_ring`, `hip_ring`,
`crotch_ring`, `knee_ring`, `ankle_ring` — plus the `shoulder_line` and
`sole_plane` as `profile`s. These are the surfaces a Fashion Cabinet garment's
"dressed form" view wraps its pieces onto.

## Measurements

Drive it with the ISO-8559 girths (mm, full-body circumferences): `neck_girth`,
`chest_girth`, `waist_girth`, `hip_girth`, `thigh_girth`, `knee_girth`,
`ankle_girth`, plus the linear landmarks `back_waist_length`, `shoulder_width`,
`crotch_height`, `inside_leg_length` and `foot_length`. Size presets ship for
6M, 18M, 4Y and 8Y; a made-to-measure set overrides any of them. It renders to
**GLB/GLTF** (the web-3-D format the studio consumes) as well as STL / STEP /
3MF / OBJ for fabrication.

Official visualizer and configurator: **Yantra4D**.
