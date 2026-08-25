# Sharps Container Lid Adapter

Turns an ordinary threaded jar into a one-way sharps container.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A used needle is the most dangerous object in a small clinic. The engineering answer has been settled for decades — a rigid, puncture-resistant container that admits sharps and does not give them back — and it is one of the few safety interventions whose effectiveness is not seriously disputed.

What is not settled is **availability**. Purpose-made containers are a recurring purchase in hard currency. When a clinic's supply lapses, the substitute is not nothing: it is a soft drink bottle or a tin with an open mouth. That is *worse than useless*, because an open container can be reached into, it spills when knocked over, and it invites the recapping that causes most needlestick injuries in the first place.

**The scarce component is never the vessel. It is the lid.** Jars are everywhere; the one-way lid is not. This cartridge supplies the part that is actually missing.

## What "one-way" means, mechanically

| Feature | What it does |
| :--- | :--- |
| **Entry slot** | passes a syringe hub, does not pass a hand |
| **Sprung baffle** | admits from above, closes behind the drop — nothing can be fished back out, and the contents do not pour if the jar is knocked |
| **Permanent closure** | once seated, destroyed rather than reopened |

The closure is deliberately one-way. A sharps container that *can* be reopened for one more needle will be, and the whole chain of custody from clinic to incinerator depends on it staying shut.

### The slot is sized on the hub, not the needle

A needle arrives **attached to a syringe**. A slot sized to a bare cannula is unusable in practice, so the floor is the Luer hub — nominal Ø 7.5 mm — plus slop, adjusted for the largest gauge the container must accept.

| | Value |
| :--- | ---: |
| Luer hub nominal Ø | 7.5 mm |
| Slot floor | hub + 1.5 mm + ½ cannula Ø |
| Slot ceiling (hard) | **22 mm** |

The 22 mm ceiling is enforced in `main.py` regardless of what the slider says: above it an adult finger enters easily and the container stops being one-way in the only sense that matters. The manifest additionally warns above 16 mm.

| Gauge | Cannula Ø |
| :--- | ---: |
| 14G | 2.11 mm |
| 16G | 1.65 mm |
| 18G | 1.27 mm |
| 21G | 0.82 mm |
| 23G | 0.64 mm |
| 25G | 0.51 mm |
| 30G | 0.31 mm |

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `lid` | Threaded Lid | CadQuery B-Rep | `main.py` |
| `baffle` | One-Way Baffle | CadQuery B-Rep | `main.py` |
| `closure` | Permanent Closure | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

The baffle is printed as **one piece with a living hinge**, not as two parts and a pin. A pin joint inside a container full of used needles is a part that can be pulled apart — precisely the failure the container exists to prevent.

## Distinct from `sharps-lid`

The commons already publishes a `sharps-lid` cartridge. **These do not interchange, and neither supersedes the other.**

| | `sharps-lid` | `sharps-lid-adapter` (this) |
| :--- | :--- | :--- |
| Attachment | friction fit on a plain bore | **threaded** jar finish |
| Vessel | bucket, carboy | jar |
| Interface | shared vessel-bore series | jar CT thread series |

A clinic with buckets wants the first; a clinic with jars wants this one. They sit alongside each other deliberately.

## Reuses two published interfaces

Nothing here is a new standard. The cartridge is a **recombination** of two interfaces the commons already carries:

- The thread lands on the **jar CT finishes** that `jar-adapter`, `jar-rack` and `spice-jar` already encode — same helical rib convention, same `half_turns` guard.
- The slot is keyed to the **needle-gauge series** the `needle-gauge` cartridge publishes.

| Finish | Thread major Ø | Pitch |
| :--- | ---: | ---: |
| 63-400 | 63.0 mm | 4.23 mm |
| 70-400 | 70.0 mm | 4.23 mm |
| 89-400 | 89.0 mm | 4.23 mm |

("-400" is the GPI finish code for a shallow single-lead continuous thread; the number before it is the nominal thread OD in millimetres.)

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Jar CT Thread** (`thread`, 63-400 / 70-400 / 89-400) — compatible with `jar-adapter`, `jar-rack`, `spice-jar`, `bottle-thread`.
  - **Sharps Entry Slot** (`pocket`, Luer hub floor, 22 mm hard ceiling) — compatible with `needle-gauge`, `sharps-lid`.
  - **One-Way Baffle Seat** (`socket`, internal).
  - **Permanent Closure Bead** (`snap`, internal — opens only by destruction).
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — see below.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print the lid **skirt-down**, 4+ perimeters, **60 % or higher infill**. This is a puncture barrier, not a cosmetic shell; the manifest floors the wall at 2 mm and warns below 3 mm. Sparse infill under a thin top is exactly what a dropped needle punches through.

Use **PETG** or **ABS/ASA**. Avoid PLA, which is brittle and shatters rather than resisting a puncture, and which softens in a hot vehicle during transport to disposal.

**Do not use recycled or unknown-provenance filament**, which is why `recycled_material_toggle` is off in the manifest. Layer adhesion is the whole mechanical property being relied on here, and reground filament has unpredictable interlayer strength.

Fill to **no more than three-quarters**. An overfull sharps container is the second most common cause of needlestick after recapping — the contents rise into the slot and are contacted on the next deposit.

## Scope and limitations — read this before use

This is **printable geometry published as a commons object. It is not a certified medical device**, and it must not be presented as one.

- Printed containers are **not tested or certified** to the standards that govern commercial sharps containers (puncture resistance, drop, leak, and closure-integrity testing under schemes such as ISO 23907 or national equivalents). No claim of compliance is made or implied.
- Where certified containers **are** available and affordable, use them. This cartridge addresses the situation where the realistic alternative is an open bottle, not the situation where a proper container is on the shelf.
- **Sharps disposal is regulated** in most jurisdictions — how waste is contained, labelled, stored, transported and destroyed. Local rules govern, and using a printed container may not satisfy them. Check before adopting this in any clinical setting.
- **Label it.** An unlabelled container of used needles is a hazard to whoever handles it next. The biohazard symbol and the contents should be marked externally.
- Nothing here changes the underlying practice: **do not recap needles**, dispose at the point of use, and never reach into a container.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode, plus all three jar finishes, all seven needle gauges, both baffle states and all three lock styles — **47/47**, each `is_watertight == True` with `body_count == 1`, on the first authoring pass.

That clean first pass is not luck; it is the three defects found in `milpa-seed-plate`, `graft-clip` and `hive-frame-spacer` earlier in this same batch, applied as rules before the geometry was written:

- **Every cut is bounded inside the blank that must contain it**, with a full margin. The entry slot's half-length is capped at `bore_r − wall × 1.5` so it can never reach the skirt and cut the lid open; the closure's grip flutes are bounded inside the cap wall; the baffle's three kerfs are bounded inside the disk.
- **Every added feature overlaps the material it grows from**, never touching it face-to-face. The retaining bead is unioned into the skirt, the thread rib's root is pushed *into* the wall by `overlap`, and the closure's catch ring shares the cap bore.
- **No fillet is taken on any edge a slot or bore has touched.** OCC blends such arcs without raising and returns a non-watertight solid — the failure that cost the most to find in `graft-clip`.
- **The baffle's hinge groove leaves a stated ligament** (`t − hinge_lig`, `hinge_lig = t × 0.45`) rather than a depth chosen independently of the thickness it cuts into. That is the `graft-clip` hinge defect, avoided by construction.
- **`half_turns()` guards the thread sweep.** A whole number of turns produces a null sweep in OCC because the helix closes on itself; the nearest lower half-integer is used, the same guard the published `jar-adapter` carries.
