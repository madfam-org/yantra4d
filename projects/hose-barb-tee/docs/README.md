# Hose Barb Tee

The junction the commons' own tube series never had.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

`pneumatic-barb-port` publishes a barb series sized by tube **inner** diameter — 2 / 3 / 4 mm — and four more cartridges consume it:

`bellows-actuator` · `pneu-net-finger` · `suction-cup-bellows` · `vacuum-manifold-block`

Five objects speak one tube series, and between any two of them there is a length of silicone tube and nothing else. **No tee. No elbow. No reducer. No way to plug one cartridge's barb straight into another's port.** A soft-pneumatic rig with two actuators is therefore a rig with a hand-cut splice in it, and a hand-cut splice is where a demonstration stops being a machine.

This is that missing fitting set, generated from **the same four expressions**, copied unchanged from `pneumatic-barb-port`:

```
stem_r(tid) = max(tid/2, bore/2 + wall)
barb_r(tid) = stem_r(tid) + barb_rise
bore_r(tid) = min(bore/2, stem_r(tid) - 0.6)
ridge_h()   = min(barb_pitch*0.75, barb_rise*3.0 + 0.8)
```

A stem built here at `tube_id = 3` grips the same tube as a port built there at `tube_id = 3`, because both derive from the same expression. Changing one of them without changing the other would fork the series while still calling it one.

## The socket form is the point

All five members of the series publish their barb as a **`profile`**. Under the shipped compatibility rules, `profile ↔ profile` is neither self-mating nor complementary — so **the series is published but not self-mating.** It needs an object that consumes it as a `socket`.

Every mode's first port therefore takes a selectable form:

| Form | What it is |
| :--- | :--- |
| `barb` | A barbed stem, for tube |
| `socket` | A plain socket that receives **another cartridge's barb stem directly**, with no tube between them |
| `push_in` | A parallel **smooth** stem for a commercial one-touch collet fitting — a barb would shred the collet's gripping ring |

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `tee` | Tee | Three ports on one hub: a run through, and a branch |
| `elbow` | Elbow | Two ports at a settable angle, 30–150° |
| `reducer` | Reducer | A straight coupler between two different tube sizes |

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Commons Barb Series Socket** (`socket`, `internal (2 / 3 / 4 mm tube ID)`) — the consuming half the series has never had.
  - **Barb Stem Series** (`profile`, same string) — the publishing half, so the fitting set is a member of its own series.
  - **Push-in Collet Stem** (`profile`, 4 / 6 mm metric pneumatic tube OD).
- **Measured partners: 0 today.** See below — this is a taxonomy fact, not a geometry fact.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — this part carries pressure against a printed wall.
- **License:** CERN-OHL-W-2.0

### Why the measured partner count is zero, said plainly

The wave plan scores this slot at **5 partners** and marks the figure as depending on a taxonomy fix. Running the shipped rules over the live catalog, the honest measured count today is **zero**.

The reason is `normalize_family()`'s treatment of the `internal` prefix. That rule is right: private geometry must never masquerade as a shared standard. But the barb series *is* shared — five cartridges publish it — and it is named `internal (2 / 3 / 4 mm tube ID)` because there was no honest alternative. So the graph cannot see a family that demonstrably exists.

The wave plan proposes a `commons:<series>` namespace to fix exactly this. **That proposal is explicitly an open operator question and has not been ratified**, so it is not landed here and this cartridge does not invent a private variant of it. It declares the string the five existing members declare, character for character. The day the namespace is ruled on, all seven objects join at once — and nothing about this geometry changes.

**The mating is physically real regardless of what the graph can see.** A stem generated here at any `tube_id` fits the same tube as a port generated there at the same `tube_id`, today.

## Printing and using it

Print **standing on a port end**, 4 perimeters or more, 60 % infill or solid. A printed wall around a pressurised passage is porous at the layer lines; the manifest warns below 1.2 mm for that reason, and a slow leak in a soft-robotics rig looks exactly like a weak actuator.

Barb rise is the whole grip: too little and the tube walks off, too much and soft tube tears going on. The manifest warns below 0.4 mm, where the ridge is inside the print's own layer resolution.

### Scope — read this

**Low pressure only.** These fittings are for soft actuators, vacuum and gravity feed — the regime `pneumatic-barb-port` was designed for. They are not rated for anything, they have no burst-pressure figure, and a printed barb under shop-air pressure can release a tube at speed. Do not use them on compressed-air lines, on anything carrying hot fluid, or in any application where a release would injure someone. Leak-test every fitting under water before you trust it, and re-test after any drop.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of the port-form select**, at the **all-min and all-max corners**, and at every declared preset. **74 cases, 74 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `tee` | 8.12 × 4.4 × 6.15 | 108.6 × 24.79 × 55.22 |
| `elbow` | 5.27 × 4.4 × 8.18 | 46.48 × 24.79 × 63.13 |
| `reducer` | 4.4 × 4.4 × 8.12 | 24.8 × 24.79 × 97.74 |

**One defect was found by the sweep, and only the body count could see it.**

`reducer` with the first port set to `socket` returned **two bodies, both perfectly watertight**. The receiving socket bore was being drilled like a passage — from outside the hub, all the way through — so whenever the *opposite* port's stem was narrower than the socket (a 3 mm socket against a 2 mm barb, which is precisely what a reducer is for), the socket bore simply cut the far half of that stem off. Two closed solids, `is_watertight == True` on the whole export, and nothing in the kernel or the render objecting. The socket is now a **bounded counterbore**: it stops short of the far side of the hub by a named distance, `SOCK_STOP_Z`, and the small through-passage carries on alone. The general rule this pays for: **a receiving feature is bounded by the body it sits in, never run like a through feature.**

Everything else held on the first pass because the rules were paid for before the geometry was written:

- **Every stem straddles the hub** by `STEM_OVERLAP`, starting *inside* the hub body rather than at its surface, so every fuse is volumetric at every angle and every tube size.
- **The hub radius is derived from the largest port it must carry**, plus a wall — so a small tube with a large socket can never leave a hub thinner than its own port.
- **Barb ridges are clamped inside their own stem's span** and skipped when they would not fit, rather than drawn past the end. A ridge past the end is a floating collar, and a floating collar is a second body no watertightness check reports.
- **All bores are cut last, and every one of them opens to atmosphere**, so no internal void is ever sealed. Ports are unioned first and passages cut afterwards for the same reason: cutting as it goes would leave a moment where an open pipe end is sealed by the next union.
- **No spheres anywhere.** The hub is a barrel. A sphere's poles are degenerate points where every meridian meets; OCC reports the solid valid and the tessellator splits it in two.
