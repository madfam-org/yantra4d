# Sanding / Router Template

A flat template generated with **CadQuery** (B-Rep) that a router follows with a
**guide bushing** (or a bearing-guided bit) to reproduce a shape exactly. The
template is a plate with the shape cut clean through; the opening is
intentionally **offset** from the finished size by the bushing-to-bit offset so
the routed part comes out on-size.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Circle Template** | `circle_template` | A round opening of `radius`. |
| **Rectangle Template** | `rect_template` | A `rect_w` × `rect_d` opening with corner radius `corner_r`. |
| **Slot Template** | `slot_template` | A rounded slot of length `slot_len`, width `slot_w`. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Guide-bushing offset

With a guide bushing the cutter is inset from the template edge by
`(bushing_OD − bit_dia) / 2`. Enter that as `bushing_offset`. For an **inside
cutout** the template opening must be **larger** than the finished size by the
offset — this cartridge grows the opening by `bushing_offset` on every side so
the routed pocket lands on nominal. Set `bushing_offset = 0` for a **flush-trim
bearing bit** (the bearing rides the template edge, no offset).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Opening Shape | `radius` | 40.0 mm | Circle finished radius. |
| Opening Shape | `rect_w` / `rect_d` / `corner_r` | 80 / 50 / 8 mm | Rectangle finished size + corner. |
| Opening Shape | `slot_len` / `slot_w` | 70 / 18 mm | Slot finished length + width. |
| Bushing Offset | `bushing_offset` | 3.0 mm | `(bushing OD − bit) / 2`; 0 = flush-trim bearing. |
| Plate & Mounting | `plate_t` | 6.0 mm | Template thickness (clears the bushing collar). |
| Plate & Mounting | `border` | 25.0 mm | Plate margin around the opening. |
| Plate & Mounting | `mount_holes` / `mount_dia` | on / 4.5 mm | Screw/pin holes to fix the template. |

## Presets

- **Speaker Cutout (Ø100)** — a 50 mm-radius round opening (offset for a common
  bushing/bit pair).
- **Inlay Pocket (80×50)** — a rounded rectangular pocket.
- **Hinge Mortise Slot** — a 90 × 25 mm rounded slot with fixing holes.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Router Template Opening** (`profile`, internal) — the offset opening
    profile, defined by the shape params plus `bushing_offset`.
  - **Template Mount Pattern** (`bolt_pattern`, internal) — the corner fixing
    holes, `mount_holes`, `mount_dia`, `border`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` are
  declared. Printed templates shrink slightly; the exposed `bushing_offset`
  absorbs both the bushing math and any material allowance.
- **Societal benefit:** reproducible woodworking without a CNC — a hand router
  cuts the same on-size shape any number of times, with the bushing offset baked
  in so beginners get repeatable results.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
