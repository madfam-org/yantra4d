# Math Manipulatives / Solids

Geometric manipulatives for the maths classroom, generated with **CadQuery**
(B-Rep): the five **Platonic solids**, a regular **N-gon prism** for surface-area
and volume lessons, and pie-slice **fraction tiles** that snap into a whole
circle. All pieces share a **40 mm nominal size** so a set is comparable and
stackable.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Platonic Solid** | `platonic` | A selectable regular polyhedron — tetrahedron (4), cube (6), octahedron (8), dodecahedron (12) or icosahedron (20) — at a target circumscribed size, resting on the desk. |
| **N-gon Prism** | `prism` | A regular polygon prism (parametric sides + height) for *area = ½·n·s·a* and *volume = base-area × height*. |
| **Fraction Tile** | `fraction_tile` | A 1/`denominator` pie slice (a circular sector, optionally an annulus) — print `denominator` tiles to build a whole circle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Platonic Solid | `solid` | cube | Which of the five regular polyhedra. |
| Platonic Solid | `size` | 40.0 mm | Circumscribed (vertex-sphere) diameter. |
| Prism | `sides` | 6 | Polygon sides (3 = triangle, 6 = hexagon). |
| Prism | `prism_dia` / `prism_h` | 40.0 / 30.0 mm | Across-corners diameter and height. |
| Fraction Tile | `denominator` | 4 | Tile = 1/denominator of a whole circle. |
| Fraction Tile | `tile_dia` / `tile_h` | 40.0 / 8.0 mm | Whole-circle outer diameter and thickness. |
| Fraction Tile | `tile_hole` | 0.0 mm | Optional centre hole → annular sector. |

## Why these are exact (and watertight)

The Platonic solids are built from their **exact vertex + face tables** — real
polyhedra, not faceted approximations — so face, edge and vertex counts are
correct for discovering **Euler's formula** *V − E + F = 2*. Because a convex
polyhedron built from planar faces is watertight by construction, every solid
prints as a clean single body. The prism is one extrusion of a regular polygon,
and the fraction tile is one extrusion of a closed sector wire (two radii and an
arc); `denominator` tiles at the same `tile_dia` reassemble into an exact whole,
which is the point of the manipulative.

## Presets

- **Icosahedron (d20)** — the 20-face solid, a familiar die.
- **Hexagonal Prism** — a 6-side prism for area/volume work.
- **Quarter Tiles (1/4)** — four tiles make a whole circle.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **40 mm Nominal Size** (`surface`, *internal solids 40mm*) — the shared
    reference size (`size` / `prism_dia` / `tile_dia`) that makes the set
    comparable.
  - **Whole-Circle Fraction Sector** (`profile`, *internal*) — the sector angle
    `2π/denominator` at `tile_dia`; tiles of one `tile_dia` tile a full circle.
- **Material awareness:** none required — these are solid reference bodies with
  no fit-critical mating surface, so no material toggle is exposed.
- **Societal benefit:** hands-on solids and fraction tiles make geometry and
  number sense concrete; a full comparable set prints from open files for a few
  grams of filament instead of a commercial kit, so any classroom can equip
  every student.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Platonic solids are constructed as polyhedra from exact vertex/face tables
  (watertight by construction); the prism is a single polygon extrusion; the
  fraction tile is a closed-sector extrusion (annulus shares both radii, staying
  one solid). No spheres or oblique curved booleans. All shipped options and
  extreme-parameter cases render **watertight**, single-body.
