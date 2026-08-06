# Circuit / Breadboard Trainer

Oversized, tactile circuit-teaching hardware on the universal **2.54 mm (0.1 in)
breadboard pitch**, generated with **CadQuery** (B-Rep) — big enough for small
hands and group demonstration. Build a solderless-breadboard base board, an
oversized component holder, or a power-rail bus strip.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Breadboard Base** | `breadboard` | A base board with a grid of lead holes on the 2.54 mm pitch and a centre DIP gutter — the socket board. |
| **Component Holder** | `component_holder` | An oversized through-hole component (body + two lead legs spaced a whole number of pitches) that plugs into the board — a giant resistor / LED / capacitor to identify and place. |
| **Power Bus Strip** | `bus_strip` | A power / ground rail: a long bar with a single row of holes on the pitch and a top rail groove (the ± rails). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Breadboard Grid | `pitch` | 2.54 mm | Lead pitch — the universal 0.1 in standard. |
| Breadboard Grid | `scale` | 4.0× | Teaching oversize multiplier. |
| Breadboard Grid | `hole_dia` | 1.0 mm | Nominal lead hole (before oversize). |
| Base Board | `bb_cols` / `bb_rows` | 10 / 6 | Hole grid size. |
| Base Board | `bb_thick` / `gutter` | 3.0 mm / on | Slab thickness and centre DIP channel. |
| Component | `comp_pitches` | 4 | Lead spacing in whole pitches. |
| Component | `comp_len` / `comp_dia` | 12.0 / 5.0 mm | Body length and diameter (before oversize). |
| Component | `leg_len` | 6.0 mm | Lead-leg drop below the body. |
| Bus Strip | `bus_holes` | 12 | Holes along the power rail. |

## Faithful to the 0.1 inch grid

Everything is laid out at the **real 2.54 mm breadboard pitch** and then
multiplied by `scale`, so a classroom board is oversized yet geometrically
faithful — a component holder built at `comp_pitches = 4` has legs exactly four
pitches apart and drops straight into the board's hole grid. Because the pitch is
the genuine 0.1 inch DIP standard, the printed trainer teaches the same lead
spacing students meet on real breadboards and ICs. The lead legs are turned
slightly under the hole diameter so they insert with a light friction fit, tunable
per material.

## Presets

- **10×6 Trainer Board** — a demonstration breadboard with the DIP gutter.
- **Giant Resistor (4-pitch)** — an oversized component to label and place.
- **12-Hole Power Rail** — a ± bus strip.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **2.54 mm Lead Grid** (`grid`, *breadboard 2.54mm*) — the hole lattice
    defined by `pitch`, `hole_dia`, `scale`; every part shares the 0.1 in grid.
  - **Component Lead Footprint** (`profile`, *breadboard 2.54mm*) — the lead
    spacing `comp_pitches × pitch` that seats a holder in the board.
- **Material awareness:** `tolerance_by_material` is declared — the lead legs run
  slightly under the hole diameter, so the insertion fit tunes per material /
  printer.
- **Societal benefit:** oversized breadboard hardware makes electronics a
  hands-on, group-visible activity — learners see how rows connect and match
  leads to the grid without soldering; sharing the real 0.1 in pitch keeps a
  printed set true to standard components for a few grams of filament per part.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The breadboard is a fillet-cleaned slab with through holes (vented both faces)
  and a top gutter (vented to top). The component holder is a solid body with a
  lead rib and two solid legs unioned in — the rib guarantees a single connected
  body even when the leads reach beyond the body ends. The bus strip is a slab
  with a row of through holes and a top groove. All shipped modes and
  extreme-parameter cases render **watertight**, single-body.
