# Bearing Housing / Pillow Block

A parametric housing generated with **CadQuery** (B-Rep) that seats a standard
deep-groove ball bearing in a press-fit bore with a shoulder, so the bearing
seats to a positive stop. The seat is sized to the bearing's outer diameter from
a built-in table.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Bearing table

| Bearing | ID | OD | Width |
| :--- | :--- | :--- | :--- |
| 608 | 8 | 22 | 7 |
| 623 | 3 | 10 | 4 |
| 625 | 5 | 16 | 5 |
| 6900 | 10 | 22 | 6 |
| 6902 | 15 | 28 | 7 |

The seat pocket bore = bearing OD (plus the `press_fit` adjustment); the pocket
depth = bearing width; the shoulder is a thinner shaft-clearance bore behind the
seat that forms the positive stop.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pillow Block** | `pillow_block` | Raised block, horizontal shaft axis, base bolt-down ears. |
| **Flange Mount** | `flange_mount` | Flat plate, axis normal to the face, bolt pattern around the seat. |
| **Insert Ring** | `insert` | Bare press-fit carrier ring (seat + shoulder). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bearing | `bearing` | 608 | Bearing designation → seat OD. |
| Pillow Block | `mount_style` | raised | Raised pedestal or flush/low profile. |
| Body & Walls | `wall` | 4.0 mm | Material around the outer race. |
| Body & Walls | `back_wall` | 2.0 mm | Shoulder (the seat stop). |
| Body & Walls | `press_fit` | 0.0 mm | Seat fit adjust (−tightens / +loosens). |
| Mounting Bolts | `mount_holes` / `bolt_dia` | 4 / 4.5 mm | 2 or 4 bolts, M4 clearance. |
| Pillow Block | `riser` | 10.0 mm | Pedestal raise height. |

## Presets

- **Pillow Block 608** — the classic 608 pillow block on a raised pedestal.
- **Flange Mount 6900** — a thin-section 6900 flange bearing.
- **Press-Fit Insert 625** — a bare 625 carrier ring with a slight interference.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Bearing Seat** (`socket`, ISO 15 608/625/6900) — the press-fit interface,
    defined by `bearing`, `back_wall`, `press_fit`. Any part with the same seat
    accepts the same bearing.
  - **Housing Mount Pattern** (`bolt_pattern`, internal) — `mount_holes`,
    `bolt_dia`.
- **Material awareness:** `tolerance_by_material` and `press_fit` let the seat
  interference be tuned per material/printer.
- **Societal benefit:** turns a loose bearing into a mountable rotating joint
  without machining a metal block.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
