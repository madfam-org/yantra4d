# Utility Hook / Coat Peg

A parametric **wall hook** generated with **CadQuery** (B-Rep) for coats, bags,
towels, or keys. The hook reaches forward and curls upward at the tip so items
cannot slide off, with load-appropriate stock thickness. A selectable mount fixes
it by screw, by adhesive, or over a door.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Hook** | `hook` | One hook on the selected mount. |
| **Hook Rail** | `hook_rail` | `count` hooks on one shared back plate / yoke. |

The studio dispatches the active part via `target_part` (`hook` / `hook_rail`).

## Mounts (`mount_type`)

| Value | Mount |
| :--- | :--- |
| `screw` | A flat back plate with two screw clearance holes. |
| `adhesive` | A flat back plate (foam adhesive tape goes on its back face); no holes. |
| `over_door` | A yoke that turns over the top of a door of `door_thick`, hanging with no fixings. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Mount | `mount_type` | `screw` | `screw`, `adhesive`, or `over_door`. |
| Hook | `hook_reach` | 40.0 mm | Forward projection before the up-curl. |
| Hook | `hook_curl_r` | 12.0 mm | Radius of the upward curl at the tip. |
| Hook | `hook_thick` | 8.0 mm | Stock thickness (load capacity). |
| Hook | `hook_width` | 12.0 mm | Stock width across. |
| Mount | `plate_thick` | 5.0 mm | Mounting plate / yoke thickness. |
| Mount | `plate_w` / `plate_h` | 26 / 45 mm | Back-plate size. |
| Mount | `screw_dia` | 4.5 mm | Screw clearance hole (screw mount only). |
| Mount | `door_thick` | 40.0 mm | Door leaf thickness (over-door mount only). |
| Rail | `count` | 3 | Hooks on one shared plate. |
| Rail | `spacing` | 60.0 mm | Centre-to-centre hook spacing. |

## Presets

- **Coat Hook (screw)** — a 45 mm reach coat hook on a screw plate.
- **Towel Hook (adhesive)** — a 30 mm adhesive hook for a bathroom.
- **Over-Door Rail (3 hooks)** — a 3-hook rail that hangs over a 40 mm door.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Wall Mount** (`bolt_pattern`, internal) — the mounting interface, defined
    by `mount_type`, the plate dimensions, `screw_dia`, and `door_thick`. The
    same hook body reuses this mount for wall, adhesive, or over-door service.
  - **Hook Up-Curl** (`profile`, internal) — the reach-and-curl hook profile,
    defined by `hook_reach`, `hook_curl_r`, `hook_thick`, and `hook_width`.
- **Material awareness:** `hook_thick` is exposed so the section can be sized to
  the material's strength for the intended load; `tolerance_by_material` is
  declared.
- **Societal benefit:** a hook is the smallest useful piece of furniture. One
  parametric hook that mounts by screw, tape, or over a door, at the reach and
  load the item needs, replaces a shelf of single-purpose plastic hooks and
  outfits an entire entryway from a single print file.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The up-curl is built as a union of short prisms sampled along a quarter-arc,
  overlapping into the bar and the tip finger, so every mount type and preset
  renders **watertight**.
- The brief named this interface a *bracket*; the manifest schema's
  `geometry_type` enum has no `bracket`, so the wall-mount interface uses the
  closest valid type, `bolt_pattern`, keeping the "Wall Mount" label.
