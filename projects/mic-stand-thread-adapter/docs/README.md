# Mic Stand Thread Adapter

The three stand threads, in every combination.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

Every stand, boom, clamp, spigot, shockmount and tripod head on earth terminates in one of three threads:

| Thread | Major Ø | Pitch | Where it lives |
| :--- | ---: | ---: | :--- |
| **5/8"-27** | 15.875 mm | 0.941 mm | Microphone stands, grip spigots |
| **3/8"-16** | 9.525 mm | 1.588 mm | European stands, small tripod heads |
| **1/4"-20 UNC** | 6.350 mm | 1.270 mm | Cameras, accessory shoes, everything small |

None of them mates any other, all three turn up in the same rack of gear, and the adapter between any two is the most-lost object in a live-sound or camera bag.

This one cartridge closes **two one-member families** and joins the largest family in the commons:

- `mic-thread-5/8-27` — one member, `mic-clip`
- `unc-3/8-16` — one member, `camera-quarter-twenty`
- `unc-1/4-20` — the commons' biggest standard family

**Each end takes an independent thread selection**, so all nine combinations of the three threads come out of one file, in three body styles.

### A note on 3/8"-16, said plainly

The European stand thread is **3/8 BSW** (Whitworth, 55° flank) and the American one is **3/8"-16 UNC** (60°). Both are 16 TPI on the same major diameter, and **a printed thread does not resolve the flank-angle difference.** This cartridge builds one 16-TPI form and says so, rather than claiming a precision it does not have.

## The 3.5-turn ceiling, and why the plain register exists

The commons' inlined thread primitive — a trapezoidal profile swept along a degenerate-radius helix with a Frenet frame — is **reliable to 3.5 turns and unreliable beyond it.** That was measured here, at every pitch this cartridge uses:

| Turns | 0.941 mm pitch | 1.270 mm | 1.588 mm |
| --: | :--- | :--- | :--- |
| 3.5 | watertight, 1 body | watertight, 1 body | watertight, 1 body |
| 5.5 | 479 non-manifold edges | 2050 non-manifold edges, 2 bodies | 961 non-manifold edges, 2 bodies |
| 7.5 | `BRep_API: command not done` | — | — |

Two alternative formulations were tried and are worse. A **real-radius helix** produces a 670 000-face mesh whose rib does not fuse to the wall (2 bodies). A **segmented sweep** — three-turn segments stacked with a full turn of identical overlap so the helix phase stays continuous — is clean at 1.588 mm pitch but yields six bodies at 0.941 mm.

So the thread is capped at 3.5 turns, and **the joint does not rely on thread length for its alignment.** Each end carries a **plain register**: a parallel barrel ahead of the thread that takes the concentricity and the bending moment. That is also how a real stand adapter is made — the thread only holds it on. A microphone on a boom is mostly bending moment, and the manifest warns below 2 mm of register for exactly that reason.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `bushing` | Reducer Bushing | Female at the top, male stud below — the classic reducer, and the one that goes missing first |
| `double_stud` | Double Stud | Male at both ends, for joining two female fittings |
| `coupler` | Coupler | Female at both ends, for joining two studs |

Setting both ends to the same thread is legitimate, not a mistake: a same-size coupler joins two studs, and a same-size double stud joins two sockets.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:** **5/8-27 Mic Stand Thread**, **3/8-16 Stand Thread**, **1/4-20 UNC Camera Thread** — all `thread`.
- **Measured partners:** **6** — `mic-clip`, `camera-quarter-twenty`, `spigot-adapter`, `ball-socket`, `gopro-mount`, `sensor-mount-plate` — verified by running `normalize_family()` and the shipped geometry rules over the live catalog.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — this part holds a microphone above people's heads.
- **License:** CERN-OHL-W-2.0

### The seventh edge, and why it is not here

The wave plan scores this slot at **7 partners**. The missing one is `tripod-hub`, and it is missing for a punctuation reason: `tripod-hub` declares `1/4"-20 UNC — major Ø6.35 mm…`, while the family pattern is `1/4[\s-]?20`, which allows **one** separator where that string carries two (`"` then `-`). The fix (`F1` in the wave plan) is a one-character regex change, it is proposed and **not ratified**, so it is not landed here. The moment it lands, `tripod-hub` joins both `unc-1/4-20` and `unc-3/8-16`, and this adapter gains it with no change of its own.

## Printing and using it

Print **standing on an end face**, 4 perimeters, 50 % infill or solid. The threads then form on flat layers.

`clearance` is per-side slop on both threads. A printed **27 TPI** thread is a fine thread by printing standards: start at 0.3 mm and go **up**, not down, if it binds. The manifest warns below 0.2, where the thread binds before it seats and forcing it shears the crests off *inside* the fitting, where you cannot see them.

Choose **hex** for anything that must come apart cold and in the dark; a spanner works when fingers do not. The knurl is grip only — if it fails to cut, the part still builds.

### Scope — read this

**A printed thread is not a rigging component.** This adapter is for the mass of a microphone, a small light or a compact camera on a stand that is not over anybody. It is not for overhead rigging, not for a load-bearing truss fitting, not for a heavy head, and not for anything whose fall would matter. Printed polymer creeps under sustained load and fails without warning at the layer line; a metal adapter costs very little and is the right part for anything valuable or anything above a person. Inspect it before every use and replace it when the thread looks polished or the register feels loose.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of all three selects — including all three thread choices at each end**, at the **all-min and all-max corners**, and at every declared preset. **76 cases, 76 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `bushing` | 21.87 × 20.48 × 10.18 | 51.96 × 45.0 × 61.49 |
| `double_stud` | 21.87 × 20.48 × 14.37 | 51.96 × 45.0 × 82.97 |
| `coupler` | 21.87 × 20.48 × 9.97 | 51.96 × 45.0 × 44.57 |

The sweep passed on the first run, because three rules were paid for before the geometry was written rather than after:

- **The collar height is raised to whatever the bores need**, never the reverse. Trimming a bore to fit a collar the user chose would silently drop thread turns, and nothing would report it — the part would simply hold less than it says. For the coupler that guarantee is what keeps the two opposed bores from meeting and leaving a shell.
- **The thread turn count was bounded by measurement before it was exposed**, not after a failure. The probe above is the reason this cartridge has a `register_h` parameter at all.
- **Every stud straddles the collar it grows from** by a named overlap, so no fuse is ever tangential; the through bore is capped so it can never eat the minor diameter of the smallest thread present; and no fillet is taken on any edge a bore or a thread has touched.
