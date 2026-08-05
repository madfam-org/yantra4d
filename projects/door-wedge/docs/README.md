# Door / Window Wedge & Stop

A classic ramp doorstop generated with **CadQuery** (B-Rep). Length, width, and
height set the ramp angle; an optional grip texture on the underside keeps it from
sliding on hard floors, and an optional finger hole lets it hang on a hook.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wedge** | `wedge` | The plain ramp. |
| **Hook Stop** | `hook_stop` | A wedge with a raised heel at the tall end so a door can't ride up and over it. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Wedge Size | `length` | 120 mm | Ramp run; longer + lower = shallower angle. |
| Wedge Size | `width` | 45 mm | Width across the door. |
| Wedge Size | `height` | 35 mm | Tall-end height; sets the ramp angle with length. |
| Grip & Hanging | `grip` | on | Shallow ridges on the underside for floor grip. |
| Grip & Hanging | `finger_hole` | off | Through-hole near the tall end to hang on a hook. |
| Heel | `heel_height` | 22 mm | Raised heel height (hook stop mode). |

## Presets

- **Standard Doorstop** — 120×45×35, grip ridges.
- **Low-Gap Wedge** — 140×50×22 for a small floor gap, with a hang hole.
- **Heavy-Door Hook Stop** — 150×60×45 with a 30 mm heel.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Wedge Ramp** (`profile`, internal) — the right-triangle ramp cross-section,
    defined by `length`, `width`, `height`.
- **Material awareness:** `tolerance_by_material` declared.
- **Societal benefit:** the definitive first print — free, fast, and immediately
  useful. Tuning the ramp angle to the real floor gap and door weight beats a
  one-size store wedge; grip ridges keep it in place without adhesive.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Watertight by design:** the ramp is a solid triangular prism; grip ridges are
  full cross-floor channels, the heel is a unioned solid block, and the finger
  hole is a full through-bore — every preset and extreme renders watertight.
