# Bike Bottle Cage

A water-bottle cage that bolts to a bicycle frame's standard water-bottle bosses,
generated with **CadQuery** (B-Rep). Sized by the bottle diameter so the cradle
grips a 73 mm bidon. The **64 mm M5 boss pattern** is the shared interface every
frame in the world exposes.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Side-Entry Cage** | `cage` | Two C-bands on a spine; bottle springs in from the front. |
| **Top-Entry Cage** | `top_entry_cage` | Deep cup + broad upper loop; bottle drops in the top. |
| **Accessory Holder** | `accessory_mount` | Boss-mounted holder for a tool/CO2/spares canister. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bottle & Cradle | `bottle_dia` | 73 mm | Bottle diameter (bidon ≈ 73-74 mm). |
| Bottle & Cradle | `grip` | 210° | How far each band wraps the bottle. |
| Bottle & Cradle | `band_w` / `band_t` | 12 / 4 mm | Cradle band width / thickness. |
| Bottle & Cradle | `tool_dia` | 40 mm | Accessory canister diameter. |
| Frame Boss | `boss_space` | 64 mm | Boss spacing (64 std / 50 / 72). |
| Frame Boss | `spine_w` | 18 mm | Backbone spine width. |
| Frame Boss | `bolt_dia` | 5.5 mm | M5 bolt clearance hole. |

## Presets

- **Standard Bidon (73 mm)** — side-entry cage on 64 mm bosses.
- **MTB Top-Entry** — top-entry for tight front triangles.
- **Tool / CO2 Canister** — boss-mounted accessory holder.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Bottle Boss** (`bolt_pattern`, *water-bottle boss*) — the two-M5 frame
    mount, defined by `boss_space`, `bolt_dia`, and indexed to `bottle_dia`.
  - **Bottle Cradle** (`socket`, internal) — the curved band cradle, `bottle_dia`,
    `grip`, `band_w`, `band_t`.
- **Material awareness:** `tolerance_by_material` declared — band grip and bolt
  fit adapt to the printed material.
- **Societal benefit:** every frame exposes the same 64 mm boss pattern; a
  printable cage sized to any bottle keeps riders hydrated without brand hardware.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Cradle bands are annulus rings with a pie-mouth cut for the entry opening;
  bands, spine, and boss plate all overlap volumetrically for a watertight union.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
