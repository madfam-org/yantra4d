# Junction Box Mounting Ears

Retrofit mounting hardware for US electrical junction boxes, built with
**CadQuery** (B-Rep). It bridges the device-mounting screw pattern of a standard
single-gang box — **#6-32 screws on a ~83.3 mm (3.28 in) vertical pitch** — to a
wall, a surface standoff, or a raised mud ring. Sizes follow US NEMA/NEC box
conventions.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com). This is a **new** commons
family/cluster — no existing family member mates it, so `compatible_with` is
empty pending future siblings.

## Modes

| Mode | Part id | Description |
| :--- | :--- | :--- |
| **Retrofit Ear Plate** | `ear_pair` | A flat plate sized to the box face, carrying the device-screw pattern plus outboard wall-screw ears — the simplest retrofit flange. |
| **Box Standoff Frame** | `box_standoff` | A rectangular frame that lifts a box off a rough or uneven surface, with a vented wiring window and the device pattern on the top rim. |
| **Raised Mud Ring** | `mud_ring` | A raised single-gang plaster ring that brings the device face up flush to a thick wall finish, with side wall-ears. |

The platform renders per-part via `target_part`; each mode's `parts[]` id equals
the value the code dispatches on, so the three modes render as distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Device Screw Pattern | `device_pitch` | 83.3 mm | #6-32 device screw vertical C-C (US single-gang). |
| Device Screw Pattern | `device_screw` | 3.6 mm | #6-32 screw clearance. |
| Box & Plate | `gang_w` | 50 mm | Single-gang box face width (~2 in). |
| Box & Plate | `plate_t` | 4.0 mm | Plate / wall thickness. |
| Box & Plate | `ring_h` | 16 mm | Raise / standoff depth (standoff, mud ring). |
| Wall Mount | `wall_screw` | 4.5 mm | Wall/surface screw clearance (#8). |
| Wall Mount | `ear_w` | 22 mm | Outboard wall-ear width. |

## Presets

- **Single-Gang Ear Plate** — a flat retrofit flange on the 83.3 mm pattern.
- **Rough-Surface Standoff** — a 16 mm frame lifting a box off an uneven wall.
- **Thick-Wall Mud Ring** — a 16 mm raised ring for a deep finish.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **US Junction Box Device Screws** (`bolt_pattern`, standard **US junction
    box**) — the #6-32 device pattern (`device_pitch`, `device_screw`, `gang_w`).
  - **Wall Ear Screws** (`bolt_pattern`, internal) — the outboard surface-fixing
    pattern (`wall_screw`, `ear_w`).
- **Material awareness:** screw clearances are printable values tunable per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** electrical retrofit is full of boxes that sit too deep,
  mount to crumbling plaster, or lack a fixing point after a remodel. Printable
  ears, standoffs and mud rings on the standard #6-32 device pattern let an
  installer salvage an existing box — flush it to a new finish, lift it off a
  rough surface, or add a wall flange — instead of cutting a new opening.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Watertight construction: blanks are filleted before feature cuts; all screw
  holes and the device opening are through-bores that vent to outside (no
  trapped void); the collar/base geometry always extends past the device screws
  with margin so a bore never clips a wall edge (which would sliver into a
  non-manifold mesh). All three modes and the min/max extremes export watertight,
  single-body.
