# Bucket Lid Adapter

A bored pail or carboy lid, given a bottle finish.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A food-grade bucket is the cheapest large vessel in the world and the one most widely already owned. It stores grain, ferments, carries water, holds a rainwater catch, feeds a drip line. What it cannot do is anything a **port** would let it do: fill, dose, vent, decant or plumb without taking the lid off. The ports that are sold for it are proprietary, regional, and priced as though the bucket were not free.

The commons already speaks both halves of that sentence, and had never joined them:

- **On the vessel side**, `airlock-grommet` and `sharps-lid` both seat into a drilled **carboy/bucket bore**.
- **On the fitting side**, nine cartridges speak **PCO 1881** — `pco-cap`, `jar-adapter`, `bottle-coupler`, `bottle-thread`, `faircap-filter`, `filter-straw`, `bird-feeder`, `pet-dispenser`, `rain-gauge-funnel`.

PCO 1881 is the neck finish on every carbonated-drink PET bottle manufactured anywhere, which means the mating half of this cartridge is already in the waste stream of every settlement on earth. This adapter is the disc that carries the bore interface on its underside and the bottle finish on its face.

## What it is NOT, and why

The wave plan drafted this slot as a **pail-mouth lid**. Two facts ruled that out, and neither is a matter of taste.

1. **The nominal 5 gal / 20 L pail mouth is a (verify) figure with no issuing body.** Pail mouths are a maker's tooling dimension; they vary between suppliers, and no primary source could be confirmed for one during authoring. Writing a plausible number as a dimension is exactly what the commons' invariants forbid.
2. **A ~290 mm disc does not fit a consumer print bed.** A full-mouth lid would be a cartridge almost nobody could print.

The **bore**, by contrast, is a dimension the *user* creates with a hole saw and can measure — and it is the interface the commons already publishes. So this adapter seats **into** the lid rather than replacing it, and every vessel figure it depends on is a slider, not an assertion.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `lid_port` | Lid Port | A flanged bore fitting presenting a **male PCO 1881 neck** on its face. Any PET bottle cap, or the commons' `pco-cap` / `jar-adapter` / `bottle-coupler`, screws straight on |
| `bottle_receiver` | Bottle Receiver | The inverse: a **female PCO 1881 socket** on the same bore flange, so a cut-down PET bottle screws in neck-first as a reservoir, funnel or float |
| `bore_plug` | Bore Plug | A blanking plug on the same bore series, optionally vented for a tube, a thermometer or an airlock stem |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## The bore is yours to measure

`bore_dia` is the hole **you** cut in the lid, and it is the commons' shared carboy/bucket bore series — the same series `airlock-grommet` and `sharps-lid` seat into. Measure the hole saw, not the pail. `lid_thick` is the material the flange clamps through: a moulded HDPE pail lid is typically 2–4 mm, a plywood or barrel lid far more.

`retention` chooses how the stem holds underneath:

- **Snap bead** — a chamfered ring on both flanks, so it prints without support and still pulls back out. Its height is capped so it can never exceed the flange, which would make the part impossible to push through its own bore.
- **Anti-rotation ribs** — six axial ribs that resist twisting when a cap is turned on hard.
- **Plain** — friction and a gasket only.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Carboy / Bucket Bore** (`socket`, `carboy/bucket bore`) — the same string `airlock-grommet` declares, so both objects join the moment the family is named.
  - **PCO 1881 Bottle Finish** (`thread`, `PCO 1881`) — mates all nine live PCO 1881 cartridges.
  - **Grommet / Stem Boss** (`socket`, internal) — the through passage, sized from the bore series.
- **Measured partners:** **9**, every one on the genuine-standard PCO 1881 family, verified by running `normalize_family()` and the shipped geometry rules over the live catalog rather than by reading them.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — this cartridge is used against food, drinking water and ferments, and reground feedstock has unknown provenance.
- **License:** CERN-OHL-W-2.0

### The two edges this does not yet derive

