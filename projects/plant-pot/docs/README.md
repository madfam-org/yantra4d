# Drainage Plant Pot & Saucer

A tapered plant pot with a real drainage array in the floor, a matching drip
saucer, and a hanging variant with cord lugs. Generated with **CadQuery** (B-Rep).
Sized by rim diameter and height with an adjustable wall taper so pots nest for
storage and shipping.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Distinct from the self-watering **planter** cartridge: this is a classic
> free-draining nursery pot plus saucer and hanging option, not a reservoir system.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Drainage Pot** | `pot` | Tapered vessel with a central + ring drainage array, optional rolled rim and foot ring. |
| **Drip Saucer** | `saucer` | A shallow nesting tray with an inner support ridge to keep the pot above caught water. |
| **Hanging Pot** | `hanging_pot` | The pot plus 2–6 pierced lugs on the rim for cord or wire. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shape | `pot_dia` | 120 mm | Inner rim diameter. |
| Shape | `pot_h` | 110 mm | Pot height. |
| Shape | `taper` | 12 mm | Base narrowing per side (enables nesting). |
| Walls & Floor | `wall` | 3.0 mm | Side wall thickness. |
| Walls & Floor | `floor` | 4.0 mm | Floor thickness. |
| Walls & Floor | `rim_lip` | on | Rolled top rim. |
| Walls & Floor | `foot_ring` | on | Raised foot ring for drainage clearance. |
| Drainage & Extras | `drain_dia` | 10 mm | Drainage hole diameter. |
| Drainage & Extras | `drain_ring` | 6 | Ring holes (plus one central). |
| Drainage & Extras | `saucer_h` | 22 mm | Saucer wall height. |
| Drainage & Extras | `hang_lugs` | 3 | Hanging lugs (hanging pot). |
| Drainage & Extras | `lug_hole` | 6 mm | Cord hole per lug. |

## Presets

- **Succulent Pot** — small, shallow, few drain holes.
- **Herb Pot Saucer** — a 120 mm-class drip tray.
- **Hanging Fern** — mid-size pot with three cord lugs.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Pot Drainage** (`surface`, internal) — the floor drainage geometry defined by
    `drain_dia`, `drain_ring`, `floor`, `taper`. The same drainage surface and
    tapered footprint mean the pot always seats correctly on the matching saucer.
- **Material awareness:** wall/floor and hole sizes are exposed so the pot can be
  tuned for recycled or waste-stream filament and print shrinkage;
  `tolerance_by_material` is declared.
- **Societal benefit:** nursery pots are single-use plastic thrown away by the
  billion — a printable, right-sized pot with real drainage lets households grow
  and propagate food from recycled filament.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. The rolled rim and the
  drain ring are wrapped in try/except so extreme inputs still build watertight.
- All shipped presets and every mode render **watertight**.
