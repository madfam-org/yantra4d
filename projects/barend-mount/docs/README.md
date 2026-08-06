# Motorcycle Bar-End / Mirror Mount

Handlebar hardware for motorcycles and bicycles, generated with **CadQuery**
(B-Rep): a split clamp that closes around the bar to carry an accessory, an
expanding plug for the hollow bar end (bar-end weights and mirrors), and a wider
clamp with an action-cam / phone cradle. Sized to real bar diameters — 7/8"
(22.2 mm), 1" (25.4 mm), 31.8 mm oversize.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print load-bearing clamps in a **tough material** (PETG or ASA/nylon) and use
> a metal bolt; a handlebar mount carries a vehicle accessory.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bar Clamp** | `bar_clamp` | A split C-clamp that wraps the bar OD, closed by a pinch bolt, with a flat accessory boss drilled for an M-bolt. |
| **Bar-End Plug** | `bar_end_plug` | A stepped plug for the hollow bar end, with a shoulder that rests on the rim and a central bolt bore for a weight/mirror stud. |
| **Phone / Cam Clamp** | `phone_clamp` | A wider bar clamp carrying a raised platform with a corner lip and a mounting slot, for an action-cam / phone base. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Handlebar | `bar_od` | 22.2 mm | Bar OD (7/8"=22.2, 1"=25.4, oversize=31.8). |
| Handlebar | `bar_id` | 16.0 mm | Hollow bar ID for the expanding plug (commonly 14–19). |
| Clamp | `wall` | 5.0 mm | Clamp wall and body thickness. |
| Clamp | `clamp_w` | 20.0 mm | Clamp width along the bar. |
| Clamp | `bolt_d` | 5.2 mm | Pinch bolt clearance (M5). |
| Clamp | `acc_bolt_d` | 8.4 mm | Accessory/mirror bolt clearance (M8, bar-end mirror standard). |
| Clamp | `clearance` | 0.3 mm | Per-side gap between the bore and the bar. |
| Platform | `plate_len` | 40.0 mm | Phone/cam platform length. |
| Platform | `plate_wid` | 32.0 mm | Phone/cam platform width. |

## Presets

- **7/8" Bar Clamp (22.2 mm)** — sport/dirt/JP bars.
- **1" Bar-End Plug (M8)** — cruiser bar end.
- **Action-Cam Platform**.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Handlebar Clamp** (`socket`, "7/8-1in bar") — the bore that wraps the bar
    OD, defined by `bar_od`, `wall`, `clamp_w`, `clearance`.
  - **Bar-End Socket** (`socket`, internal) — the insert plug for the hollow bar
    end, defined by `bar_id`, `acc_bolt_d`.
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material grips the bar with less clearance.
- **Societal benefit:** fits a mirror, phone or camera to any bike from durable
  printed parts and standardises every mount to one bolt size instead of a
  per-brand bracket.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy (the C-section clamp rule): the clamp is a solid block with
  the bar bore drilled through and a thin pinch slit sawn to one side — both open
  slots vent to outside and keep the part one manifold. The bar-end plug is a
  stepped solid cylinder with a central through bore. Fillets are applied to
  clean blanks before feature cuts.
- All shipped presets and defaults render **watertight**, single-body.
