# Tube Squeezer Key

A **winding key** that squeezes the last of a toothpaste, cosmetic, or paint
tube, generated with **CadQuery** (B-Rep). Feed the flattened (crimped) end of
the tube through the lengthwise **slot**, then turn the bar so the tube winds
around it, driving every remaining bit of product forward.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Squeezer Key** | `squeezer` | The standard flat slotted winding key. |
| **Roller Squeezer** | `roller_squeezer` | A chunkier, edge-rounded barrel (≥ 9 mm thick, taller) that winds wide tubes flat in fewer turns. Same slot interface. |

## How it works

The bar carries a **through-slot** running along its length — verified open top
to bottom, so the crimped tube end threads all the way through. The slot length
follows `tube_width`; its width is `slot_width`. A turn handle at the far end
gives you leverage:

- **Winged Tabs** (`handle` on) — two finger wings to twist by hand.
- **Rod hole** (`handle` off) — a `rod_dia` cross-hole to pass a pencil or rod
  through and crank.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tube & Slot | `tube_width` | 35 mm | Flattened tube width → slot length. |
| Tube & Slot | `slot_width` | 1.6 mm | Slot opening for the crimped end. |
| Tube & Slot | `wall_margin` | 6.0 mm | Material at each end of the slot. |
| Winding Bar | `bar_thick` | 6.0 mm | Bar thickness (Roller mode ≥ 9 mm). |
| Winding Bar | `bar_height` | 14.0 mm | Bar height = how much tube winds on. |
| Turn Handle | `handle` | on | Winged tabs (on) or rod cross-hole (off). |
| Turn Handle | `rod_dia` | 6.5 mm | Cross-hole diameter when tabs are off. |

## Presets

- **Toothpaste (winged)** — the everyday 35 mm tube, finger wings.
- **Cosmetic Tube (rod)** — narrower tube, rod hole for leverage.
- **Paint / Ointment Roller** — wide roller variant with a rod hole.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Tube Slot** (`profile`, internal) — the winding interface, defined by
    `tube_width`, `slot_width`, and `bar_thick`. The slot cross-section is the
    contract: any key with a slot sized to the tube's crimp width and thickness
    winds that tube, so one profile spans a whole family of tube sizes.
- **Material awareness:** `slot_width` is exposed so the fit for the crimped
  metal/plastic seam can be tuned per material and printer; `tolerance_by_material`
  is declared.
- **Societal benefit:** recovers the 5–15 % of product left in a tube that is
  otherwise thrown away — a reusable printed key that reduces waste and stretches
  every tube of toothpaste, ointment, glue, or paint.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The bar is a solid block; the slot and rod hole are cut with cutters that
  overshoot the faces and the wings are unioned — so both modes, both handle
  styles, and the parameter extremes render **watertight**.
