# Stacking Solar Dryer Tray

A stacking mesh tray for a solar food dryer.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

Somewhere around a third of what smallholders grow is lost between the field and the plate, and the largest single share of that is microbial spoilage in the first days after harvest. That is a failure of **water control**, not of yield — which matters, because every kilogram saved at that point needed no extra land, seed, water or labour. Post-harvest handling returns more per unit of effort than almost any intervention upstream of it.

Sun drying is the oldest answer and needs no power. But drying on a mat or a roof is slow, exposed to rain, dust, insects and birds, and uneven enough that part of a batch spoils anyway. A tray is what turns a dryer cabinet into a *system*: it holds food in a thin layer, off the ground, with air moving across every piece.

## Airflow, not heat

The single most useful thing this cartridge does is make **open-area ratio** a declared parameter instead of leaving mesh density to chance.

Drying is limited by **airflow across the food**, not by heat alone. The common failure of a home-built dryer is not too little heat — it is too little airflow. A hot cabinet with stagnant air **case-hardens** the surface: a dry skin seals in wet flesh, and the piece then spoils from the inside while looking finished.

So the tray declares the fraction of its floor that is hole rather than material, and **solves the strut width from it** rather than the other way round. For a square grid of pitch `p` with struts of width `s`:

```
open_ratio = (p − s)² / p²        ⟹        s = p × (1 − √open_ratio)
```

| Requested ratio | Strut at 8 mm pitch | Reads as |
| ---: | ---: | :--- |
| 0.30 | 3.62 mm | heavy, throttles airflow |
| 0.45 | 2.63 mm | conservative |
| **0.55** | **2.06 mm** | **default** |
| 0.65 | 1.55 mm | open, fast |
| 0.80 | 0.84 mm → clamped to 1.00 | at the printable floor |

Two clamps can move the built result away from the request, and `mesh_report()` in `main.py` states both rather than letting them pass silently:

- **`MIN_STRUT = 1.0 mm`** — below roughly two extrusion widths a strut is a single unsupported bead spanning a hole; it droops, and it breaks when the tray is washed.
- **`MAX_HOLES = 900`** — a B-Rep kernel limit, not a design preference. See Verification.

## Stacking

Trays stack so one dryer holds several loads and so air is forced to travel across each layer in turn. The rim carries a male spigot on top and the tray above drops its rim over it, with 0.35 mm printed clearance per side so a stack self-locates instead of sliding.

`stack_height_mm` sets the gap between mesh planes. Too tight and the tray above touches the food below — marking the pieces and blocking the air over them, which the manifest warns about under 20 mm. Too loose and the cabinet is mostly air.

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `tray` | Mesh Tray | CadQuery B-Rep | `main.py` |
| `stack_foot` | Stack Foot | CadQuery B-Rep | `main.py` |
| `airflow_baffle` | Airflow Baffle | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

The **stack foot** exists because air must be able to *enter under* the stack. A stack sitting flat on the cabinet floor draws only from its sides, and the bottom tray — usually nearest the absorber and therefore hottest — case-hardens first.

The **airflow baffle** stops the stream short-circuiting up the gap between the stack and the cabinet wall. That short-circuit is the classic reason a load dries at the edges and stays wet in the middle: air takes the cheapest path, and the cheapest path is never through the food.

## Choosing a pitch

| Load | Suggested pitch | Note |
| :--- | ---: | :--- |
| Herbs, chilli, seeds | 4–6 mm | fine enough to hold small pieces |
| Sliced fruit, tomato | 8–12 mm | the default range |
| Whole halves, large slices | 14–20 mm | dries fastest, small pieces fall through |

## Hyperobject Profile