The wave plan scores this slot at **11 partners**, not 9. The missing two are `airlock-grommet` and `sharps-lid`, and they are missing for a taxonomy reason, not a geometry one: `normalize_family()` has no pattern for `carboy/bucket bore`, so the string resolves to no family and the edge cannot derive. That fix (`F5` in the wave plan) is proposed and **not ratified**, so it is not landed here. This cartridge declares the string the existing cartridges already declare, character for character, so all three join in one step the day the family is named.

## Printing and using it

Print **flange-down**, 4 perimeters, 40 % infill or more. The thread then forms on flat layers rather than across an overhang, and the passage wall gets solid perimeters rather than sparse infill.

`clearance` is per-side slop on **both** the bore fit and the printed thread. Raise it for a coarse nozzle or a shrink-prone material; lower it to pull harder onto a gasket.

Use a real gasket. A printed face is not a seal, and this cartridge does not pretend to be one.

### Scope — read this

**This is not a pressure vessel, not a potable-water certification and not a food-safety approval.** A printed wall is porous at the layer lines: it will weep under head pressure long before it fails structurally, and no printable polymer here is certified for food contact by anyone. Treat any liquid that has sat against a printed part as you would treat any other uncertified container, use a real gasket, and do not use this on anything under pressure. If it weeps, thicken the wall and reprint; if it still weeps, the part is telling you it is the wrong part.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of every select**, at the **all-min and all-max corners**, and at every declared preset. **64 cases, 64 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box, judged through the repo's own `mesh_integrity.assess` (raw `trimesh.is_watertight` reports a valid solid as holed, because STL stores every triangle with its own vertices).

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `lid_port` | 31.73 × 31.72 × 14.26 | 100.0 × 99.97 × 34.46 |
| `bottle_receiver` | 32.23 × 32.22 × 14.26 | 100.0 × 99.97 × 34.46 |
| `bore_plug` | 31.73 × 31.72 × 7.4 | 100.0 × 99.97 × 27.6 |

**Three defects were found by the sweep and fixed. None of them raised an exception.**

1. **The thread rib overshot the neck it was supposed to sit on.** A helical rib swept from a profile occupies `pitch × 0.18` *below* its nominal start and `pitch × 0.82` *above* its nominal end — half the profile height, plus the half-pitch the sweep is translated by. The neck was sized to the nominal thread length alone, so the last 2 mm of rib stood in free air: **7 bodies, 1278 non-manifold edges, and a kernel that reported success.** The neck height is now derived *from* the thread's full swept extent. The general rule this pays for: **bound the container by the feature, never the feature by the container.**

2. **The snap bead was two lofts stacked face-to-face.** A cone up to the bead radius and a cone back down, meeting on one shared circular face — a textbook tangential union. It is now a single three-section loft. This is the same failure class as the tangent-torus trap that cost `frog-closure` two rounds of plausible fixes: **union overlaps, never tangents.**

3. **The female thread stopped building above 3.5 turns, and the slider was bounded to the measured ceiling.** At 4.5 turns the union of the rib into a thin annulus returns `NCollection_Sequence::ChangeValue`, or a solid carrying ~1500 non-manifold edges. The cause is upstream of the boolean: a degenerate-radius helix swept with a Frenet frame accumulates profile wobble along its length — at 5.5 turns the *rib alone*, before any union, is already 0.23 mm out of round. `isFrenet=False` and a cut-groove formulation were both tried and are worse (`BRepOffsetAPI_MakePipeShell::MakeSolid`). The male neck survives further; the slider is bounded by the **weaker** of the two so that both modes are honest at every position. This is also the physically generous end of the range: **PCO 1881 is a three-start short-neck finish whose real closures engage barely over one turn.**

The traps that did *not* bite, because the rules were paid for elsewhere in the commons: no fillet is taken on any edge a bore or a thread has touched; no internal void is ever sealed (the ports are through-bores and the unvented plug is solid, not hollow); thread turns are forced to a half-integer so a whole-turn helix cannot close on its own seam; and the flange rim is forced strictly clear of the thread crest so a small bore with a small overhang can never produce two coincident coplanar cylinders.
