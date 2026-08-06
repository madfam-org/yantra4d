# Zipper Pull & Cord Ends

Replacement zipper pulls and cord ends generated with **CadQuery** (B-Rep). A
flat grip tab with a slider loop that threads onto a zipper slider, a barrel
cord-end aglet for paracord, and a teardrop loop pull for cord zippers. Size the
loop and grip to your zipper.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pull Tab** | `pull_tab` | A flat grip tab with a slider loop at one end and a finger notch. |
| **Cord End** | `cord_end` | A tapered barrel aglet with an axial cord bore and a hang ear. |
| **Loop Pull** | `loop_pull` | A teardrop plate with a large cord hole and a finger grip hole. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Slider Loop | `loop_dia` | 5.0 mm | Inner diameter of the loop that threads onto the slider. |
| Grip | `grip_len` | 26 mm | Grip / tab length. |
| Grip | `grip_w` | 9.0 mm | Grip / tab width. |
| Grip | `thick` | 3.0 mm | Part thickness. |
| Cord | `cord_dia` | 4.0 mm | Cord diameter for the bore / hole (paracord ≈ 4 mm). |

## Presets

- **Jacket Zipper Pull** — the everyday flat pull tab.
- **Paracord Aglet** — a 4 mm cord end.
- **Glove-Friendly Loop** — a large teardrop loop pull.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Zipper Slider Loop** (`snap`, internal) — the loop that threads onto the
    zipper slider pin, defined by `loop_dia`, `thick`.
  - **Cord Bore** (`socket`, internal) — the paracord bore / hole, defined by
    `cord_dia`.
- **Material awareness:** loop and bore sizes are exposed so the fit can be tuned
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a broken zipper pull ends the useful life of jackets,
  bags, and tents; a printed replacement restores the garment in minutes.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard. The final solid is assigned to `result`.
- The cord-end ear fuses volumetrically into the barrel before its hole is cut,
  keeping the union manifold and watertight.
- All shipped presets and defaults render **watertight**.
