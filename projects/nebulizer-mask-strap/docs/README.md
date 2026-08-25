# Nebulizer Mask Strap Buckle

Head-strap hardware that re-straps a nebulizer or aerosol mask with ordinary webbing after the original elastic perishes.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A nebulizer mask is normally thrown away when its elastic loop perishes, even though the mask body is intact. The elastic lives in a warm, humid airstream and gets washed; the moulded mask does not care. These three parts let a carer re-strap the same mask with stock webbing and, more usefully, make the fit *adjustable* — which matters for a child, or for a patient who cannot tolerate the tension of a fixed factory loop.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `tri_slide` | Three-Bar Strap Adjuster | CadQuery B-Rep | `main.py` |
| `mask_hook` | Mask Staple Hook | CadQuery B-Rep | `main.py` |
| `split_yoke` | Split Yoke | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`webbing` selects the nominal strap width (20/25 mm). `web_t` and `slot_clear` size the slot to the strap you actually own. `bar_w`, `frame_t` and `rail_t` set the frame; `staple_w` and `staple_t` fit the hook to your mask's moulded staple; `yoke_angle` fans the yoke arms. All labels and tooltips are bilingual (en/es).

## Deliberately not a new standard

The webbing interface here is **not** invented for this cartridge. It is the same nominal 20/25 mm slot the wearables closures wave published — slot width = nominal + clearance, slot height = webbing thickness + clearance. A strap already cut for `strap-buckle`, `tri-glide-slider`, `ladder-lock`, `cam-buckle` or `side-release-buckle` threads these parts unchanged, and a carer can mix a printed medical yoke with an off-the-shelf side-release buckle for a quick-release head strap. Publishing a second, medical-only strap width would have been the easy authoring choice and the wrong commons choice.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| Webbing nominal (published series) | 20.0 / 25.0 mm |
| Slot width | nominal + `slot_clear` |
| Slot height | `web_t` + `slot_clear` |
| Mask staple throat | `staple_w` × `staple_t`, + `slot_clear` on both |

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Webbing Slot** (`rail`, 20/25 mm webbing) — the published strap interface; compatible with `strap-buckle`, `tri-glide-slider`, `ladder-lock`, `cam-buckle`, `side-release-buckle`.
  - **Mask Strap Staple** (`snap`, moulded aerosol-mask staple) — the hook throat that captures the mask's own staple without modifying the mask.
- **Material awareness:** tolerance-by-material (slot fit tuned per filament).
- **Societal benefit:** keeps an intact mask in service when only its elastic has failed, and makes the fit adjustable for patients the factory loop does not suit.
- **License:** CERN-OHL-W-2.0

## Printing and material notes

Print flat on the bed with the slots vertical, so the strap load runs along the layer lines rather than across them. These parts contact skin and sit in a humid airstream: PETG is the sensible default because it survives repeated washing and does not soften at the temperatures a warm-mist nebulizer reaches. Avoid PLA, which creeps under sustained strap tension and deforms in a hot wash.

This is strap hardware, not a medical device: it does not touch the gas path and makes no claim about the mask's own performance or its regulatory status.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider plus both webbing options — 41/41 cases, each `is_watertight == True` with `body_count == 1`.

Derived dimensions are clamped in `main.py` rather than trusted from the UI: the frame is forced thicker than the slot it carries (`frame_t = max(frame_t, slot_h + 1.6)`), bar and rail widths have hard floors, and the hook mouth is capped below the throat height so a retaining lip always survives. Those clamps are what keep the extremes watertight instead of splitting the frame into two bodies.
