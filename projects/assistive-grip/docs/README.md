# Assistive Grip / Utensil Aid

A grip aid that slips over a utensil, pen, or tool handle to enlarge it for users
with limited hand dexterity. Generated with **CadQuery** (B-Rep) and sized to the
handle it fits over.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cylindrical Grip** | `grip` | Plain slip-on tube; supports the `shape` selector (cylindrical / bulb / triangular). |
| **Bulb Grip** | `bulb_grip` | Fatter in the middle for a relaxed power grasp. |
| **Strap Grip** | `strap_grip` | A grip with a transverse strap slot for a hand strap. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the
dispatched values (`grip` / `bulb_grip` / `strap_grip`) so every mode renders its
own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Handle Fit | `handle_dia` | 8 mm | Diameter of the handle the grip slips over. |
| Handle Fit | `clearance` | 0.4 mm | Radial slip gap over the handle. |
| Grip Shape | `grip_dia` | 32 mm | Enlarged outer diameter. |
| Grip Shape | `length` | 95 mm | Overall length. |
| Grip Shape | `shape` | cylindrical | `cylindrical`, `bulb`, or `triangular`. |
| Grip Shape | `bulb_gain` | 1.35 | Mid-swell factor for the bulb shape. |
| Grip Shape | `strap` | off | Add a strap slot (grip mode). |

## Presets

- **Cutlery Enlarger** — an 8 mm handle built up to a 32 mm cylindrical grip.
- **Pen Bulb Grip** — a bulb profile for writing.
- **Tool Grip + Strap** — a larger grip with a hand-strap slot.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Utensil Handle Bore** (`socket`, internal) — the through bore that receives
    the handle, defined by `handle_dia` and `clearance`. Any utensil whose handle
    matches `handle_dia` (within `clearance`) seats in the grip.
- **Material awareness:** `clearance` is exposed so the slip/friction fit can be
  tuned for rigid (PLA/PETG) or soft (TPU) filament; `tolerance_by_material` is
  declared.
- **Societal benefit:** built-up handles are a core occupational-therapy aid for
  arthritis, tremor, and reduced grip strength — restoring independent eating,
  writing, and tool use at near-zero cost.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- The outer body is one solid (cylinder, lofted bulb, or unioned rounded triangle)
  with a single clean through bore; the strap slot never opens the bore — all
  shipped presets render **watertight**.
