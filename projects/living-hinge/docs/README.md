# Living-Hinge Panel

A print-in-place **flexure hinge** generated with **CadQuery** (B-Rep) that folds
two flat panels without a separate pin. Pick a continuous thin web, a segmented
slot lattice, or a coiled knuckle — for boxes, lids, cases, and folding parts.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Web Hinge** | `hinge` | Two panels joined by one continuous thin membrane (`web_thick`). Flexes by bending the skin. |
| **Segmented Hinge** | `hinge` | Two panels bridged by a full-thickness block perforated with alternating through-slots that let it curl. |
| **Box Corner** | `hinge` | An L of two panels meeting at a folded 90° corner, with the hinge wrapping the inner corner. |

The `hinge_type` selector (`thin_web` / `segmented` / `coiled`) further sets the
flexing element; `coiled` builds a rolled arch knuckle over the web.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Panels | `panel_w` | 60 mm | Fold-line length (Y span shared by both panels). |
| Panels | `panel_len` | 40 mm | Length of each panel on either side of the hinge. |
| Panels | `panel_thick` | 3.0 mm | Thickness of the rigid panels. |
| Hinge | `hinge_type` | thin_web | Thin web / segmented / coiled knuckle. |
| Hinge | `web_thick` | 0.5 mm | Flexing membrane thickness (0.4–0.6 mm flexes best). |
| Hinge | `hinge_len` | 8.0 mm | Length of the flexing zone. |
| Segmented | `seg_count` | 6 | Number of cut slots (segmented mode). |
| Segmented | `seg_gap` | 1.2 mm | Width of each slot (segmented mode). |

## Presets

- **Snap-Lid Web (0.5 mm)** — a thin-web hinge sized for a box lid.
- **Curling Segmented Band** — a 10-slot segmented hinge that curls tightly.
- **Folded Case Corner** — a box-corner fold for a snap-together case.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Flexure Web** (`spline`, internal) — the living flexing membrane, defined
    by `web_thick`, `hinge_len`, `panel_w`. The thin continuous web is the
    interface that folds; keeping `web_thick` in the 0.4–0.6 mm band makes any
    panel pair fold reliably.
  - **Panel Edge** (`profile`, internal) — `panel_w`, `panel_thick`, `panel_len`
    define the rigid panel cross-section that mates to box walls or lids.
- **Material awareness:** the flex band thickness is exposed so it can be tuned
  per material/printer; `tolerance_by_material` is declared (PLA/PETG flex band
  differs from a brittle resin).
- **Societal benefit:** print-in-place hinges remove the last piece of hardware
  from folding boxes and enclosures — one continuous part replaces a pin, two
  knuckles, and an assembly step.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Every mode is a single continuous watertight solid — the thin web is one
  unbroken membrane between the panels, and segmented slots never reach the
  outer edges so the block never splits.
