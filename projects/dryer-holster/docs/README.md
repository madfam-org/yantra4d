# Hair Dryer / Tool Holster

Wall holsters for hair dryers and styling tools, generated with **CadQuery**
(B-Rep) and sized to the **real handle and barrel diameters** of the tool:
dryer handles (~40–55 mm), barrels / nozzles (~50–75 mm), and curling-iron
handles (~28–35 mm). Three distinct socket modes.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Barrel Cradle** | `barrel_cradle` | A U-shaped cradle the dryer barrel drops into sideways; a top slot opens it so the tool lifts straight out. |
| **Handle Holster** | `handle_holster` | A deep tube socket the handle drops into so the tool hangs handle-down. A side cord slot lets the cable exit the back. |
| **Cord Hook** | `cord_hook` | A compact wall horn (arm + up-turned lip) to loop the cord and hang the tool by its handle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tool | `barrel_d` | 62 mm | Dryer barrel / nozzle diameter (barrel cradle). |
| Tool | `handle_d` | 45 mm | Handle diameter. Dryer ~40–55, curling iron ~28–35. |
| Holster Body | `wall` | 5 mm | Wall thickness of the cradle / holster. |
| Holster Body | `plate_h` | 70 mm | Back-plate height against the wall. |
| Holster Body | `depth` | 60 mm | How far the cradle / holster / hook projects. |
| Wall Mount | `screw_d` | 4.2 mm | Wall-mount screw clearance (M4 ~4.2 mm). |

## Presets

- **Standard Dryer Cradle** — a 62 mm barrel U-cradle.
- **Handle-Down Holster** — a 45 mm handle tube socket.
- **Curling-Iron Holster** — a slim 32 mm handle socket.
- **Cord Loop Hook** — a simple cord + handle hook.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Barrel Cradle Socket** (`socket`, *internal*) — the U-channel sized by
    `barrel_d` that receives the dryer barrel.
  - **Handle Socket** (`socket`, *internal*) — the tube / hook sized by
    `handle_d`; the interface that captures the tool handle.
  - **Wall Screw Mount** (`bolt_pattern`, *ISO 7045 M4*) — the mount screws.
- **Material awareness:** `tolerance_by_material` is declared — the cradle /
  socket fit is set by `barrel_d` / `handle_d` and `wall`, tunable per printer.
- **Societal benefit:** a hot tool set on a counter is a burn and fire risk, and
  the branded dock it shipped with is rarely the one you keep; sizing the cradle
  and holster to real diameters lets anyone park the exact dryer or iron they own.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Watertight by construction:** the blank is filleted **before** cutting; the
  cradle channel opens to a face via a top slot; the holster bore opens to the
  top over a solid floor with a side cord slot (no trapped void); the cord hook
  is a union of solid primitives (cylinders placed with explicit direction
  vectors, generously overlapping — no fragile sweep or tangent seam). All three
  modes and the MIN/MAX extremes render watertight with a single body.
