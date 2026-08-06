# Bottle / Can Koozie Adapter

A sleeve or adapter generated with **CadQuery** (B-Rep) that fits a small can or
bottle into a larger cup holder and insulates it. Sized by **real vessel and
holder diameters** with a tunable fit clearance, so the printed bore matches the
drink and the outside matches the holder.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Sleeve** | `sleeve` | Straight or tapered sleeve; bore holds the vessel, outer wall can taper. |
| **Stepping Adapter** | `adapter` | Steps a small-Ø vessel up to a larger holder Ø; straight outside, optional base. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Diameters | `inner_dia` | 66 mm | Vessel Ø the bore must hold (66 ≈ 355 ml can). |
| Diameters | `outer_dia` | 90 mm | Holder Ø the outside must fill. |
| Diameters | `height` | 95 mm | Overall height (Z). |
| Shape & Fit | `taper` | 6.0 mm | How much narrower the top is than the bottom (sleeve; 0 = straight). |
| Shape & Fit | `wall` | 3.0 mm | Minimum wall / insulating thickness. |
| Shape & Fit | `fit_clear` | 0.5 mm | Added to the bore, removed from the outside, for a slip fit. |
| Base | `base` | on | Close the bottom so the vessel rests on an insulating floor. |
| Base | `base_th` | 3.0 mm | Thickness of the closed base. |

## Presets

- **355 ml Can → Cup Holder** — 66 mm bore into a 90 mm holder, closed base.
- **Slim Can Sleeve (tapered)** — 58 → 84 mm, 10 mm taper.
- **Bottle Insulator** — 70 mm bore, thick 5 mm wall, closed base.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Vessel Taper** (`profile`, internal) — the diameter/taper interface.
    `inner_dia`, `outer_dia`, `taper`, `wall` and `fit_clear` define the bore
    (vessel Ø + clearance) and the outer profile (holder Ø − clearance). Any two
    parts built at the same vessel/holder diameters share the same mating profile,
    so a sleeve and an adapter can target the same drink and the same holder.
- **Material awareness:** `tolerance_by_material` is declared so the fit clearance
  can be tuned per material/printer — a firmer grip for rigid PLA, a looser bore
  for flexible TPU.
- **Societal benefit:** rescues the mismatch between a drink and a cup holder,
  extending the life of vehicles, furniture and vessels people already own.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The tapered sleeve is a lofted frustum minus a cylindrical bore; the adapter is
  a straight tube. All shipped modes and presets export **watertight**.
