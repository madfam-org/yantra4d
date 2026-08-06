# PCO-1881 Bottle Cap

A reusable screw cap for the **PCO-1881** soda / water bottle neck — the world's
most abundant standardized vessel. Generated with **CadQuery** (B-Rep). The
functional interface is a **real single-start helical thread** (27.43 mm thread
major diameter, 2.7 mm pitch) that mates with the same PCO-1881 neck used by the
`bottle-thread`, `bird-feeder`, `faircap-filter`, and `pet-dispenser` cartridges.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Simple Cap** | `simple_cap` | A plain PCO-1881 female-threaded cap with a sealed top and grip knurl — a drop-in replacement for a lost bottle cap. |
| **Tethered Cap** | `tethered_cap` | The same cap joined by a flexible strap to an anchor ring that slips over the bottle neck, so the cap can never be lost. |
| **Sport Spout Cap** | `sport_cap` | A cap with a raised drink spout and a through bore you sip from — turns a throwaway soda bottle into a reusable sport bottle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread & Fit | `clearance` | 0.4 mm | Per-side printed-thread slop (0.3–0.5 typical). |
| Thread & Fit | `turns` | 3.5 | PCO-1881 engagement turns (snapped to a half-integer internally). |
| Cap Body | `wall` | 2.6 mm | Radial wall around the thread. |
| Cap Body | `top_th` | 2.4 mm | Sealed-top thickness. |
| Cap Body | `skirt_h` | 3.0 mm | Plain wall below the thread for grip / seal lead-in. |
| Cap Body | `grip_knurl` | on | Vertical grip flutes. |
| Tether | `tether_len` | 26 mm | Strap span between cap and anchor ring. |
| Tether | `ring_id` | 26 mm | Anchor-ring bore over the bottle neck. |
| Sport Spout | `spout_dia` | 7 mm | Drink-spout bore. |
| Sport Spout | `spout_h` | 14 mm | Spout height above the cap. |

## Presets

- **Replacement Soda Cap** — the everyday plain replacement cap.
- **Anti-Loss Tethered Cap** — cap + strap + neck ring.
- **Sport Drink Spout** — the reusable sport-bottle spout.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **PCO-1881 Neck Thread** (`thread`, PCO 1881) — the female bottle-neck thread,
    defined by `clearance`, `turns`, `wall`. **Compatible with** `bottle-thread`,
    `bird-feeder`, `faircap-filter`, and `pet-dispenser`: any bottle those cartridges
    thread onto, this cap fits, and vice versa.
- **Material awareness:** `clearance` is exposed so the printed thread fit can be
  tuned per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** a lost or broken cap normally sends an otherwise-good bottle
  to the bin; an on-demand PCO-1881 cap keeps it in service, and the tethered and
  sport variants convert a single-use soda bottle into a durable reusable bottle.
- **License:** CERN-OHL-W-2.0

## Food contact & material responsibility

This cap can touch drinking water and beverages. FDM prints are **not inherently
food-safe**: layer lines harbor bacteria and many filaments and colorants are not
food-contact rated. If you use this cap with anything you will drink, that is
**your responsibility** — choose a filament certified for food contact, print with
a clean (ideally dedicated) nozzle, and consider a food-safe sealing coat or a
disposable liner. For repeated use, treat printed drinkware as short-lived and
replace it often.

## Thread modeling notes (watertight + fast)

- Threads are **volumetric fused helical ribs**: a trapezoidal profile swept along a
  genuine `makeHelix` path and unioned into the bore wall, with the rib root pushed
  into the wall so the boolean is a clean fusion (not a fragile tangent kiss).
- The turn count is forced to a **half-integer** (`floor(n)+0.5`). A whole-integer
  turn count degenerates the OCCT helical sweep into a negative-volume / null body;
  a half-integer is well-conditioned and far faster. Modeled turns are also capped so
  the tall multi-turn sweep stays watertight at every setting.

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. No cross-file imports.
