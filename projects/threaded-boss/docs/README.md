# Threaded Insert / Boss

A **mounting boss** generated with **CadQuery** (B-Rep), sized for a **heat-set
threaded insert** (or a self-tapping screw). The boss is a printed cylinder whose
bore accepts a brass insert melted flush with a soldering iron — giving a reusable
metal thread in a printed part. Metric sizes **M2–M6** with correct heat-set bore
diameters, standalone-flange or in-wall mounts, optional gusset ribs, and a
multi-boss strip.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Parts

| Part | Description |
| :--- | :--- |
| **Boss** (`boss`) | A single boss on a standalone flange (fixing holes) or an in-wall plate segment. |
| **Ribbed Boss** (`boss_ribbed`) | The same boss reinforced with triangular gusset ribs. |
| **Boss Strip** (`boss_strip`) | A row of N bosses on one common base at a pitch. |

The studio dispatches the active part via `target_part`.

## Heat-set insert table

| `insert_size` | Insert-hole Ø | Screw-clear Ø | Min boss Ø |
| :--- | :--- | :--- | :--- |
| `M2` | 3.2 mm | 2.4 mm | 6.0 mm |
| `M2.5` | 3.5 mm | 3.0 mm | 6.5 mm |
| `M3` | 4.0 mm | 3.4 mm | 7.0 mm |
| `M4` | 5.6 mm | 4.5 mm | 9.0 mm |
| `M5` | 6.4 mm | 5.5 mm | 10.5 mm |
| `M6` | 8.0 mm | 6.6 mm | 12.5 mm |

The bore is the **insert-hole** diameter: a touch under the insert OD so the
melted brass grips the plastic. Values follow common tapered heat-set inserts
(CNC Kitchen / Ruthex style). Boss outer diameter auto-sizes to ~2.4× the bore
(honouring the table minimum) unless `boss_od` is set explicitly.

## Mounts (`mount`)

| Mount | Base |
| :--- | :--- |
| `standalone` | A round flange with two fixing holes to glue or screw the boss down. |
| `in_wall` | A rectangular wall / plate segment the boss projects from. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Insert & Boss | `insert_size` | `M3` | Metric size → bore diameter (see table). |
| Insert & Boss | `boss_od` | 0 (auto) | Boss outer Ø; 0 auto-sizes to ~2.4× the bore. |
| Insert & Boss | `boss_height` | 10.0 mm | Boss height above the base. |
| Insert & Boss | `through` | off | Through-bore vs a blind bore with a floor. |
| Mount | `mount` | `standalone` | Flange or in-wall plate segment. |
| Mount | `base_thick` | 3.0 mm | Flange / wall thickness. |
| Mount | `base_margin` | 5.0 mm | Base material beyond the boss. |
| Ribs | `ribs` | off | Add triangular gusset ribs. |
| Ribs | `rib_count` | 4 | Number of ribs. |
| Strip | `strip_count` | 3 | Bosses in a strip. |
| Strip | `strip_pitch` | 25.0 mm | Centre-to-centre pitch. |

## Presets

- **M3 PCB Standoff** — a plain M3 blind boss for standing a board off a base.
- **M4 Ribbed Mount** — a taller M4 boss with 4 gusset ribs for load.
- **M3 Boss Strip ×4** — four M3 bosses at 20 mm pitch on one bar.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Heat-Set Insert Bore** (`socket`, internal) — the insert interface, defined
    by `insert_size` (→ bore diameter), `boss_od`, `boss_height`, `through`. Any
    boss at the same `insert_size` accepts the same brass insert and screw.
- **Material awareness:** the insert bore is deliberately under-sized for the melt
  grip and `tolerance_by_material` is declared, so the bore can be nudged for
  stiffer or recycled filaments.
- **Societal benefit:** heat-set bosses give printed parts reusable metal threads
  that survive repeated assembly — the difference between a throwaway print and a
  repairable product.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The boss overlaps its base for a watertight union and the bore overshoots both
  faces on through-bores; every shipped preset, part, and extreme renders **watertight**.
