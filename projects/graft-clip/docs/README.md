# Grafting Union Clip

A spring clip that holds a graft union closed while it knits.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

Grafting joins a **scion** — the shoot you want fruit from — to a **rootstock**, the roots you want it on. It is how a household turns a wild or worthless seedling into a tree that bears known fruit, and it is how a variety survives at all: fruit trees do not come true from seed, so every apple, citrus and avocado of a named kind that has ever existed was grafted from another one.

The join only takes if the two **cambium** layers — the thin living cylinder just under the bark, which is the only tissue that divides — stay pressed together and immobile for the weeks it takes them to fuse. A clip is what supplies that pressure.

The skill is free and widely taught. **The clip is not.** It is a moulded consumable, bought by the hundred, lost in the field, and priced per unit in hard currency — which in practice rations how many grafts a smallholder or a community nursery attempts in a season. Printing it moves the binding constraint back to skill and scion wood, where it belongs.

### Why two diameters, not one

A matched graft — scion and rootstock the same thickness — is the easy case and the one every product photo shows. The real world is mismatched. Where the scion lies against the rootstock, the pair is **wider than either stem alone**, so a clip sized only to the scion pops straight off.

The jaw is therefore built around a declared union envelope:

```
union_Ø = max(scion, rootstock) + 0.25 × min(scion, rootstock)
```

| Pair | Union Ø | Note |
| :--- | ---: | :--- |
| 8 / 8 mm (matched) | 10.0 mm | the easy case |
| 8 / 10 mm (default) | 12.0 mm | typical nursery mismatch |
| 8 / 14 mm | 16.0 mm | scion onto an established stem |
| 5 / 5 mm | 6.25 mm | soft green wood, thin wall |

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `clip` | Spring Clip | CadQuery B-Rep | `main.py` |
| `wrap_band` | Wrap Band | CadQuery B-Rep | `main.py` |
| `taper_gauge` | Taper Gauge | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

The **wrap band** is for a union the jaw cannot span — a big cleft graft, or a stem healed over and no longer round. It carries grafting tape or a rubber band in tension through two radial slots rather than supplying spring force itself.

The **taper gauge** addresses the other half of the same problem. Most failed grafts fail because the two cut faces were not the *same angle*, so the cambium lines crossed instead of running together and only a point of the join was ever live. A physical reference prevents that far more reliably than an instruction does.

| Cut style | Reference angle | Used for |
| :--- | ---: | :--- |
| `whip` (whip-and-tongue) | 20° | maximum cambium contact, the classic |
| `cleft` | 35° | splitting a rootstock, inserting a wedged scion |
| `saddle` | 14° | shallow saddle over a matched stem |

## Parameters

`scion_diameter_mm` and `rootstock_diameter_mm` are the pair; `clip_wall` sets stiffness, `spring_gap` the mouth as a fraction of bore Ø, `clip_length_mm` the span along the stem. `taper_style` selects the gauge's reference angle. All labels and tooltips are bilingual (en/es).

A wall that is *thicker* grips harder but springs less and can crush soft green wood — the `soft_green` preset drops to 1.4 mm for exactly that reason.

## Reuses the published stem C-jaw

The jaw is **not** a new interface. It is the same C-jaw profile the published `plant-clip` uses for trellis work: the same 3–30 mm stem-Ø series, and the same fraction-of-bore mouth convention (capped at `2r − 0.8` so two retaining legs always survive) that `oxygen-tubing-clip` and `garment-clip` share. A grower stocking one of these is stocking the geometry of the others, and the commons did not have to publish a second stem standard.

## Hyperobject Profile

- **Domain:** agriculture
- **CDG interfaces:**
  - **Stem C-Jaw** (`snap`, 3–30 mm stem Ø series) — compatible with `plant-clip`, `garment-clip`, `oxygen-tubing-clip`.
  - **Graft Union Envelope** (`profile`, declared union Ø formula) — the mismatch rule, stated rather than assumed.
  - **Cut Taper Reference** (`profile`, whip 20° / cleft 35° / saddle 14°).
