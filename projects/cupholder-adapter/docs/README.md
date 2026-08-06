# Cup-Holder Caddy Adapter

A parametric **cup-holder caddy** generated with **CadQuery** (B-Rep). A tapered
stem drops into the car's cup-holder well — sized to your holder diameter with a
gentle draft so it self-centres and wedges — and a platform on top carries one of
three payloads.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Phone Caddy** | `phone_caddy` | An upright device slot with a front cable notch — a phone/GPS dock. |
| **Coin Tray** | `coin_tray` | A shallow round tray split into divided compartments for coins, change, keys. |
| **Multi Caddy** | `multi_caddy` | A central device slot **plus** a side pocket and a row of pen/stylus bores. |

The studio dispatches the active part via `target_part`; each mode renders a
distinct payload on the shared tapered stem.

## The fit

The stem is a circular **frustum**: its top radius matches the well radius (minus
a 0.4 mm seating clearance) and it tapers inward toward the tip by `taper` per
side over `stem_depth`. This gives a self-centring wedge fit across a wide range
of holders and tolerates the slight variation between vehicles. A blind bore up
the underside lightens the stem without breaking watertightness.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cup-Holder Fit | `holder_dia` | 74.0 mm | Inner diameter of the cup-holder well. |
| Cup-Holder Fit | `stem_depth` | 45.0 mm | How deep the stem sits in the well. |
| Cup-Holder Fit | `taper` | 2.5 mm | Draft per side over the stem depth. |
| Cup-Holder Fit | `wall` | 2.4 mm | Generic wall / rib thickness. |
| Platform | `base_dia` | 0 (auto) | Platform diameter; 0 rests on the rim (`holder_dia` + 16). |
| Platform | `base_thick` | 4.0 mm | Platform slab thickness. |
| Phone Slot | `phone_thick` / `phone_len` | 14 / 82 mm | Device slot width / length. |
| Phone Slot | `slot_height` | 40.0 mm | Upright wall height. |
| Tray & Pockets | `coin_wells` | 3 | Coin-tray compartments. |
| Tray & Pockets | `tray_depth` | 22.0 mm | Coin-tray depth. |
| Tray & Pockets | `pen_holes` / `pen_dia` | 2 / 12 mm | Pen bores on the multi caddy. |

## Presets

- **Standard Phone Dock** — a 74 mm holder, 82 mm phone slot, 40 mm walls.
- **Coins & Change Tray** — a 78 mm holder with three change compartments.
- **Console Organizer** — an 80 mm holder combo with three pen bores.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Cup-Holder Taper** (`profile`, internal) — the self-centring frustum that
    grips the well, defined by `holder_dia`, `stem_depth`, `taper`, and `wall`.
    Any payload on the same taper fits the same set of holders.
  - **Device Platform** (`socket`, internal) — the rim-resting platform carrying
    the payload, defined by `base_dia`, `base_thick`, `phone_thick`, `phone_len`.
- **Material awareness:** the seating clearance and wall thickness tune the wedge
  fit per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** cup holders are the one near-universal fixture in every
  car; a tapered adapter converts that wasted well into a phone dock, coin tray,
  or organiser sized to the exact holder, replacing throwaway retail caddies that
  never quite fit.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The stem is a lofted frustum with a cylinder fallback; the payload cavities are
  cut with overshooting bores so every shipped preset and default renders
  **watertight**.
