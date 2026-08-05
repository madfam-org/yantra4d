# Funnel

A hollow funnel generated with **CadQuery** (B-Rep): a wide conical mouth tapering
into a narrow spout tube, built as a single surface of revolution so it prints
watertight by construction. Options include an anti-glug vent tube for smooth
pouring and a nesting rim so funnels stack.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Funnel** | `funnel` | The everyday funnel shape. |
| **Long Neck** | `long_neck` | Extended, slimmer spout (min 70 mm long, ≤ 14 mm Ø) to reach into bottles. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Funnel Shape | `top_dia` | 90 mm | Wide mouth (inlet) diameter. |
| Funnel Shape | `total_h` | 85 mm | Overall height including the spout. |
| Funnel Shape | `wall` | 2.0 mm | Shell wall thickness. |
| Spout | `spout_dia` | 12 mm | Spout outer Ø; auto-clamped to keep an open bore. |
| Spout | `spout_len` | 30 mm | Straight spout length. |
| Options | `vent` | off | Anti-glug air tube for smooth pouring. |
| Options | `nesting_rim` | on | Rim at the mouth so funnels stack / rest on jars. |

## Presets

- **Kitchen Funnel** — 90 mm mouth, 14 mm spout, nesting rim.
- **Wide Dry-Goods Funnel** — 160 mm mouth, 40 mm spout.
- **Bottle Long-Neck** — 80 mm mouth, 10 mm × 80 mm spout, vent on.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Funnel Taper** (`profile`, internal) — the revolved cross-section from
    mouth to spout, defined by `top_dia`, `spout_dia`, `total_h`, `spout_len`,
    `wall`.
- **Material awareness:** `tolerance_by_material` declared; the spout diameter is
  auto-clamped so the bore never collapses below a printable minimum.
- **Societal benefit:** a funnel sized to your exact bottle or jar makes decanting
  clean and spill-free, replacing a drawer of mismatched plastic funnels.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Watertight by design:** the shell is *one* closed half-section revolved 360°
  (outer wall down, across the spout end, back up the inner bore) — not a boolean
  of two separate solids, so there are no seams. Every preset and extreme renders
  watertight, including the vent variant.