- **Material awareness:** shrinkage compensation, recycled-material toggle, tolerance-by-material.
- **Societal benefit:** removes a per-unit imported consumable from the path between a grafting skill and a fruiting tree.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print the clip **on its end**, bore vertical, so the layer lines run *around* the C rather than across the hinge — a clip printed on its side splits at the hinge on first opening, because that is exactly where the layer bond is loaded in tension. Three perimeters, 30–40 % infill.

**PETG** is the right default: it keeps some spring after weeks in sun, where PLA goes brittle and ABS/ASA can be stiffer than a soft scion tolerates. For summer green grafting under a humidity tent, PETG also survives the heat. Recycled filament is fine — nothing here is dimensional below about a quarter millimetre.

Fit the clip so the jaw **spans the whole cut face**, not just its middle; the manifest warns below 15 mm for that reason. Remove it once the union has knitted and the scion is growing away — typically a few weeks to a season depending on species and temperature. A clip left on a stem that is actively thickening will girdle it, and a girdled union dies above the constriction.

**Scope.** This is the clamp, not the technique. Which graft to use, when to cut scion wood, what rootstock suits your soil and climate, and whether the pair is even compatible are all outside what a printed part can decide; local horticultural guidance governs. The clip does not replace grafting tape or sealing where the method calls for them — it holds the union while they do their own work.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode, plus all three taper styles — **30/30**, each `is_watertight == True` with `body_count == 1`. The clip was additionally grid-tested across every scion Ø × rootstock Ø × wall × mouth-fraction combination, for **111/111** total.

**Three failures were found and fixed during authoring, and the grid found two of them that the plain min/max sweep did not.**

- **The wrap band's tape slots were not slots.** They were cut as boxes spanning `out_r × 4` in X, which does not open a window in one flank — it slices straight across the band and takes the far wall with it. At minimum wall the surviving ligament went to zero and the part came back non-watertight *while still reporting one body*, so `body_count` alone did not catch it; only the watertight check did. Each slot is now a radial window bounded to its own flank, with its height capped so a stated ligament (`height × 0.22`) survives above and below.

- **The live-hinge groove claimed a clamp it did not have.** The comment read "capped well under the wall so it can never cut through", but the cut box's X extent was never actually tied to the wall. At a 30 mm rootstock with a 1.2 mm wall the groove ran from x = −17.47 to −16.39 while the wall occupied only −17.2 to −16.0 — clean through, and the clip shattered into 23 loose pieces. The groove is now measured *inward from the outer surface* to a depth of `clip_wall − hinge_lig`, so a ligament always remains. **A comment is not a clamp.**

- **The rim break is a cut, not a fillet — and this one cost the most to find.** A blend was tried first as `edges("%CIRCLE")`, then narrowed to `faces(">Z"|"<Z").edges("%CIRCLE")`. Neither selector means "the rims". By that point in the build the solid's circular edges include every arc where the mouth slot, the flare wedges and the hinge groove meet the bore — and those arcs land on the end faces too, so scoping to the end faces changed nothing. OCC does not refuse to blend them: the result came back non-watertight and split into 13 pieces at 2.2 mm wall and 39 at 1.2 mm, **without raising**, so the surrounding `try/except` never fired.

  Isolating the build step by step made it unambiguous — the solid assessed watertight with one body immediately *before* the blend and destroyed immediately *after* it, with the volume barely changing (4225.5 → 4207.3 mm³). Two cut cones now do the same job with no selector and no kernel gamble.

Derived dimensions are otherwise clamped against the blank that must contain them: the blank is sized *from* the bore radius plus a full wall so no cut can reach an edge, the mouth is capped at `2r − 0.8`, and the flare is capped at `0.6 ×` the surviving leg so a wide mouth cannot have its remaining leg removed by its own lead-in.
