# Pneumatic Quick Exhaust

A three-port shuttle valve on the commons' own barb series.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A soft actuator inflates as fast as the supply can push air in, and deflates as slowly as that same air can crawl back out through the whole length of the supply line.

**Retraction speed is the stated weakness of the entire soft-robotics family in this commons.** `bellows-actuator`, `pneu-net-finger` and `suction-cup-bellows` all inflate briskly and all release slowly, and the reason is plumbing rather than material.

A quick-exhaust valve fixes that with three ports and one loose disc:

| State | What the shuttle does | Where the air goes |
| :--- | :--- | :--- |
| **Supply pressurised** | Pushed down, sealing the **exhaust** seat | supply → actuator |
| **Supply vented** | Lifted by the actuator's own pressure, sealing the **supply** seat | actuator → **straight out of a large aperture**, not back up the line |

Nothing about it is clever. It is a cup, a lid and a disc, and it is the difference between an actuator that releases in a second and one that releases in ten.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `valve_body` | Valve Body | The cup: actuator port in the wall, exhaust seat and a shrouded aperture in the floor, open at the top |
| `valve_cap` | Valve Cap | The lid: supply port and the supply seat, on a spigot that enters the cup |
| `shuttle_disc` | Shuttle Disc | The moving element, sized to seal against either seat |

Print all three at the same parameter values. The chamber diameter, chamber height, seat diameter and clearance are shared across every mode precisely so that the three parts are generated as one assembly rather than three objects that happen to look alike.

## Series discipline

Every barb dimension comes from the **same expressions** as `pneumatic-barb-port` and `hose-barb-tee`:

```
stem_r(tid) = max(tid/2, bore/2 + wall)
barb_r(tid) = stem_r(tid) + barb_rise
bore_r(tid) = min(bore/2, stem_r(tid) - 0.6)
```

A supply stem built here at `tube_id = 3` grips the same tube as a port built there at `tube_id = 3`.

The cap's supply port also takes a **socket** form, which receives another cartridge's barb stem directly with no tube between them — the consuming half the series has never had, since a `profile` does not mate a `profile`.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:** **Commons Barb Series Socket** (`socket`), **Barb Stem Series** (`profile`), **Shuttle Chamber** (`socket`, internal — the bore and seat rings the three modes share).
- **Measured partners: 0 today** — the same taxonomy fact as `hose-barb-tee`, not a geometry fact. `normalize_family()` rejects the whole `internal`-prefixed class, correctly, because private geometry must never masquerade as a shared standard. But this series *is* shared by six cartridges and is named `internal (2 / 3 / 4 mm tube ID)` because there is no honest alternative. The `commons:<series>` namespace the wave plan proposes is an **open operator question and is not ratified**, so it is not landed here and this cartridge does not invent a private variant of it. The mating is physically real today regardless of what the graph can see.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — this part holds pressure against a printed wall.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print the **body cup-down** and the **cap disc-down**, 4 perimeters, 60 % infill or solid. Print the **shuttle flat** at the finest layer height you have: it is the only part whose surface finish matters, because it is the only part that has to seal.

`clearance` is the gap between the shuttle and its chamber. The manifest warns below 0.2 mm, and the reason is worth stating plainly: **a stuck shuttle is a valve that has quietly become a plain tee.** It will look installed and do nothing, and the actuator will simply behave as it did before you fitted it.

The shuttle carries three low ribs on one face. They hold the disc off the seat's flat land just enough that the first puff of supply air can get *under* it, which is what makes a light printed shuttle move at all. Fit that face toward the supply seat.

Bed the cap into the body with a smear of silicone rather than glue if you want to be able to open it — the shuttle is the part that will eventually need replacing.

### Scope — read this

**Low pressure only.** This is a valve for soft pneumatics — soft actuators, vacuum, gravity feed. It carries no rating of any kind, it has no burst-pressure figure, and a printed chamber under shop-air pressure can fail suddenly and throw its cap. Do not use it on compressed-air lines, do not use it with hot fluid, and do not use it anywhere a release would injure someone. Leak-test the assembled valve under water before you trust it, and re-test after any drop.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of the supply-form select**, at the **all-min and all-max corners**, and at every declared preset. **72 cases, 72 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `valve_body` | 16.46 × 12.4 × 14.4 | 104.3 × 49.98 × 51.6 |
| `valve_cap` | 12.4 × 12.4 × 8.57 | 50.0 × 49.98 × 55.64 |
| `shuttle_disc` | 9.4 × 9.4 × 2.22 | 39.4 × 39.39 × 2.88 |

**One defect was found by the sweep — and the first fix for it moved the failure instead of removing it, which is the part worth recording.**

At `tube_id = 10` the actuator port's stem radius reaches 5.0 mm, and the stem's lowest generator line landed **exactly** on the chamber floor plane. Tangent surfaces, **one** non-manifold edge, a kernel reporting success, and a mesh that is not watertight. The stem radius comes from the *tube series*, not from this cartridge, so shrinking the port was never an option — it would silently break the series the port belongs to. The chamber height is therefore **raised** to whatever the port needs.

The first version of that fix used a 2.4 mm margin, which put the stem's lowest generator at `FLOOR + 1.2`. The seat ring's top face is at `FLOOR + SEAT_H`, and `SEAT_H` **caps at exactly 1.2**. So the tangency did not go away: it moved from the floor to the seat, and **three** sweep cases now failed the same silent way instead of one — `tube_id=max`, `bore=max` and `wall=max`, all three being the parameters that grow the stem.

The margin is now `2 × SEAT_H_MAX + 2.0 = 4.4 mm`, and every millimetre of it is answering a measured failure. The general rule this pays for: **clearance is measured against the tallest thing in the chamber, not against the chamber's own floor.**

The rest held on the first pass because the rules were paid for before the geometry was written:

- **Both seats are built as solid rings and the bore through them is cut last**, so a seat is never a thin annulus fused to a floor face-to-face.
- **The actuator passage is cut from outside to the chamber axis only** — running it through would open the body into a tube.
- **The shroud windows are counted from the space that survives the end margins**, and skipped entirely when there is none.
- **The three parts are three open or solid shapes**: the cup is open at its top, the cap has a through port, the disc is solid. Nothing seals a void, and a sealed void meshes as two bodies whatever the kernel reports.
- **No spheres.** A pole is a degenerate point where every meridian meets; OCC calls the solid valid and the tessellator splits it.
