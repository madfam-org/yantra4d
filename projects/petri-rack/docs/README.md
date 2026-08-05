# Petri / Sample Storage Rack

Racks that store or stack petri dishes and round sample containers, generated with
**CadQuery** (B-Rep). Set the dish diameter (90 mm standard) and slot count, then
choose how the dishes are held.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Edge Rack (slots)** | `edge_rack` | Two comb walls whose notches hold dishes standing on edge, like records. |
| **Stack Holder** | `stack_holder` | A ring tube with windows that holds one vertical stack of dishes. |
| **Drying Rack** | `drying_rack` | A base of ring pedestals; an inverted dish air-dries on each. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the
dispatched values (`edge_rack` / `stack_holder` / `drying_rack`). The `orientation`
selector mirrors the mode (`stacked` -> stack holder) for the preview path.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Dish | `dish_dia` | 90 mm | Dish/container outer diameter. |
| Dish | `dish_h` | 15 mm | One dish's stacked height (stack mode). |
| Rack | `orientation` | vertical | Mirrors the active mode. |
| Rack | `stacks` | 6 | Edge slots, or dishes in the stack. |
| Rack | `slot_gap` | 4.0 mm | Slot channel width (edge mode). |
| Rack | `wall` | 3.0 mm | Comb / ring wall thickness. |
| Rack | `clearance` | 1.5 mm | Radial gap around the dish. |

## Presets

- **90 mm Edge Rack (x6)** — six dishes stored on edge.
- **Stack Tower (x8)** — an eight-dish stack holder.
- **Drying Rack (x4)** — four ring pedestals for inverted drying.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Dish Slot Array** (`grid`, *90mm petri*) — the dish-holding geometry
    (slot pitch, stack ring, or pedestal ring), defined by `dish_dia`, `stacks`,
    `slot_gap`, `clearance`. Sizing to 90 mm matches the standard petri dish.
- **Material awareness:** `clearance` is exposed so the dish fit can be tuned per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** organized, ventilated dish storage keeps cultures and
  samples separated and labelled; sizing to the exact dish on hand lets clinics,
  teaching labs, and makerspaces store consumables without format-locked racks.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- Bases are solid slabs, edge slots are notches cut in raised combs, the stack
  ring keeps solid posts between its windows, and drying pedestals are unioned
  rings — all shipped presets render **watertight**.
