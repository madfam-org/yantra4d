# Modular Wall Hook Rail / French Cleat

The catalog capstone: a **45° French-cleat shop-wall system**, generated with
**CadQuery** (B-Rep). A wall-mounted cleat strip screws to the wall, and accessory
backs carry the **complementary 45° cleat** and hang on it — the whole wall becomes
reconfigurable storage from one shared interface.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wall Cleat** | `wall_cleat` | The 45° strip that screws to the wall, with mounting screw holes. |
| **Hook Back** | `hook_back` | An accessory with the mating 45° cleat on its back + a hook out front. |
| **Bin Back** | `bin_back` | A small bin with the mating cleat back (also builds a tool holder or shelf via `accessory`). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cleat | `angle` | 45° | Bevel angle — wall and accessory share it. |
| Cleat | `cleat_h` | 30 mm | Wedge band height. |
| Cleat | `cleat_depth` | 14 mm | How far the cleat projects from the wall. |
| Wall Strip | `strip_len` | 120 mm | Wall cleat length. |
| Wall Strip | `screw_dia` | 4.5 mm | Screw clearance (0 = none, ≈ #8 / M4). |
| Wall Strip | `screw_count` | 2 | Mounting screw holes. |
| Accessory | `accessory` | hook | hook / bin / tool_holder / shelf. |
| Accessory | `back_w` | 70 mm | Accessory back width. |
| Accessory | `wall` | 4.0 mm | Accessory body wall. |
| Accessory | `fit` | 0.4 mm | Hang clearance between cleats. |
| Accessory | `tool_dia` | 25 mm | Tool-holder hole diameter. |

## The 45° cleat interface (verified mate)

The wall cleat's front-top edge is a ramp at exactly `angle`; the accessory's lip
underside is the **complementary parallel plane** at the same `angle`, shifted up by
`fit` for an easy hang. The inlined `cleat_ramp_geometry()` drives BOTH profiles from
one `rise`/`run` derived from `angle`, and clamps the **rise** (never the run) when
depth is tight — so the ramp stays at the exact angle. Verified across depth/height:
at `angle` = 30/45/60 the wall ramp and accessory lip come out at 30.0/45.0/60.0°
respectively, i.e. always parallel and mating. (The repo ships a
`cq_core.cdg_french_cleat` reference helper for the same math; this cartridge inlines
its own so it stays sandbox-self-contained.)

## Presets

- **Standard 45° Wall Cleat** — a 120 mm strip with two screw holes.
- **Tool Hook** — a hook accessory back.
- **Parts Bin** — a bin accessory back.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **French Cleat 45°** (`rail`, internal) — defined by `angle`,
  `cleat_h`, `cleat_depth`. Any accessory built at the same `angle` mates any wall
  cleat built at that angle.
- **Material awareness:** `tolerance_by_material` — the hang fit (`fit`) depends on
  filament; tune per material.
- **Societal benefit:** the open, universal shop-wall standard — a parametric cleat
  plus a growing family of accessory backs turns any wall into reconfigurable,
  on-demand storage from one shared 45° interface.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
