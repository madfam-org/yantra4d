# Water Meter Box Lid

Lids for the utility box that houses a domestic water meter — parameterised to the pit you measured, not to a catalogue number.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A missing meter-box lid fails in three ways at once: the meter is exposed to frost and debris, the open box is a trip hazard and an ankle trap on a verge or sidewalk, and the utility cannot read the meter without clearing it out first.

The lid is stolen for scrap or cracked by a vehicle, and the replacement is a moulded part specific to a box some contractor installed decades ago — quoted on a minimum order, back-ordered, or simply no longer made. Meanwhile the hole sits where people walk, and the standard improvisation is a paving slab that nobody can lift for a reading.

**This is why the cartridge parameterises the bore rather than shipping a size chart.** Meter pits were laid over decades by different contractors to different specs; there is no single global standard to encode, and pretending otherwise would produce a part that fits nothing. You measure the opening; the lid is authored to it.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `round_lid` | Round Drop-In Lid | CadQuery B-Rep | `main.py` |
| `rect_lid` | Rectangular Pit Lid | CadQuery B-Rep | `main.py` |
| `lock_tab` | Locking Tab | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`bore_dia` (round) or `box_w`/`box_l` (rectangular) is the measured opening; `clearance` allows for a pit that is neither round nor clean. `ledge` sets how far the flange bears on the rim, `plug_h` how far the plug drops in to stop it sliding, and `lid_t` the plate thickness. `slot_l`/`slot_w` cut the lift slot, `port_dia` an optional reading port, and `rib_count` adds stiffening ribs. The tab parameters size the turning lock. All labels and tooltips are bilingual (en/es).

## Typical sizes

Provided as measurement starting points, **not** as a standard to trust:

| Opening | Typical sizes |
| :--- | :--- |
| Round pits | ~180, 230, 300, 380 mm |
| Rectangular mouths | ~250×180, 300×230, 380×300 mm |
| Lift slot | ~50–90 mm long, 12–20 mm wide |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Meter Box Bore** (`socket`, measured municipal meter-box mouth) — compatible with `stormwater-grate`.
  - **Bearing Ledge** (`profile`, internal) — the flange overhang that transfers load to the box rim.
  - **Lift Slot** (`pocket`, hand-tool slot, clamped inside the plug).
  - **Lock Tab Pivot** (`bolt_pattern`, internal).
- **Material awareness:** shrinkage compensation, recycled-material toggle, tolerance-by-material.
- **Societal benefit:** closes an open utility box the same week, and the reading port removes the reason lids get left off after every visit.
- **License:** CERN-OHL-W-2.0

## Printing, material and load

Print flat, plug side up, with high infill (50%+) and at least five perimeters — the flange is a plate in bending and the ribs are its beams. **ASA** for a lid that lives in sun and frost; pigmented **PETG** as a second choice. PLA is unsuitable: it creeps under a standing load and embrittles in UV, and a lid that fails underfoot is worse than the hole it covered.

The reading port is worth using. A lid that lets the meter be read without lifting removes the single most common reason a lid ends up left off, upside down, or lost after a visit.

**Load scope — read this.** This is a **pedestrian-area cover, not a load-bearing or traffic-rated lid**. It must not be placed in a driveway, a parking area, or anywhere a vehicle can run over it, and it is not a substitute for a rated casting where one is specified. The manifest warns below 8 mm thickness because under that it is a debris cover only, not something to stand on. Nothing here is load-tested and this cartridge makes no engineering claim.

Also worth saying plainly: the meter itself belongs to the utility. Fitting a lid over an open box is a safety repair; opening, obstructing, or interfering with the meter, its seals, or its connections is not, and in most jurisdictions is an offence. Print the lid, close the hazard, leave the meter alone.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode — 49/49 cases, each `is_watertight == True` with `body_count == 1`. An additional 105-case local grid covered the pathological combinations (smallest bore × largest slot × largest port × most ribs, and the inverse).

Two failures were found and fixed during authoring, and the first is the most transferable lesson in this whole wave:

- **Cutting with a `cq.Compound` of OVERLAPPING solids silently produces a broken mesh.** The stadium-shaped lift slot was built as a compound of a bar plus two end cylinders. It raised no error, and the CAD solid count stayed at `1` — but the exported STL tessellated into **1031 loose shells** and was not watertight. Every overlapping cutter and every overlapping union member in this file is now `fuse()`d into a single solid first. A compound of *disjoint* members remains safe and is used deliberately elsewhere in the commons (the `stormwater-grate` slot arrays rely on it for a 31× speedup); the difference is purely the overlap, so the rule is: **fuse whenever members intersect.**
- **Full-diameter ribs were severed by the lift slot.** At seven or more radial ribs, two of them straddle 90° and both get sliced by the slot, leaving the wedge trapped between them fully detached — the lid exported as two bodies. Ribs are now *ring* ribs that start outside the slot footprint and run out to the plug edge, which makes the failure structurally impossible instead of a function of rib count.

Derived dimensions are otherwise clamped in `main.py` rather than trusted from the UI: `_fit_slot` clamps the lift slot to stay inside the plug with a full 3 mm wall, and the reading port is clamped clear of both the slot and the plug edge, so a 120 mm port on a 120 mm bore reduces to a legal hole instead of breaking out through the rim. Every opening is cut fully through and breaks out on both faces — a blind pocket would keep the Euler characteristic at 2 and pass a naive watertight check while being geometrically wrong, which is why the local harness reports genus as well as body count.
