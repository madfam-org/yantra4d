# Body Form

A parametric **dress form** (tailor's torso) — the mannequin the
[Fashion Cabinet](https://github.com/madfam-org/fashion-cabinet) soft-goods
commons drapes its patterns onto. Deliberately an **abstract form, not a figure**:
neutral, historically correct for pattern work, and free of the uncanny-valley
and representation problems a realistic human body would carry.

## Why it lives in Yantra4D

The body is a rigid solid, so it belongs to the CAD kernel — and it is a
**hyperobject in the exact CDG sense**: its value is its *interfaces*, the
neck / shoulder / bust / waist / hip **landmark rings**. Each ring's girth is an
ISO-8559 body measurement, so the *same numbers* that draft a flat pattern in
Fashion Cabinet also size this solid. That shared measurement contract
(`fashion-cabinet/packages/schemas/body-measurements.schema.json`) is the seam:
a garment edge wraps to the ring that carries its measurement, and because both
sides speak one vocabulary, the body and the garment can never disagree.

## How it's built

One **loft through named elliptical cross-sections** stacked by height. Each
section's perimeter equals its landmark girth — girth → ellipse `(width, depth)`
via a Ramanujan perimeter fit at a per-landmark depth:width ratio. A **linear
(ruled) loft** is used deliberately: it can never bulge wider than a bounding
ring, so every measured ring is dimensionally exact (verified: hip / waist /
bust / chest / neck all measure their girth to <0.2%). A B-spline loft would
overshoot at fast transitions (shoulder→neck) and break that guarantee.

Watertight throughout (Yantra4D scar tissue respected): a pure additive loft, no
cuts, no fillets after features; the neck is closed by a loft-to-flat frustum
(never a sphere pole); the stand post is a solid cylinder rooted into a solid
base and up through the form (no floating base, no trapped cavity).

## Modes

| mode | what it is |
|------|-----------|
| `torso` | the bare dress form, neck ring down to the hip ring, capped |
| `torso_stand` | the torso on a neck post + weighted round base — a usable stand |
| `bifurcated` | the torso continued past the hip into two upper-thigh stumps (a trouser form) for bottoms/one-pieces |

## Landmark-ring interfaces (CDG)

The manifest's `hyperobject.cdg_interfaces` expose the measured rings as
`surface` interfaces (plus the shoulder line as a `profile`), each mapped to the
ISO-8559 landmark it carries: `neck_ring`, `bust_ring`, `chest_ring`,
`waist_ring`, `hip_ring`, `shoulder_line`. These are the surfaces a Fashion
Cabinet garment's Tier-1 "dressed form" view wraps its pieces onto.

## Measurements

Drive it with the ISO-8559 girths (mm, full-body circumferences): `neck_girth`,
`chest_girth`, `bust_girth`, `waist_girth`, `hip_girth`, plus `back_waist_length`
(vertical proportioning), `shoulder_width`, and `thigh_girth` (bifurcated). Size
presets ship for women's M, men's M, and a 6-year child; a made-to-measure set
overrides any of them. It renders to **GLB/GLTF** (the web-3-D format the studio
consumes) as well as STL / STEP / 3MF / OBJ for fabrication.

Official visualizer and configurator: **Yantra4D**.
