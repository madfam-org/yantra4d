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
base and up through the form (no floating base, no trapped cavity). The full
legs and the arm stubs follow the same rule: each starts at a wire placed *inside*
the solid it joins — the leg root sits at the hip ring, well above the crotch and
buried in the seat; the arm-stub root sits inboard of the shoulder shelf — so
every union is a volumetric **overlap**, never the coplanar touch that cracks a
boolean. Both close on the loft's own flat end cap.

## Modes

| mode | what it is |
|------|-----------|
| `torso` | the bare dress form, neck ring down to the hip ring, capped |
| `torso_stand` | the torso on a neck post + weighted round base — a usable stand |
| `bifurcated` | the torso continued past the hip into two upper-thigh stumps (a trouser form) for bottoms/one-pieces |
| `figure` | the full figure, shoulders to floor — the torso with a shoulder cap and a short upper-arm stub each side, and the hip continued through thigh / knee / ankle rings to close at the ankles. The form dresses/robes/outerwear/tailoring are cut for |
| `legs` | the lower body alone, waist ring through hip / thigh / knee / ankle — a trouser and skirt form for bottoms, skirts and denim |

### `figure` — shoulders to floor

The whole point is that a floor-length garment finally reads as one. Two things
extend the torso:

- **The legs.** Each leg is one continuous ruled loft whose stations are
  hip root → crotch → **thigh** → mid-thigh taper → **knee** → calf swell →
  **ankle**, the three starred rings being the measured ISO-8559 girths. Because
  the root wire is at the hip ring — inside the seat solid — the two legs and the
  torso fuse into one printable body through the seat, and the inner-thigh line
  falls out of the loft rather than out of a cut.
- **The shoulder cap + arm stubs.** The torso loft already carries a shoulder
  shelf; the cap widens it to the measured `shoulder_width` with a shallow
  three-wire loft, and a short lofted cone roots into that shelf on each side,
  rotated outboard and tilted ~14° down so it follows a real shoulder slope. The
  stub is deliberately short — this is a dress form, not a figure — but it is
  enough that a tailored shoulder, a jacket head, or a raglan has something to
  hang from instead of falling off a bare bust.

### `legs` — waist to ankle

The same leg lofts, mounted on a short waist→hip block instead of a torso. The
block is closed flat at the waist by the loft's end cap, and it is what connects
the two legs into a single solid: this is one trouser form, not a pair of
detached legs. `bifurcated` proved the split; `legs` carries it to the floor.

### Leg and arm parameters

`figure` and `legs` add the lower-body landmarks: `thigh_girth` (already shipped
for `bifurcated`), `knee_girth`, `ankle_girth`, and `inside_leg_length` — the
crotch→floor measurement, which is what actually sets the figure's height rather
than any proportion guessed off the torso. `figure` additionally takes
`upper_arm_girth` and `arm_stub_length`. Manifest constraints keep the leg
tapering (knee ≤ 0.92 × thigh, ankle ≤ 0.92 × knee); the script clamps to the
same rule, so an out-of-order set still renders a well-posed solid.

## Landmark-ring interfaces (CDG)

The manifest's `hyperobject.cdg_interfaces` expose the measured rings as
`surface` interfaces (plus the shoulder line as a `profile`), each mapped to the
ISO-8559 landmark it carries: `neck_ring`, `bust_ring`, `chest_ring`,
`waist_ring`, `hip_ring`, `shoulder_line`, plus the lower-body and arm rings the
full-length modes expose — `thigh_ring`, `knee_ring`, `ankle_ring`,
`upper_arm_ring`. These are the surfaces a Fashion Cabinet garment's Tier-1
"dressed form" view wraps its pieces onto: a trouser hem wraps the ankle ring the
same way a neckline wraps the neck ring.

## Measurements

Drive it with the ISO-8559 girths (mm, full-body circumferences): `neck_girth`,
`chest_girth`, `bust_girth`, `waist_girth`, `hip_girth`, plus `back_waist_length`
(vertical proportioning), `shoulder_width`, and `thigh_girth` (bifurcated,
figure, legs). The full-length modes add `knee_girth`, `ankle_girth`,
`inside_leg_length`, `upper_arm_girth`, and `arm_stub_length`. Size
presets ship for women's M, men's M, and a 6-year child; a made-to-measure set
overrides any of them. It renders to **GLB/GLTF** (the web-3-D format the studio
consumes) as well as STL / STEP / 3MF / OBJ for fabrication.

Official visualizer and configurator: **Yantra4D**.
