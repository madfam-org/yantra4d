# Squeeze Bottle Nozzle

A precision dispensing nozzle for squeeze / dispenser bottles that use the common
**"410" personal-care neck finishes: 28-410 (28 mm) and 24-410 (24 mm)**. Generated
with **CadQuery** (B-Rep). The functional interface is a **real 410-series female
helical thread** (~3.18 mm pitch) — the same 28 mm bottle neck the `filter-straw`
cartridge threads onto.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cone Nozzle** | `cone_nozzle` | Female 410 thread + a tapered precision cone with a small tip orifice — cut the tip back with a knife to open the bore wider (classic twist-cap style). |
| **Needle Applicator** | `needle_nozzle` | Female 410 thread + a long thin needle tube for fine, precise flow (adhesives, oils, flux). |
| **Drip Dome** | `drip_nozzle` | Female 410 thread + a low dome with a single tiny centre orifice for controlled drip / drop dispensing. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Neck & Fit | `neck` | 28-410 | 28 mm or 24 mm dispenser neck finish. |
| Neck & Fit | `clearance` | 0.4 mm | Per-side printed-thread slop. |
| Neck & Fit | `turns` | 1.5 | 410 turns (snapped to a half-integer internally). |
| Nozzle Body | `wall` | 2.2 mm | Radial wall around the thread. |
| Nozzle Body | `top_th` | 2.2 mm | Closed shoulder thickness under the nozzle. |
| Nozzle Body | `grip_knurl` | on | Vertical grip flutes on the collar. |
| Cone Tip | `cone_h` | 18 mm | Cone height. |
| Cone Tip | `tip_dia` | 2.0 mm | Tip orifice diameter. |
| Needle | `needle_len` | 30 mm | Needle length. |
| Needle | `needle_od` | 4.0 mm | Needle outer diameter. |
| Needle | `needle_id` | 1.5 mm | Needle bore (flow diameter). |
| Drip | `drip_dia` | 1.2 mm | Single drip orifice diameter. |
| Drip | `dome_h` | 6.0 mm | Drip dome height. |

## Presets

- **28 mm Precision Cone** — the cuttable tapered tip.
- **Fine Glue Needle** — a 24 mm-neck needle applicator.
- **Controlled Drip** — the dropper-style drip dome.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **410 Dispenser Neck Thread** (`thread`, 28-410 / 24-410) — the female
    dispenser-neck thread, defined by `neck`, `clearance`, `turns`, `wall`.
    **Compatible with** `filter-straw`, which threads onto the same 28 mm bottle
    neck.
- **Material awareness:** `clearance` is exposed so the printed thread fit can be
  tuned per material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** commercial precision nozzles are sold pre-set to one orifice
  and one length and thrown away with the bottle; a printed 410 nozzle lets anyone
  match the tip exactly to the task and refit it to any refill bottle, turning a
  disposable dispenser into a precise, reusable tool.
- **License:** CERN-OHL-W-2.0

## Food / skin contact & material responsibility

These nozzles may dispense personal-care products, condiments, or other substances
that contact skin or food. FDM prints are **not inherently food-safe**: layer lines
harbor bacteria and many filaments and colorants are not food-contact or
skin-contact rated. Matching the filament to the intended contents is **your
responsibility** — choose an appropriately rated filament, print with a clean nozzle,
and treat printed contact parts as short-lived.

## Thread modeling notes (watertight + fast)

- Threads are **volumetric fused helical ribs** swept along a genuine `makeHelix`
  path and unioned into the bore wall.
- The turn count is forced to a **half-integer** (`floor(n)+0.5`); a whole-integer
  count degenerates the OCCT helical sweep into a null body.
- **The socket has a closed shoulder.** An open-ended threaded socket terminates the
  helical rib at a free rim and tessellates non-watertight; the dispensing channel
  is bored through the shoulder afterward.

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. No cross-file imports.
