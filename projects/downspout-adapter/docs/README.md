# Rain-Barrel / Downspout Adapter

Adapts a rectangular house downspout to a round pipe or rain-barrel inlet, generated
with **CadQuery** (B-Rep) — the missing piece for rainwater harvesting. A hollow
transition lofts a rectangular mouth (2×3" or 3×4") into a round outlet; variants add
a barrel-lid mounting flange and a coarse debris screen.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rectangle → Round** | `rect_to_round` | The bare hollow transition duct, optional debris screen. |
| **Barrel Inlet** | `barrel_inlet` | Transition + flat mounting flange (4 bolt holes) for a barrel lid. |
| **Screen Box** | `screen_box` | A perforated leaf-catcher tray that hangs in the downspout mouth. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Downspout Mouth | `spout_w` / `spout_d` | 76 / 51 mm | Rectangular mouth (3"×2"). |
| Round Outlet | `outlet_dia` | 60 mm | Round pipe / barrel bulkhead diameter. |
| Round Outlet | `trans_len` | 70 mm | Rect→round morph length. |
| Round Outlet | `flange_w` | 30 mm | Barrel flange radial width (barrel_inlet). |
| Shell & Options | `wall` | 3.0 mm | Shell wall thickness. |
| Shell & Options | `collar_len` | 12 mm | Straight collar at each end. |
| Shell & Options | `screen` | off | Perforated grid across the outlet. |

## Presets

- **2×3" → 60 mm Round** — the common US residential downspout to round pipe.
- **3×4" Barrel Inlet** — larger downspout onto a rain barrel, with screen.
- **2×3" Leaf Screen** — standalone debris tray.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Downspout Transition** (`profile`, internal) — the rectangle-to-round morph,
    defined by `spout_w`, `spout_d`, `outlet_dia`, `trans_len`, `wall`. The
    rectangular mouth mates the downspout; the round collar mates standard pipe.
- **Material awareness:** `wall` and clearances tune per material/printer;
  `tolerance_by_material` is declared.
- **Societal benefit:** rainwater harvesting made buildable — connect an odd
  rectangular downspout to a standard round barrel inlet without custom sheet metal.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Hollow-shell method:** the outer envelope is a single solid (rounded-rect →
  circle loft via `cq.Solid.makeLoft` on explicit wires, plus straight collars via
  `cq.Solid.extrudeLinear`); the interior is removed as **three sequential cuts**
  (bottom prism, tapered inner loft, top bore). Sequential cuts avoid the OCC
  non-manifold collapse that unioning near-coincident void faces would cause, so all
  modes export **watertight**.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
