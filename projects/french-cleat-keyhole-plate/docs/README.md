# French Cleat Keyhole Plate

Two one-member families, closed by one plate.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

The commons publishes a 45° **French cleat** wall system (`french-cleat`, `grid-hub`) and a **keyhole** wall-hanging pattern (`speaker-bracket`). Both families have exactly one member the graph can see, and the two systems have never met — which is odd, because in a real workshop they meet constantly.

A cleat wall is how a shop reconfigures. A keyhole slot is how almost every commercial appliance, speaker, router bracket and power strip already expects to hang. This plate is the adapter between them, and it closes both families at once.

It is deliberately the **lowest-effort object in the tranche**, and that is the argument for it: two singletons closed by one T1 cartridge is the best edge-per-effort ratio in the whole wave.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `keyhole_plate` | Keyhole Plate | Accessory cleat on the back, keyhole **slots** on the face — the plate hangs on a cleat and receives two screws |
| `stud_plate` | Stud Plate | Accessory cleat on the back, keyhole **studs** on the face — a keyhole-slotted device hangs directly on the cleat wall |
| `cleat_shelf` | Cleat Shelf | The same cleat back carrying a small shelf with a front lip, and keyholes on its riser |

**`stud_plate` is why this is a real mate and not only a graph edge.** `speaker-bracket` presents keyhole *slots*, so something has to present the studs.

## Nothing here is a new convention

`cleat_ramp_geometry` and `accessory_cleat_profile` are **inlined from `french-cleat` unchanged**, so this plate drops onto the same wall strip at the same angle with the same hang gap. The clamp is on the *rise* rather than the run, which is what keeps the angle exact and the two mating faces genuinely parallel rather than nearly so.

`keyhole_dia` defaults to **9.0 mm** and `keyhole_slot` to **4.5 mm** — `speaker-bracket`'s own defaults, kept identical on purpose. Two cartridges that nearly agree on a keyhole are worse than two that do not agree at all, because the near-miss is only discovered with the device already on the wall.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **45° French Cleat** (`rail`, `French cleat 45 deg`)
  - **Wall Keyhole Pattern** (`bolt_pattern`, `Wall Keyhole`)
- **Measured partners:** **2** — `grid-hub` and `speaker-bracket` — verified by running `normalize_family()` and the shipped geometry rules over the live catalog. Exactly the wave plan's count, with no taxonomy caveat.
- **Material awareness:** shrinkage compensation, tolerance-by-material, **and recycled material is enabled here** — unlike most of this tranche. This part is loaded in steady bending at room temperature with no seal, no spring and no pressure to lose; reground filament is a reasonable choice for it, and saying so is more useful than a blanket rule.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **face down**, 4 perimeters, 30–40 % infill. The keyhole then forms on flat layers and the load above each slot runs *across* the layer lines rather than along them — which matters, because a keyhole plate carries its whole load on the material above two slots, in bending. The manifest warns below 3.5 mm of plate thickness, where that material is a couple of perimeters and will tear out of the slot rather than break.

Match `cleat_h`, `cleat_depth` and `angle` to the wall strip you already printed.

`fit` is the clearance between the two mating ramps: too little and the plate has to be forced down the strip, too much and it rattles and sits low.

### Scope — read this

A French cleat carries its load in shear against a wall, and the wall strip is the part that matters. **This plate is only as good as what the strip is screwed into.** Find a stud or use a fixing rated for the substrate; a cleat strip on two drywall anchors will pull out with the whole wall's worth of tools on it. Printed plastic also creeps under sustained load: check anything heavy periodically, and do not hang anything above a person, above a bed, or anything whose fall would matter.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at the **all-min and all-max corners**, and at every declared preset. **83 cases, 83 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `keyhole_plate` | 10.0 × 40.0 × 40.0 | 39.0 × 300.0 × 300.0 |
| `stud_plate` | 12.75 × 40.0 × 40.0 | 50.2 × 300.0 × 300.0 |
| `cleat_shelf` | 30.0 × 40.0 × 40.0 | 159.0 × 300.0 × 300.0 |

**One defect was found at the defaults, before the sweep, and it is a copy-the-idiom-not-the-line lesson.**

The cleat band was extruded with `french-cleat`'s own form — `.extrude(len).translate((0, -len/2, 0))`. That is correct *there*, because `french-cleat` builds a one-piece strip whose origin is its own. Here the plate is centred on Y = 0, and a `Workplane("XZ")` extrudes along **−Y**: the band landed at Y ∈ [−1.5 L, −0.5 L], overlapping the plate by a 4 mm sliver and hanging 112 mm off the side. Every render was **watertight and single-bodied** — the union was volumetric, just in the wrong place — and the only thing that showed it was the bounding box: **228 mm wide on a 120 mm plate.** The cleat is now extruded with `both=True`, which is the form that composes with a centred body.

That is why the sweep record carries bounding boxes and not just a pass count. A watertight, connected, single-bodied solid can still be the wrong shape, and the bbox is the cheapest check that notices.

The rest held on the first pass because the rules were paid for before the geometry was written:

- **The keyhole is cut as one fused tool** — head bore, slot channel and shank bore unioned *before* the cut. Cutting a circle and then a slot leaves the throat as an edge two separate booleans share, and OCC will happily produce a solid whose mesh is non-manifold at exactly that edge.
- **The stud head is a single three-section loft**, not two frusta meeting on a shared face — the tangential-union trap that cost `bucket-lid-adapter` a round earlier in this tranche.
- **Plate height and width are raised to fit the keyholes**, never trimmed. Trimming would silently shorten the slot travel, which is the one dimension that decides whether the plate can be lifted off a screw at all.
- **A pattern wider than the plate moves the holes inward** rather than cutting the plate's corners off.
- **No fillet is taken on any edge a slot or a bore has touched.**
