# Walker Glide Cup

The front feet of a walker do **not** grip — they **slide**. This glide cup,
generated with **CadQuery** (B-Rep), presses onto the front leg tube and presents a
broad, smooth, low-friction dome that skates over vinyl, tile, and low-pile carpet
instead of catching on it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **A printable mobility AID for personal use, not a certified medical device.**
> A glide that slips is a fall risk: test on YOUR floor, under YOUR weight, before
> relying on it, and replace it when the wear face is thin.

## Why this cartridge exists

The commons' mobility aids stopped at `mobility-tip`, which is deliberately a
**grip** tip for the rear legs. Glide and grip are genuinely different parts, and
the distinction is clinical: a front leg that grips instead of sliding is a trip
hazard. The two cartridges share the leg-tube socket series and **nothing else**.

The sliding front glide is also the higher-replacement-rate part — it is the one
that wears out — which is why the **wear face** here is a published parameter
rather than a hidden constant.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Glide Cup** | `glide_cup` | The domed sliding cup — the front-leg standard. |
| **Tennis-Ball Cup** | `tennis_cup` | A hemispherical seat that takes a tennis ball, the classic improvised glide. |
| **Carpet Glide Disc** | `glide_disc` | A flat, wide disc for deep carpet where a dome digs in. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Leg | `tube_dia` | 25.0 mm | Leg tube outer diameter — 25 mm is the common front leg. |
| Leg | `clearance` | 0.35 mm | Per-side press-fit gap. |
| Leg | `wall` | 3.2 mm | Socket wall. |
| Leg | `socket_h` | 30.0 mm | Seating depth — deeper resists being pulled off. |
| Glide | `wear_th` | 6.0 mm | **THE CONSUMABLE** — material beneath the socket that abrades away. |
| Glide | `glide_dia` | 58.0 mm | Sliding face diameter. |
| Glide | `dome_rise` | 7.0 mm | Dome bulge; 0 gives a flat disc for deep carpet. |
| Ball | `ball_dia` | 67.0 mm | Ball diameter (a tennis ball is about 67 mm). |
| Ball | `rim_th` | 3.0 mm | Rim that retains the ball. |

## Presets

- **Front Leg 25 mm (Vinyl)** — the default.
- **Heavy Wear Face** — a thicker consumable for a heavy user or rough floor.
- **Tennis Ball (67 mm)** — the ball-seat variant.
- **Deep Carpet Disc** — flat and wide.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Leg Tube Socket** (`socket`, shared leg-tube series, glide variant) —
    `tube_dia`, `clearance`, `wall`, `socket_h`. Compatible with `mobility-tip`:
    the same leg tube, a deliberately different ground face.
  - **Wear Face Profile** (`profile`, internal) — `wear_th`, `glide_dia`,
    `dome_rise`. The consumable, published.
  - **Ball Seat** (`pocket`, tennis ball nominal Ø 67 mm ITF) — `ball_dia`, `rim_th`.
- **Material awareness:** `clearance` and `wear_th` are exposed so the socket and
  the consumable can be tuned per material and per user weight;
  `tolerance_by_material` is declared.
- **Societal benefit:** the improvised tennis ball is one of the world's most
  widespread assistive hacks, and it exists because commercial glides are a
  recurring consumable that is hard to source in the right diameter.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- **Watertight strategy:** every body is one solid. The leg socket is a single
  blind bore that **always** leaves a floor beneath it — the floor thickness is
  enforced by a clamp, not by hope, and that floor *is* the wear face. The dome is
  a revolved profile unioned coaxially; the ball seat is one revolved cut. No
  shelling, no lofted surfaces.
- **Two revolve degeneracies are designed out here**, both observed as real
  failures during verification before the current shapes were adopted. In each
  case OCCT reported a single valid solid while the exported mesh was a
  non-watertight two-body soup, so `.solids()` alone would not have caught them:
  - The dome profile does **not** start on the revolution axis. A profile whose
    first point sits at `r = 0` sweeps a **pole singularity** that tessellates
    into a torn cap, so the apex carries a small flat land instead. The land is
    far too small to change how the cup slides, and real floor contact is a land
    anyway.
  - The ball seat is **not** a `sphere()` cut. A sphere primitive grazes the body
    at its tangency and leaves a zero-volume sliver; the seat is instead a solid
    of revolution with a flat bottom land, extended straight up so it **exits**
    the top face cleanly rather than ending tangent to it. The body radius is
    clamped to contain the seat rim plus `rim_th`, so the seat can never cut out
    through the sides.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
