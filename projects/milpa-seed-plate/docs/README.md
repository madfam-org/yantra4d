# Milpa Seed Spacing Plate

A hand-held spacing jig for laying out a milpa — maize, beans and squash together.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

The milpa is not a crop, it is a **system**. Maize gives the bean a pole to climb. The bean fixes nitrogen the maize spends. The squash runs between the hills, shades the ground and holds moisture. Each plant pays for something another one costs.

The system only works at the right spacing, and spacing is exactly what hand-sowing loses — across a season, a slope, and several pairs of hands, an eye-judged pitch drifts. Extension services teach spacing as *numbers*, but a smallholder has no cheap instrument to apply a number to ground.

This plate is that instrument. It is a **jig, not a planter**: you lay it on prepared ground, drop seed through the holes, and lift. What it guarantees is a repeatable, *stated* spacing that an inexperienced or tired hand reproduces exactly.

### Two pitches, not one

| Parameter | Axis | What it controls |
| :--- | :--- | :--- |
| `row_spacing_mm` | across the plate (X) | distance between **rows** |
| `hill_spacing_mm` | along a row (Y) | distance between **hills** |

Field milpa runs roughly **800–1000 mm between rows** and **400–500 mm between hills** of 3–5 maize seeds. Those spans are neither printable nor carryable, so the plate is a **sub-multiple** you step across the plot:

| Field pitch | Plate pitch | Steps per field interval |
| ---: | ---: | ---: |
| 800 mm rows | 200 mm | 4 |
| 900 mm rows | 300 mm | 3 |
| 1000 mm rows | 250 mm | 4 |
| 400 mm hills | 200 mm | 2 |
| 500 mm hills | 250 mm | 2 |

The `row_marker` mode exists to keep those successive placements on **one** grid rather than drifting: leave it in the last hole of a pass and register the plate's end hole against it.

### Why the holes are a block, not a line

Maize is **wind-pollinated**. A single long row sheds its pollen sideways into nothing and sets a visibly gap-toothed cob — kernels missing in patches. Sown as a block of several short rows, the same plants pollinate each other. So `hole_count` is laid out as a **near-square block** rather than a strip, and the manifest raises a warning below four holes.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `plate` | Spacing Plate | CadQuery B-Rep | `main.py` |
| `depth_stop` | Dibber Depth Stop | CadQuery B-Rep | `main.py` |
| `row_marker` | Row Marker | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`row_spacing_mm` and `hill_spacing_mm` are the two independent pitches. `hole_count` sets the block size, `seed_diameter_mm` the drop bore, `plate_thickness` the slab, `handle_style` the grip. `depth_stop_mm` and `dibber_dia_mm` size the sowing collar. All labels and tooltips are bilingual (en/es).

### Sizing the seed bore

| Seed | Typical Ø | Suggested bore |
| :--- | ---: | ---: |
| Maize kernel (*Zea mays*) | 8–12 mm | 14 mm |
| Common bean (*Phaseolus vulgaris*) | 10–14 mm | 16 mm |
| Squash / calabaza (*Cucurbita* spp.) | 12–18 mm | 20 mm |

Size to the **largest** seed in the mix — one plate serves all three, since a bore that passes squash also passes maize.

### Sowing depth

Maize wants roughly **30–50 mm**. Shallower and birds and ants take the seed before it roots; deeper and the coleoptile spends its reserves reaching light and emerges weak or not at all. The `depth_stop` collar is a split ring that springs onto a dibber or planting stick and makes that depth repeatable without judgement.

## Hyperobject Profile

- **Domain:** agriculture
- **CDG interfaces:**
  - **Sowing Grid** (`grid`, declared row × hill pitch in mm) — compatible with `seed-tray` and `net-cup-lid`, so a milpa block laid out here can be raised from the same commons' propagation and hydroponic shelves.
  - **Seed Drop Bore** (`socket`, 6–30 mm seed Ø series) — sized by seed, not by guess.
  - **Dibber Collar** (`socket`, 10–50 mm round handle-stock series) — the same round-stock series the household handle cartridges use.
- **Material awareness:** shrinkage compensation, recycled-material toggle, tolerance-by-material.
- **Societal benefit:** turns a taught spacing number into a physical pattern any hand can reproduce, for the cost of filament.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print the plate **flat on the bed**, holes vertical, 3–4 perimeters and 20 % infill — it is a jig that gets stepped on and dropped, not a display piece. **PETG** or **ASA** outlast PLA in field sun; PLA left in a truck bed on a hot afternoon will sag and lose the very pitch it exists to hold. Recycled filament is entirely appropriate here: nothing about this part is dimensional-critical below about half a millimetre.

Use it on **prepared, roughly level ground**. On a slope, work across the contour rather than up and down it, and re-register on the `row_marker` every pass — a plate stepped downhill by eye walks its grid.

**Scope.** This sets *geometry*, not agronomy. Correct spacing for your ground depends on variety, rainfall, soil depth and whether you are intercropping at all; the field pitches quoted above are a common smallholder range, not a recommendation for a particular plot. Local extension guidance and your own seed's instructions govern. It does not meter seed count per hill — that stays a hand judgement, as it traditionally is.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode, plus all three handle styles — **26/26**, each `is_watertight == True` with `body_count == 1`. The plate was additionally grid-tested across every hole-count × seed-Ø × thickness × handle-style combination, for **107/107** total.

One structural decision is worth recording, because it is the failure this family of parts invites: **the blank is derived from the grid, not sized alongside it.** The hole centres are computed first, and the slab's half-width and half-depth are then set to `(grid extent)/2 + hole radius + margin`. Sizing the slab from an independent formula is exactly how a maximum-pitch, maximum-count grid ends up with its outer bores hanging off the edge — which cuts the plate into loose islands that still tessellate but are not one body.

Two further clamps are deliberate rather than incidental:

- **The hole-mouth funnel is a cut cone, not a fillet.** A blend on a bore edge in a thin slab is the classic OCC self-degenerate-face case, and it fails *silently* — no exception is raised, the solid simply comes back non-watertight, so the surrounding `try/except` never fires. Cutting a loft cone instead avoids the operation entirely. The chamfer is also capped at `plate_thickness × 0.35` and `hole_r × 0.5` so it can never consume the slab or the bore wall.
- **The corner fillet is capped under the margin** (`margin × 0.6`), so the blend can never reach the outermost hole and eat its wall.
