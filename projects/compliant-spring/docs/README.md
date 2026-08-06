# Compliant Spring

A printable **geometric spring** generated with **CadQuery** (B-Rep) — no coil. It
flexes because its *shape* bends, not because the material is elastic, so it prints
in one continuous mono-material solid. Three flexure families cover compression,
suspension, and snap-fit duties.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wave Spring** | `wave_spring` | A vertical serpentine (stacked sine flexures) between two flat mounting pads; compresses along Z. |
| **Leaf Spring** | `leaf_spring` | A curved circular-arc cantilever leaf with a root mounting block; loading the tip flattens the bow. |
| **Cantilever** | `cantilever` | A straight cantilever beam with a root block and a tip catch lip — the reference snap flexure. |

The mode selects the family; the `spring_type` select mirrors it.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Flexure | `spring_type` | wave | wave / leaf / cantilever. |
| Flexure | `thickness` | 2.0 mm | Beam/wall thickness — the primary stiffness lever. |
| Flexure | `waves` | 4 | Sine cycles over the height (wave only). |
| Flexure | `amplitude` | 10 mm | Meander sway (wave) or bow rise (leaf). |
| Size | `free_length` | 40 mm | Unloaded height (wave) or beam length (leaf/cantilever). |
| Size | `width` | 16 mm | Width across (Y); wider = stiffer. |
| Size | `pad` | 4.0 mm | End mounting-pad thickness (wave). |

## Presets

- **Soft Wave (TPU)** — a compliant compression wave for a soft material.
- **Leaf Suspension** — a stiffer arc leaf for a small suspension.
- **Snap Latch** — a cantilever snap flexure for a latch or clip.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Compliant Flexure** (`spline`, internal) — the flexing geometry, defined by
    `thickness`, `free_length`, `waves`, `amplitude`. End pads/blocks present flat
    mounting faces so the spring drops into a pocket sized to `width` × pad.
- **Material awareness:** `tolerance_by_material` is declared. **Stiffness is
  material-dependent** — the identical shape is firm in PLA and soft in TPU — so
  `thickness`, `waves`, and `width` are the stiffness levers and force must be
  validated empirically.
- **Societal benefit:** springs are consumable hardware rarely stocked in the exact
  rate a repair needs — a coil-free, mono-material printable flexure replaces a
  broken spring in a latch, clip, or suspension on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Every family is built as **one closed 2D outline extruded across `width`** (the
  wave traces up its +thickness/2 edge and back down its −thickness/2 edge into a
  single loop), so the result is one continuous watertight solid. **All shipped
  presets, all three families, and both extremes render watertight.**
- **This models geometry, not force.** Actual spring rate depends on material,
  layer orientation, and infill.
