# Oxygen Tubing Clip

Tubing management for home oxygen: route the cannula line along a garment edge, a chair rail or a skirting board.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A concentrator user drags fifteen metres of supply line around a house every day. It snags on furniture legs, gets rolled over by a walker, and when it catches it pulls the cannula off the face — a fall risk and a therapy interruption in the same motion. The near-universal improvisation is a clothes peg.

Note the design intent in `grip`: a *wider* channel mouth is often the safer choice, because the clip should release the tubing under a snag rather than transmit the yank to the patient's face. This cartridge is deliberately parameterised so a household can choose that trade-off rather than having it fixed at authoring time.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `garment_clip` | Garment Clip | CadQuery B-Rep | `main.py` |
| `rail_clip` | Rail Clip | CadQuery B-Rep | `main.py` |
| `wall_anchor` | Wall Anchor Saddle | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`tube_od` (4–7 mm) sizes the channel to your line, with `tube_clear`, `grip` (mouth width as a fraction of Ø), `wall` and `length`. The garment jaw adds `bite_gap`, `jaw_len` and `jaw_t`; the rail clip adds `rail_dia`; the wall anchor adds `screw_dia`. All labels and tooltips are bilingual (en/es).

## Two reused interfaces, no new ones

- The **tube channel** is a 4–7 mm OD series covering real home-oxygen supply tubing (crush-resistant line is ~6.3 mm OD / ~4 mm ID; thin cannula lead is nearer 4 mm, heavy concentrator line nearer 7 mm).
- The **garment jaw** reuses the jaw profile the commons already published in `garment-clip` — a slab jaw pair with a bite gap and a lead-in flare — rather than inventing a second, medical-only jaw. That is what makes this cartridge a cross-link between the wearable and medical shelves instead of an isolated part.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| Home-oxygen supply tubing OD | ~6.3 mm (range 4.0–7.0) |
| Channel bore | `tube_od` + 2 × `tube_clear` |
| Channel mouth | `grip` × channel Ø |
| Garment bite gap | `bite_gap` (shirt placket ~1.5–2.5 mm) |

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Oxygen Tube Channel** (`socket`, supply tubing OD 4–7 mm) — the C-channel that holds the line.
  - **Garment Edge Jaw** (`snap`, commons garment-clip jaw profile) — compatible with `garment-clip`, `suspender-clip`, `garter-clip`.
- **Material awareness:** tolerance-by-material (channel fit tuned per filament).
- **Societal benefit:** lets a household dress a supply run properly, and lets them tune whether it holds or releases under a snag.
- **License:** CERN-OHL-W-2.0

## Printing notes

Print with the channel axis vertical or flat on the bed; the C mouth needs to flex, so orient so the mouth opening is not split across a weak layer boundary. PETG is preferred over PLA for anything that lives on a person or in a warm room. These clips touch the *outside* of the tubing only — they are not part of the gas path and make no claim about oxygen service.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every applicable slider — 43/43 cases, each `is_watertight == True` with `body_count == 1`.

Beyond watertightness, the local harness also checks the mesh's **Euler characteristic** (genus). That check earned its place here: the first draft of this cartridge extruded its channel on an `XZ` workplane, which extrudes toward **−Y**, so every "through" bore was translated the wrong way and silently became a *blind pocket*. Watertight passed, `body_count == 1` passed, and the part was wrong. Genus caught it — `wall_anchor` now correctly reports `g == 2` for its two screw through-holes.

The garment jaw's lead-in flare is built from an explicit triangular prism whose two legs are each clamped against the material actually available, rather than from a rotated box. A rotated box swings its far corner an unbounded distance into the arm; at `jaw_t.min` and `jaw_len.max` that cut straight through and split the clip into three bodies.
