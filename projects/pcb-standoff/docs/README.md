# PCB Standoff / Mounting Plate

Standoffs to raise a PCB above a surface, generated with **CadQuery** (B-Rep). A
hole pattern — the four corners of a W×D rectangle, or a rows×cols grid — drives
the standoff positions; each standoff is a bored tube sized to an M2 / M2.5 / M3
screw.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plate** | `plate` | Standoffs standing on a solid connecting base plate — one printable mounting plate. |
| **Loose Standoffs** | `standoffs` | The same standoffs joined by a thin runner strip so they print as one set and snap apart. |
| **Single Spacer** | `spacer` | One tubular spacer/standoff, bored through. |

Render each mode with `target_part` set to that mode's part id to see the
distinct part.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Hole Pattern | `pattern` | corners | `corners` (W×D) or `grid` (rows×cols). |
| Hole Pattern | `rect_w` / `rect_d` | 58 / 49 mm | Corner hole spacing X / Y. |
| Hole Pattern | `grid_rows` / `grid_cols` | 3 / 3 | Grid standoff count. |
| Hole Pattern | `grid_pitch` | 20 mm | Grid hole-to-hole spacing. |
| Standoff | `standoff_h` | 6.0 mm | Standoff / spacer height. |
| Standoff | `screw_size` | M3 | M2 / M2.5 / M3 — sets bore and boss diameter. |
| Base Plate | `plate_t` | 2.0 mm | Connecting plate thickness (0 → thin default slab). |

## Presets

- **Pi HAT Plate (58×49)** — corner pattern at the HAT hole rectangle, M2.5.
- **Prototype Grid (4×4)** — a 16-standoff grid at 18 mm pitch, M3.
- **Tall M3 Spacer** — a single 15 mm spacer.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **PCB Mount Pattern** (`bolt_pattern`, internal) — the hole layout, defined
    by `pattern`, `rect_w`, `rect_d`, `grid_rows`, `grid_cols`, `grid_pitch`,
    `screw_size`. Any board sharing that hole pattern bolts to these standoffs.
  - **Standoff Screw Bore** (`socket`, ISO metric M2/M2.5/M3) — `screw_size`,
    `standoff_h`: the bore each standoff presents to the mounting screw.
- **Material awareness:** the bore is sized slightly under nominal so a
  thread-forming screw bites plastic directly; `tolerance_by_material` is
  declared for per-filament tuning.
- **Societal benefit:** the simplest reprinted electronics primitive — raise any
  board off any surface at the exact height and hole pattern needed.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`
  and the active part is selected through `target_part`.
- All shipped presets and defaults render **watertight**.
