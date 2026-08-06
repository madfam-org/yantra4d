# Universal Cup Lid

A press-fit lid for mugs and cups generated with **CadQuery** (B-Rep), sized by
the **outer rim diameter** (`rim_dia`). A downward seal skirt hugs the rim OD and a
shallow inward **grip bead** pinches it by a set interference, so the lid clicks on
and stays. Sip, solid, or straw opening.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Sip Lid** | `sip_lid` | Obround drink opening near the edge (travel-mug style). |
| **Solid Cover** | `solid_lid` | No opening — a splash / keep-warm cover. |
| **Straw Lid** | `straw_lid` | Centered straw hole with a sealing collar. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rim & Seal | `rim_dia` | 82 mm | **Cup OUTER rim diameter — measure across the top.** |
| Rim & Seal | `rim_wall` | 2.2 mm | Skirt + top wall thickness. |
| Rim & Seal | `skirt_h` | 12 mm | How far the skirt grips down over the rim. |
| Rim & Seal | `interference` | 0.4 mm | How hard the grip bead pinches the rim. |
| Top | `top_dome` | 3.0 mm | Slight dome rise (0 = flat). |
| Opening | `sip_dia` | 16.0 mm | Sip opening size (sip lid). |
| Opening | `straw_dia` | 8.0 mm | Straw hole diameter (straw lid). |

## Presets

- **Coffee Mug Sip Lid** — 82 mm rim, 16 mm sip opening.
- **Keep-Warm Cover** — 90 mm rim, no opening.
- **Tumbler Straw Lid** — 88 mm rim, 10 mm straw hole.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:**
  - **Cup Rim Seal** (`snap`, internal) — the press-fit interface, defined by
    `rim_dia`, `rim_wall`, `skirt_h`, `interference`. Any cup whose rim OD equals
    `rim_dia` seats in the skirt. **Verified grip:** at defaults the skirt inner
    wall (r = 41.0 mm) clears the rim OD and the grip bead crest (r = 40.6 mm)
    bites inward by exactly the 0.40 mm interference, so the lid snaps on and grips.
- **Material awareness:** the grip `interference` is exposed so the seal fit can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** one printable lid fits any cup measured at the rim,
  replacing lost or single-use lids across a household's mismatched cups.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The grip bead is a **revolved profile fused to the skirt** (volumetric union) so
  the mesh stays watertight; openings are cut as independent solids to avoid
  multi-wire workplane state.
- The script is **self-contained** (sandbox-safe): parameters via
  `PARAM(lambda: name, default)`; the final solid is assigned to `result`.