- **Domain:** agriculture
- **CDG interfaces:**
  - **Open-Area Mesh** (`grid`, declared ratio with the strut solved from it) — compatible with `produce-tray`, `seed-tray`.
  - **Tray Stack Spigot** (`rail`, 0.35 mm printed clearance per side).
  - **Stack Lift Foot** (`socket`, internal).
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — this is a food-contact part and reground filament of unknown provenance is not appropriate for it.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print the tray **flat, mesh down**, 3 perimeters, 20 % infill — the struts print as solid bridges at that setting. **PETG** is the sensible default: food-contact-plausible, survives a dryer cabinet that can run well past 60 °C on a hot afternoon, and tolerates washing. **PLA will sag** in a working solar dryer and take the mesh geometry with it.

Use **virgin filament** and a **clean nozzle**. Print with a smooth first layer and wash before first use.

**Load thin and single-layer.** Piling food on a tray defeats the open area you just paid print time for: the pieces shade each other from the air, and the bottom of a heap dries last or not at all.

**Rotate the stack** through the day. Even with a baffle, the bottom tray sees hotter, drier air than the top one.

### Scope

This is the tray, not the dryer. Cabinet sizing, glazing, absorber design, chimney height and — above all — **food safety** are outside what a printed part decides.

Drying is a preservation method with real limits: it does not sterilise, water activity has to fall far enough to actually stop microbial growth, and some foods (meat, fish, anything low-acid) carry risks that solar drying alone does not address. Reconstituted or under-dried produce can be hazardous. Follow local food-safety guidance for what you are drying and how you store it afterward; nothing here substitutes for that.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode, plus all three rim styles — **30/30**, each `is_watertight == True` with `body_count == 1`.

**This cartridge was the hardest of the six, and four distinct failures were found and fixed. Three of them are recorded because they are not obvious:**

- **The mesh was originally cut as full-width slots in two directions — and that is not a mesh.** Each slot ran past the tray edges, so the two families together took the rim's lower band with them, and where they crossed they left every cell island connected to nothing. A 200 mm tray came back as **531 separate bodies**. The mesh is now an array of discrete square holes, every one bounded strictly inside a perforated field that itself stops a full strut short of the cavity wall — so the floor always meets the rim through solid material all the way round.

- **A hole count that the kernel cannot take.** A 300 mm tray at 4 mm pitch asks for roughly 5000 discrete holes. Fusing that many boxes into one cutting tool and subtracting it **did not complete in ten minutes** — the run was killed with no output at all. Cutting them one at a time is worse, since each boolean re-evaluates a solid more complex than the last (that version took 183 s at the *default* size). The grid is now capped at `MAX_HOLES = 900` and the effective pitch is opened up to spread that many holes across whatever tray was asked for.

- **Capping the count silently wrecked the ratio, which is the one number this cartridge exists to get right.** With the count capped the effective pitch grows, but the hole *opening* was still being clamped to the originally-requested fine value — leaving enormous struts. At 300 mm on 4 mm pitch the achieved open ratio fell to **0.086 against a requested 0.55**. Since `open_ratio = (open/pitch)²`, the opening now simply scales with the pitch actually used (`opening_for()`), and the worst case holds **0.546**. A cartridge that quietly delivers a sixth of the airflow it promises would be worse than one that refused to build.

- **The stacking spigot and the stack foot were both detached, for two different reasons.** The spigot was sized from `w − 2·wall − 2·clearance`, which put its band at 94.85–97.25 mm while the rim's ran 97.6–100.0 — a 0.35 mm air gap the whole way round, touching only through a `−0.01` mm z-overlap on zero footprint. `clearance` belongs on the *socket* side of a joint, never on the side that has to stay attached. The foot's leg, meanwhile, had a **fully enclosed internal void**: physically unprintable (it traps air and cannot drain when washed) and geometrically counted by trimesh as a body of its own, so the foot read `body_count == 2` at every parameter combination while being perfectly watertight. Isolating the build showed the **leg alone** was already two bodies before the pad, lip or slots were involved — two earlier attempts to fix the lip had been chasing the wrong part entirely.

Following the lesson from `graft-clip` in this same batch, **no fillet is taken on any edge a slot or bore has touched.** OCC blends such arcs without raising and returns a non-watertight solid, so a `try/except` around a fillet is not the safety net it appears to be.
