# Shoe Accessories

Footwear add-ons generated with **CadQuery** (B-Rep), sized to lace width and
sole geometry. A spring lace lock (a single-piece cord-lock for shoelaces), a
heel clip that grips the shoe's heel counter, and a boot shaper that keeps a
boot shaft upright.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Lace Lock** | `lace_lock` | A barrel cord-lock: two lace channels and a printed sprung button that pinches both laces. Print-in-place. |
| **Heel Clip** | `heel_clip` | A C-clip that hooks over the heel counter, extruded once across the heel width (inherently watertight). |
| **Boot Shaper** | `boot_shaper` | A boot tree: spine, flared foot, and a curved top spreader that holds the shaft upright. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Lace | `lace_w` / `lace_t` | 6.0 / 2.5 mm | Flat lace cross-section. |
| Heel | `heel_w` | 62 mm | Heel counter width the clip grips. |
| Heel | `heel_h` | 34 mm | Section of the heel the clip wraps. |
| Heel | `sole_t` | 16 mm | Counter/sole edge thickness between the hooks. |
| Boot | `shaft_h` / `shaft_w` | 150 / 90 mm | Boot shaft height / interior width. |
| Build | `wall` | 2.4 mm | Wall / rib thickness. |

## Presets

- **Sneaker Lace Lock** — a 7 mm-lace cord lock.
- **Running-Shoe Heel Clip** — grips a 60 mm heel counter.
- **Tall Boot Tree** — a 220 mm boot shaper.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Lace Lock** (`snap`, internal) — the sprung lace pinch, defined by `lace_w`,
    `lace_t`, `wall`. One lace-channel helper sizes both channels.
  - **Heel Counter Grip** (`profile`, internal) — the C-clip cross-section that
    grips the counter, defined by `heel_w`, `heel_h`, `sole_t`, `wall`.
- **Material awareness:** channel and grip clearances scale with lace/counter
  dimensions so the fit can be tuned per material/printer; `tolerance_by_material`
  is declared.
- **Societal benefit:** small footwear fixes that extend the wearable life of
  shoes and reduce fast-fashion footwear churn.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard. The final solid is assigned to `result`.
- The lace lock's spring is a printed compliant button (a rooted cantilever) —
  no separate parts. The heel clip is a single extruded C profile.
- All shipped presets and defaults render **watertight**.
