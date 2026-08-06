# Bottle-Fed Bird Feeder

Turns a discarded PET soda bottle into a gravity bird / seed feeder. Generated
with **CadQuery** (B-Rep). The feeder cap screws onto a standard **PCO-1881**
bottle neck — the same thread the `bottle-thread` cartridge uses — and seed flows
down through rounded ports onto a catch tray with perches.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Feeder Cap** | `feeder_cap` | A PCO-1881 female-threaded cap with a rain-shedding skirt and seed ports; screw an inverted bottle in. |
| **Tray Base** | `tray_base` | A round catch tray with a domed center, a central boss, and radial perches. |
| **Tube Feeder** | `tube_feeder` | A standalone closed tube reservoir on a tray with base ports and perches — no bottle needed. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bottle Thread | `turns` | 1.5 | PCO-1881 engagement turns. |
| Bottle Thread | `clearance` | 0.4 mm | Per-side printed-thread slop. |
| Bottle Thread | `wall` | 2.6 mm | Cap / tray / tube wall. |
| Seed & Ports | `port_count` | 3 | Feeding ports around the body. |
| Seed & Ports | `port_size` | 14 mm | Port opening (match seed size). |
| Tray & Perch | `tray_dia` | 110 mm | Catch-tray diameter. |
| Tray & Perch | `tray_wall_h` | 16 mm | Tray lip height. |
| Tray & Perch | `perch_len` | 32 mm | Perch reach past the tray. |
| Tray & Perch | `perch_dia` | 8 mm | Perch rod diameter. |
| Tube Reservoir | `tube_h` | 140 mm | Reservoir height (tube feeder). |
| Tube Reservoir | `tube_dia` | 60 mm | Reservoir diameter (tube feeder). |

## Presets

- **Soda-Bottle Cap** — the classic invert-a-bottle feeder cap.
- **Catch Tray + Perch** — the tray that pairs with the cap.
- **Standalone Tube** — a self-contained tube feeder.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **PET Bottle Neck** (`thread`, PCO 1881) — the female bottle-neck thread on the
    feeder cap, defined by `turns`, `clearance`, `wall`. **Compatible with** the
    `bottle-thread` cartridge, so any bottle its caps fit also fits this feeder, and
    vice versa.
- **Material awareness:** `clearance` is exposed so the printed bottle-thread fit
  can be tuned per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** backyard feeders support pollinators and songbirds under
  habitat pressure; reusing a PET bottle keeps it out of the waste stream and makes
  the feeder essentially free.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- The **bottle thread** uses the volumetric-rib idiom — a trapezoidal profile swept
  along a `makeHelix`, unioned into the wall with an `overlap` for a watertight
  mesh. Seed ports are rounded through-cuts so the boolean stays clean at every
  size.
- All shipped presets and every mode render **watertight** (verified through the
  full extreme-parameter corner).
