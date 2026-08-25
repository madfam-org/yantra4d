# Hive Frame Spacer

Spacers that hold Langstroth frames at the correct pitch inside a hive body.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Bee space

This cartridge rests on the one genuinely hard published dimension in beekeeping.

L. L. Langstroth's 1852 patent turned on a single observation: bees treat a gap of roughly **6 to 9.5 mm** as a passage and leave it open. They fill anything **smaller** with propolis, and they build comb across anything **larger**. Hold every gap in the hive inside that band and the frames stay separate and liftable.

That is the entire reason a modern hive comes apart at all. Miss it and the colony glues the box into a solid mass that cannot be opened without destroying comb and killing bees — and a beekeeper who cannot inspect cannot detect disease, manage swarming, or harvest without loss.

| Gap | What the colony does |
| :--- | :--- |
| under 6 mm | fills it with propolis — frames cement to the rail |
| **6 – 9.5 mm** | **leaves it open as a passage** |
| over 9.5 mm | bridges it with burr comb — tears on every inspection |

The manifest raises a warning on both sides of that band rather than silently letting you leave it.

## Frame pitch

A frame's comb face and its neighbour's must sit at a pitch of comb thickness plus one bee space. The spacer's job is to make that pitch **mechanical rather than eyeballed** — a hive spaced by eye drifts, and drifted frames get braced together with burr comb.

| Standard | Frame depth | Top bar | Pitch |
| :--- | ---: | ---: | ---: |
| Langstroth deep (9-1/8 in) | 232 mm | 482.6 mm | 35 mm |
| Langstroth medium (6-1/4 in) | 168 mm | 482.6 mm | 35 mm |
| Langstroth shallow (5-3/8 in) | 137 mm | 482.6 mm | 35 mm |
| Nine-frame spread (deep) | 232 mm | 482.6 mm | **38 mm** |

All three depths share the **same 482.6 mm (19 in) top bar** — they differ only in how far down they hang. That is why one spacer geometry serves the whole family. The nine-frame spread puts nine frames in a ten-frame box on purpose: the bees draw fatter honey comb, which uncaps more cleanly.

Moving `bee_space_mm` shifts the pitch as a deviation from the nominal 8 mm working value, so the slider moves the pitch the way it physically would.

## The lug

A frame hangs by its **lug**: a short tab at each end of the top bar that rests on a rebate — the "frame rest" — milled into the hive body's end wall. The lug is the only interface a spacer can grip, so it is a declared parameter rather than a hidden constant.

| Feature | Nominal |
| :--- | ---: |
| Lug projection each end | ~9.5 mm |
| Lug width | 25.4 mm (1 in) |
| Lug thickness | ~9.5 mm |

**Measure yours.** Lugs vary noticeably between makers and between home-built and bought frames, which is exactly why `lug_width_mm` and `lug_thickness_mm` are sliders and not baked in.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `rail` | Castellated Comb Rail | CadQuery B-Rep | `main.py` |
| `clip` | Lug Clip | CadQuery B-Rep | `main.py` |
| `end_spacer` | Follower Spacer | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

The **rail** drops into the frame rest and sets the pitch for a whole wall of frames at once. The **clip** grips one lug and stands off its neighbour by exactly one pitch, so a box already full of frames can be re-spaced without lifting every frame out. The **follower spacer** takes up slack at the end of a short row — a box run with fewer frames than it holds leaves a gap the last frame slides across, and a sliding frame crushes bees against the wall.

## Hyperobject Profile

- **Domain:** agriculture
- **CDG interfaces:**
  - **Langstroth Frame Pitch** (`rail`, 35 mm ten-frame / 38 mm nine-frame spread).
  - **Frame Lug Seat** (`pocket`, 25.4 × ~9.5 mm lug on the hive-body frame rest).
  - **Bee Space Gap** (`profile`, 6.0–9.5 mm, Langstroth 1852).
- **Material awareness:** shrinkage compensation, recycled-material toggle, tolerance-by-material.
- **Societal benefit:** turns an imported per-unit consumable into a local part, and publishes the standard alongside the geometry so a beekeeper who has never seen a catalogue can still hit the pitch their equipment was built around.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print the rail **flat, notches up**, 3–4 perimeters, 40 % infill. Spacers usually die by being pried with a hive tool, so wall thickness is the parameter that decides service life — the 2 mm minimum is a hard floor in the manifest for that reason, and 4 mm is the sensible default.

**Material matters more here than in most garden parts.** Use **PETG**, **ASA**, or **PP** if you have it. Avoid PLA: a hive in sun runs well above PLA's glass transition, and a softened rail loses the pitch it exists to hold. Print **solid-coloured, virgin or clean recycled** filament and skip anything with unknown additives — this part sits inside a food-producing colony for years.

**Clean before reuse.** Propolis and wax build up in the notches and change the effective pitch; scrape them each season.

**Scope — read this part.** This cartridge sets *geometry*, nothing else. Colony health, disease management, swarm control, treatment decisions, and whether you should be keeping bees on that site at all are outside what a printed part can address, and several of them are regulated where you live. Hive registration, notifiable-disease reporting, and apiary siting rules are common and vary by country and state. Nothing here substitutes for local apiary guidance or a mentor.

Note also that non-Langstroth systems — Dadant, British National, Warré, top-bar — use different frame geometry and in some cases a different bee-space convention (top-space versus bottom-space). This cartridge encodes Langstroth only, and says so rather than implying universality.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode, plus all four frame standards — **39/39**, each `is_watertight == True` with `body_count == 1`. The rail and clip were additionally grid-tested across every frame-count × lug-width × lug-thickness × wall combination, for **120/120** total.

**One failure was found and fixed, and it is the clearest illustration in this batch of why `body_count` is checked at all:**

- **The lug clip's stop was floating in mid-air.** The stand-off arm was placed from one formula and the bearing stop from another. The arm ended at x = 26.0; the stop was centred at x = 33.0 and spanned 31.0 to 35.0 — a **5 mm air gap** between two pieces that were meant to be one part. The clip rendered `is_watertight == True` at every single parameter combination, because both solids are individually closed; only `body_count == 2` caught it. **Watertight does not mean connected.** The stop is now positioned from `arm_x1`, the arm's actual computed end, and pulled back into the arm by half its own width so the union is volumetric.

Two structural clamps in the rail are deliberate rather than incidental:

- **The blank is derived from the notch layout** — `count × pitch + 2 × end_margin` — not sized independently. Sizing it separately is how a maximum-pitch, maximum-count layout runs its last notch off the end and severs the rail into loose teeth.
- **Notch depth is capped so a continuous spine always survives** (`height − spine`, with `spine = rail_thickness × 0.8`). A notch that reaches the bottom face turns one rail into N detached teeth that still tessellate perfectly well but are not a rail.

Following the lesson from `graft-clip` in this same batch, **no fillet is taken on any edge a notch or bore has touched.** OCC blends such arcs without raising and returns a non-watertight solid, so the `try/except` around a fillet is not the safety net it looks like.
