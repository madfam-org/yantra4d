# Guy-Line Adapter Set

Lightweight tent and tarp hardware sized to your guy-line cord, generated with
**CadQuery** (B-Rep). A friction line tensioner, a grommet-free tarp edge clip,
and a pole tip — the cord-hole geometry is shared across the whole set.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Line Tensioner** | `line_tensioner` | 2-4 hole friction adjuster for the guy-line. |
| **Tarp Clip** | `tarp_clip` | C-jaw that pinches a tarp edge and offers a cord hole. |
| **Pole Tip** | `pole_tip` | Cone cap with a cord notch for an improvised pole. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cord & Body | `cord_dia` | 3 mm | Guy-line cord diameter — sizes every hole. |
| Cord & Body | `thick` | 5 mm | Tensioner plate / clip jaw thickness. |
| Variant Options | `holes` | 3 | Tensioner cord holes (3 = classic triangle). |
| Variant Options | `tarp_gap` | 2 mm | Tarp edge thickness the clip pinches. |
| Variant Options | `pole_dia` | 16 mm | Stick/pole diameter the tip caps. |

## Presets

- **Standard 3-Hole Tensioner** — the classic triangle friction adjuster.
- **Tarp Tie-Out Clip** — grommet-free tarp tie-out.
- **Improvised Pole Tip** — caps a 16 mm stick.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Guy-Line Tensioner** (`snap`, internal) — the friction adjuster geometry,
    defined by `cord_dia`, `thick`, `holes`.
  - **Cord Hole** (`socket`, internal) — the shared cord clearance hole,
    `cord_dia`.
- **Material awareness:** `tolerance_by_material` declared — cord holes and tarp
  grip adapt to the printed material.
- **Societal benefit:** guy-line hardware is trivially lost and costly; a printable
  set sized to any cord lets campers and relief shelters pitch with scrap line.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
