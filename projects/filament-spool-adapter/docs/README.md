# Filament Spool Adapter

The spool runs on a bearing, and the core is whatever the core is.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

**A spool dragging on a printed axle is the commonest cause of under-extrusion that is not the extruder's fault.** It is a particularly cruel failure because the drag is not constant: it rises as the spool empties and the tension arm has less mass to fight, so it appears *late in a long print* and looks exactly like a heat or retraction problem. People chase it for weeks.

Fifty cents of bearing and a printed insert remove it entirely.

## What is fixed, and what is a slider

**Every filament spool has a different core.** 52, 54 and 56 mm are the sizes most often quoted — but they are *quoted*, not specified. There is no issuing body for a spool core, and the only honest way to build against one is to measure it. So `core_dia` is a slider from 20 to 90 mm, and its tooltip says exactly that: a figure copied from a forum is not a dimension.

**The bearing does have a numbered standard.** 608 is an ISO 15 deep-groove ball bearing, **8 × 22 × 7 mm**, the most available bearing on earth, and already the shared interface of six commons cartridges: `idler-608`, `gt2-idler`, `bearing-housing`, `linear-wheel`, `roller-bracket`, `timing-pulley`.

So this cartridge fixes what is fixed and parameterises what is not. The bearing figures are still exposed as sliders, because the same geometry serves 623 / 624 / 625 / 688 — **the seat is the interface, not the part number.**

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `core_insert` | Core Insert | Presses into the spool core and carries a 608, so the spool turns on a bearing instead of on its own plastic |
| `axle_stub` | Axle Stub | The 8 mm shaft the bearing rides, on a bolt-through flange |
| `spool_roller` | Spool Roller | A roller with a 608 at each end, for the other common arrangement — a spool resting on two rollers, which copes with every core diameter at once because it never touches the core |

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **608 Bearing Seat** (`socket`, `608 bearing (ISO 15 — 8×22×7)`)
  - **8 mm Axle Shaft** (`socket`, same family)
  - **Spool Core Series** (`profile`, internal — declared as a *measured* bore with no issuing body, which is the honest way to name a dimension nobody publishes)
- **Measured partners:** **6** — `bearing-housing`, `gt2-idler`, `idler-608`, `linear-wheel`, `roller-bracket`, `timing-pulley` — verified by running `normalize_family()` and the shipped geometry rules over the live catalog. Exactly the wave plan's count.
- **Material awareness:** shrinkage compensation, tolerance-by-material, **and recycled material is enabled** — this part is loaded gently at room temperature with no seal and no pressure. A spool adapter is exactly the kind of object reground filament should be used for.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **flange down**, 4 perimeters, 40 % infill. The bearing seat then forms on flat layers, which is the difference between a seat that presses square and one that presses crooked.

`press_fit` is interference on the bearing's **outer race**. Zero is a slip fit, for a bearing you want to recover afterwards; 0.1 mm is a firm press into PETG. The manifest warns above 0.25 mm, and the reason is worth knowing: **a printed seat over-pressed does not usually crack on the day you fit it — it cracks on a cold day months later.**

The shoulder behind the seat is derived so that it touches **only the outer race**. A shoulder that reaches the inner race drags on it, and the bearing then does nothing at all while looking perfectly installed.

608s are the most recoverable component in the machine: they come out of skateboards, fidget spinners and dead fans. Set `press_fit` to 0 when you want to get one back.

### Scope — read this

This is a light-duty rotating part. It carries the weight of a filament spool on a bench, and nothing else. It is not a load-bearing bearing housing, not a wheel hub, and not for anything that spins fast or carries a person or a tool. Printed polymer creeps under sustained load; if the flange starts to dish or the spool begins to wobble, replace it rather than tightening something.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at the **all-min and all-max corners**, and at every declared preset. **59 cases, 59 pass, on the first run**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `core_insert` | 24.0 × 23.99 × 9.2 | 120.0 × 119.96 × 57.6 |
| `axle_stub` | 58.0 × 57.98 × 13.2 | 120.0 × 119.96 × 48.6 |
| `spool_roller` | 30.1 × 30.09 × 21.6 | 66.0 × 65.98 × 141.6 |

Clean on the first run because the one failure this part *wanted* to have was designed out before any geometry was written:

**The bearing seat lives entirely in the flange, never in the core barrel.** `core_dia` goes down to 20 mm, and a 608 seat is Ø22. A seat allowed to run into the barrel would therefore be a Ø22 bore inside a Ø20 body at the small end of the core range — **a bore wider than the solid it sits in**, which is not a part with a hole, it is a shell. The flange thickness is derived as `bearing_w + shoulder` so the seat is always contained, and the barrel only ever carries the axle bore.

The rest of the rules were paid for by earlier cartridges in this tranche and applied here directly:

- **The axle bore is derived from the bearing bore and is always smaller than the seat**, so the seat's shoulder always survives — and that shoulder is sized to touch only the outer race.
- **The grip fingers are bounded inside the barrel's own length.** A slot reaching the flange would sever the barrel from it, and the result would be *N* separate watertight fingers plus a disc — the failure `is_watertight` cannot see.
- **Every union straddles what it grows from**, so no fuse is tangential, and the barrel's lead-in is a loft rather than a chamfer taken on a bored edge.
- **Every bore opens on a face**, so nothing is ever a sealed void.
