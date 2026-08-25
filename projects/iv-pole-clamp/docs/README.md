# IV Pole Clamp

The **mounting spine of the ward**, generated with **CadQuery** (B-Rep). A split
clamp that grips a round IV pole (19–25 mm is the usual range) and presents a
**dovetail accessory face**. Anything that speaks the same dovetail — starting with
`drip-chamber-holder` — slides on and locks without a second tool.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **A printed clamp is a convenience mount, not a certified device.** Do NOT hang
> an infusion pump, a patient-load device, or anything whose fall would injure
> someone. Verify the grip under the intended load first.

## Why this cartridge exists

Ward equipment mounting is a permanent low-grade improvisation: tape, gauze ties,
and bent coat hangers, because the manufacturer's bracket is proprietary,
discontinued, or costs more than the item it holds. The **pole-Ø series** published
here is what makes this the CDG spine for the other clinical picks: a clamp and an
accessory generated at the same `pole_dia` are guaranteed to share a pole, and
because the dovetail is published **separately**, an accessory author never needs to
know the pole size at all.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Dovetail Clamp** | `dovetail_clamp` | Split clamp + pinch bolt + dovetail accessory face. |
| **Bag-Hook Clamp** | `hook_clamp` | The same clamp carrying a bag hook instead of a dovetail. |
| **Dovetail Shoe** | `dovetail_shoe` | The mating shoe alone — the piece an accessory inherits to ride any clamp. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pole | `pole_dia` | 22.0 mm | Pole outer diameter — 19 / 22 / 25 mm covers most ward poles. |
| Pole | `grip_fit` | 0.3 mm | Per-side bore clearance before the bolt is pinched. |
| Pole | `wall` | 6.0 mm | Ring wall — this carries the whole load. |
| Pole | `clamp_h` | 26.0 mm | Height along the pole; taller resists tipping under an offset load. |
| Pinch | `kerf` | 2.2 mm | Split-kerf width. |
| Pinch | `bolt_dia` | 5.3 mm | Pinch bolt clearance (5.3 = M5). |
| Pinch | `nut_af` | 8.1 mm | Captive nut pocket across flats (8.1 = M5). |
| Accessory | `dove_w` | 18.0 mm | Dovetail width — keep equal on clamp and accessory. |
| Accessory | `dove_h` | 8.0 mm | Dovetail projection. |
| Accessory | `dove_angle` | 60 deg | Flank angle. |
| Accessory | `hook_len` | 26.0 mm | Bag-hook reach (hook clamp only). |

## Presets

- **Standard 22 mm Pole** — the default ward pole.
- **Slim 19 mm Pole** — the narrower series member.
- **Bag Hook (25 mm)** — a hook instead of a dovetail.
- **Accessory Shoe Blank** — the interface piece on its own.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **IV Pole Diameter Series** (`socket`, 19 / 22 / 25 mm ward poles) —
    `pole_dia`, `grip_fit`, `wall`, `clamp_h`. Compatible with
    `drip-chamber-holder`.
  - **Accessory Dovetail Face** (`rail`, internal) — `dove_w`, `dove_h`,
    `dove_angle`. Compatible with `drip-chamber-holder` and `rail-mount`.
  - **Pinch Bolt & Captive Nut** (`bolt_pattern`, M5) — `bolt_dia`, `nut_af`, `kerf`.
- **Material awareness:** `grip_fit` and `wall` are exposed for per-printer and
  per-material tuning; `tolerance_by_material` is declared.
- **Societal benefit:** one clamp per pole, then any number of accessories against
  a face whose geometry never changes.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- **Watertight strategy:** the clamp is one extruded solid. The pole bore is a
  single through-cut; the split kerf is one thin slot from the bore out to the rim;
  the pinch-bolt hole is cross-drilled **after** the ears are unioned on. The
  dovetail is a trapezoid prism unioned to the back with a deliberate 0.2 mm
  overlap, so it can never be a separate body. The kerf is clamped narrower than
  the wall it passes through, so **the ring can never be severed** at any extreme.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
