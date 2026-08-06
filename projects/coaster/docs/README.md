# Coaster / Trivet

A patterned disc generated with **CadQuery** (B-Rep) that protects a surface from
a cold drink or a hot pot. Round, square, or hex outline; an optional raised edge
lip catches condensation; and a top pattern (solid, grid cutout, concentric rings,
or honeycomb) adds style while saving material.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Coaster** | `coaster` | The small drink rest. |
| **Trivet** | `trivet` | A larger, thicker version for hot cookware (min Ø 150, min 6 mm thick). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Outline & Size | `diameter` | 95 mm | Outer Ø (round) or width across flats (square / hex). |
| Outline & Size | `thickness` | 5.0 mm | Solid base thickness below the pattern. |
| Outline & Size | `shape` | round | `round` / `square` / `hex`. |
| Edge Lip | `lip_height` | 2.5 mm | Raised rim to catch condensation (0 = flat). |
| Edge Lip | `lip_wall` | 3.0 mm | Thickness of the rim ring. |
| Top Pattern | `pattern` | grid-cutout | `solid` / `grid-cutout` / `concentric-rings` / `honeycomb`. |
| Top Pattern | `pattern_depth` | 2.0 mm | Cut depth; auto-clamped to keep a solid floor. |

## Presets

- **Round Grid Coaster** — 95 mm round, grid cutout, 2.5 mm lip.
- **Hex Honeycomb Coaster** — 100 mm hex, honeycomb, 3 mm lip.
- **Square Ring Trivet** — 180 mm square, concentric rings, flat (no lip).

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Patterned Disc** (`surface`, internal) — the top-face pattern field bounded
    by the outline and lip, defined by `diameter`, `shape`, `pattern`,
    `pattern_depth`, `lip_height`.
- **Material awareness:** `tolerance_by_material` declared; the pattern reduces
  material use versus a solid puck.
- **Societal benefit:** a first-print staple that protects furniture from rings
  and heat damage; the same geometry scales from drink coaster to cookware trivet.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Pattern cutters are intersected with the interior field so no channel breaches
  the outline or lip wall — every preset and extreme renders **watertight**.
