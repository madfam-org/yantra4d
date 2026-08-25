# Rain Gauge Funnel

A calibrated rain-gauge collector that screws onto an ordinary PET bottle.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

Rainfall is a **depth**, not a volume. A bare bottle left outside catches whatever its own neck happens to be — a tiny and unknown area — so the water it holds cannot be converted into millimetres of rain. It is not a measurement.

The missing piece is never the container; every household has bottles. It is calibration. Give the bottle a funnel of *known* aperture and the arithmetic closes:

```
depth_mm = collected_mL × 1000 / aperture_area_mm²
```

At the default 100 mm aperture the area is 7853.98 mm², so **1 mm of rain = 7.854 mL**, i.e. 0.1273 mm per mL. That ratio is a pure function of `aperture` and is the one number that has to be right for the instrument to be an instrument.

| Aperture | Area | 1 mm of rain collects |
| ---: | ---: | ---: |
| 50 mm | 1 963.50 mm² | 1.963 mL |
| 80 mm | 5 026.55 mm² | 5.027 mL |
| 100 mm | 7 853.98 mm² | 7.854 mL |
| 150 mm | 17 671.46 mm² | 17.671 mL |
| 200 mm | 31 415.93 mm² | 31.416 mL |

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `funnel` | Calibrated Funnel | CadQuery B-Rep | `main.py` |
| `splash_ring` | Splash Insert | CadQuery B-Rep | `main.py` |
| `mount_clip` | Post Mount Clip | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`aperture` **is** the calibration — change it and you change the scale of every reading. `rim_t` keeps the rim sharp; `cone_angle` and `throat_dia` shape the drainage path. `neck_standard`, `clearance` and `skirt_len` fit the bottle thread. `post_dia` and `bottle_dia` size the mount clip. All labels and tooltips are bilingual (en/es).

## Reuses the published bottle-neck thread

The outlet is **not** a new attachment. It is the same female helical thread and the same `NECK_STANDARDS` table the published `bottle-thread` family established (PCO-1881, PCO-1810, 28-410, 38-400), so a funnel screws onto the same bottles as `pco-cap`, `bottle-coupler`, `jar-adapter` and the `faircap-filter` chain. A gauge built here can hand its bottle straight to the water-filter ecosystem, and neither cartridge had to invent a second bottle standard.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| PCO-1881 thread major Ø / pitch | 27.4 mm / 2.7 mm, ~1 turn |
| PCO-1810 | 27.4 mm / 2.7 mm, ~1.5 turns |
| 28-410 | 28.0 mm / 3.18 mm, ~1.5 turns |
| 38-400 | 38.0 mm / 4.2 mm, ~1.25 turns |
| Aperture area | π(`aperture`/2)² |
| Collection ratio | 1 mm rain = area/1000 mL |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Bottle Neck Thread** (`thread`, PCO-1881 / PCO-1810 / 28-410 / 38-400) — compatible with `bottle-thread`, `pco-cap`, `bottle-coupler`, `jar-adapter`, `faircap-filter`.
  - **Calibrated Aperture** (`profile`, stated mm-per-mL ratio) — the instrument's scale, declared rather than incidental.
  - **Throat Bore** (`socket`, internal) — accepts the splash insert.
- **Material awareness:** shrinkage compensation, recycled-material toggle, tolerance-by-material.
- **Societal benefit:** puts a comparable, calibrated rainfall record within reach of a farm, a watershed group or a school for the cost of filament.
- **License:** CERN-OHL-W-2.0

## Siting, printing and reading it

**Siting matters more than the print.** Standard practice is to set the rim level and 300–500 mm above ground, clear of buildings and trees by at least twice their height — a gauge under an eave or beside a wall reads badly no matter how well it is made. The `mount_clip` exists because a tilted gauge presents a smaller effective aperture and silently under-reads; level it.

Print the funnel rim-down (cone pointing up) so the aperture edge is the smooth first layer and the cone self-supports. Use **ASA** or pigmented **PETG** for a gauge that lives outside year-round; PLA will craze and go brittle in UV within a season. Print the rim solid rather than sparse-infilled — a knife rim with infill voids wicks water and blunts.

Read the bottle with a kitchen measuring cylinder in mL and divide, or mark the bottle once against a known volume. Empty it after every reading.

**Accuracy scope.** This is a manual, non-recording gauge. It does not correct for wind-field losses over the aperture (the largest error in any raingauge, and the reason official gauges use windshields), evaporation between readings, or snow. Numbers from it are comparable *to each other* across a network of same-aperture funnels, which is what makes a citizen network useful — but it is not a certified instrument and should not be presented as one in a regulatory or insurance context.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode plus all four neck standards — 31/31 cases, each `is_watertight == True` with `body_count == 1`. The mount clip was additionally grid-tested across every post Ø × bottle Ø × wall combination (72/72), and the splash insert across every throat Ø × wall combination.

Two failures were found and fixed during authoring, both worth recording:

- **The splash insert's cosmetic fillet.** A flat 0.8 mm blend on `%CIRCLE` edges consumed the entire lip land at minimum throat diameter and OCC returned a self-degenerate face. It did **not** raise, so the surrounding `try/except` never fired — the part just came back non-watertight. The radius is now tied to the smallest local feature (`lip_land × 0.35`, `lip_h × 0.35`) and skipped entirely below 0.1 mm.
- **The mount clip's blank sizing.** The slab was sized from an independent `span` formula while the bores were placed separately, so at maximum post diameter the post bore ran off the end of the slab and the mouth slot severed what remained into three loose arcs. The blank is now derived *from* the bores — `x_min`/`x_max` enclose both plus a full wall — so no bore can reach an edge at any parameter combination.

Derived dimensions are otherwise clamped in `main.py` rather than trusted from the UI: the funnel's aperture is forced to clear the threaded skirt by 3 mm (`ap_r = max(ap_r, skirt_out_r + 3)`) so the revolve profile can never self-intersect, the throat is capped below the aperture, and both snap mouths are capped at `2·r − 0.8` so a retaining leg always survives.
