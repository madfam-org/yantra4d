# Glasses Holders

Holders for glasses and sunglasses generated with **CadQuery** (B-Rep), all built
around one sprung **temple cradle** that grips an eyewear temple arm. A visor clip
for the car sun visor, a wall hook, and a desk stand.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Visor Clip** | `visor_clip` | A C-clip that slides onto a car sun visor, carrying a temple cradle so glasses hang from the visor. |
| **Wall Hook** | `wall_hook` | A screw-mounted wall plate with a temple cradle on an arm. |
| **Desk Stand** | `desk_stand` | A wide-foot stand with an upright post and a temple cradle so glasses perch upright. |

The `mount` select mirrors the three modes for UI discovery; the mode's `parts[]`
id (injected as `target_part`) is the authority for which part is built.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Temple Cradle | `temple_w` / `temple_t` | 5.0 / 4.0 mm | Temple arm cross-section the cradle grips. |
| Temple Cradle | `cradle_w` | 16 mm | Cradle length along the temple. |
| Mount | `mount` | visor-clip | Visor / wall / desk (mirrors the mode). |
| Mount | `visor_t` | 18 mm | Sun-visor thickness the clip grips. |
| Mount | `stand_h` | 70 mm | Desk-stand post height. |
| Build | `wall` | 3.0 mm | Wall thickness. |

## Presets

- **Car Visor Clip** — grips an 18 mm sun visor.
- **Entryway Wall Hook** — a screw-mount wall hook.
- **Bedside Stand** — a 70 mm desk stand.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Temple Cradle** (`snap`, internal) — the sprung V-notch that grips the
    eyewear temple, defined by `temple_w`, `temple_t`, `cradle_w`, `wall`. One
    cradle helper is shared across all three mounts.
  - **Visor Grip** (`profile`, internal) — the C-clip that grips the sun visor,
    defined by `visor_t`, `wall`.
- **Material awareness:** the cradle notch clearance scales with the temple
  dimensions so the grip can be tuned per material/printer; `tolerance_by_material`
  is declared.
- **Societal benefit:** keeps eyewear off dashboards and floors where it gets
  scratched or crushed — one cradle, three mounts, extending the life of glasses.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard. The final solid is assigned to `result`.
- The visor clip is a single extruded C profile; the cradle is a rooted
  compliant U-notch. No separate parts or hardware.
- All shipped presets and defaults render **watertight**.
