# Roof-Rack / Crossbar Accessory

Accessory saddles that seat on a roof-rack crossbar, generated with **CadQuery**
(B-Rep): the bar profile is channelled into the underside so the saddle
straddles the bar, a clamp plate pinches it from below via side bolts, and a
T-slot platform on top takes an accessory. Built for the three profile families
— square, round and aero — using Thule / Yakima crossbar dimensions.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> A roof-rack saddle carries load — print in a **tough material** (PETG/ASA or
> nylon), keep walls thick, and use metal clamp bolts. Verify fit before loading.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Square-Bar Saddle** | `square_clamp` | A saddle with a rectangular channel for a square crossbar (e.g. Thule SquareBar 31.75 × 22.2 mm). |
| **Round-Bar Saddle** | `round_clamp` | A saddle with a circular channel and a bottom mouth for a round crossbar (e.g. Yakima RoundBar 28.6 mm). |
| **Aero-Bar Saddle** | `aero_saddle` | A saddle with a rounded-rectangle channel approximating a wide aero bar (e.g. Thule WingBar ~79 × 25 mm). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Crossbar | `bar_w` | 31.75 mm | Bar width (SquareBar 31.75, RoundBar 28.6, WingBar ~79). |
| Crossbar | `bar_h` | 22.2 mm | Bar height (SquareBar 22.2; WingBar aero ~25). |
| Saddle | `saddle_w` | 50.0 mm | Saddle width along the bar. |
| Saddle | `wall` | 5.0 mm | Saddle wall and body thickness. |
| Saddle | `bolt_d` | 6.4 mm | Clamp bolt clearance (M6). |
| Saddle | `clearance` | 0.4 mm | Per-side gap between channel and bar. |
| Platform | `acc_slot_w` | 8.0 mm | Top T-slot width for the accessory bolt. |
| Platform | `plat_h` | 8.0 mm | Accessory platform height above the bar. |

## Presets

- **Thule SquareBar (31.75 × 22.2)**.
- **Yakima RoundBar (28.6 mm)**.
- **Thule WingBar (79 × 25)**.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Crossbar Profile Clamp** (`socket`, "aero/square crossbar") — the channel
    that seats the bar, defined by `bar_w`, `bar_h`, `saddle_w`, `clearance`. One
    saddle family covers square, round and aero crossbars.
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material or a foam shim takes up bar tolerance.
- **Societal benefit:** mounts a light bar, bike tray or tie-down to any rack
  from printed parts, keeps an aging or discontinued rack useful, and
  standardises every accessory to one T-slot instead of a per-brand adapter.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy: each saddle is a solid block; the bar profile is cut up
  from the bottom face (the bar enters from below → vented, no trapped void).
  Side clamp-bolt holes pass through; the accessory T-slot is cut through the top
  platform. The aero and round channels round their interior edges. Fillets are
  applied to clean blanks before cuts.
- All shipped presets and defaults render **watertight**, single-body.
