# Center Finder / Marking Gauge

Layout tools generated with **CadQuery** (B-Rep) that scribe or find a reference
line. A 90° vee registers on a round or square end so a slot down its bisector
marks dead centre; a fenced marking gauge scribes a line a set distance from an
edge; a mortise gauge scribes two parallel lines for a mortise or tenon.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Center Finder** | `center_finder` | A vee-block whose 45° bisector slot finds the centre of round or square stock up to `stock_max`. |
| **Marking Gauge** | `marking_gauge` | A fenced beam with a scribe-pin slot for scribing a line a set distance from an edge. |
| **Mortise Gauge** | `mortise_gauge` | A fenced beam with two parallel scribe slots `mortise_gap` apart for marking mortises / tenons. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Stock & Body | `stock_max` | 50.0 mm | Largest round/square stock the vee accepts. |
| Stock & Body | `thick` | 12.0 mm | Tool body thickness. |
| Scribe | `scribe_w` | 1.6 mm | Pencil / scribe-pin slot width. |
| Gauge Beam & Fence | `beam_len` / `fence_h` | 90 / 30 mm | Gauge beam reach and edge-fence height. |
| Gauge Beam & Fence | `mortise_gap` | 8.0 mm | Spacing between the two mortise scribe lines. |

## Presets

- **Dowel Center Finder** — a vee finder for round dowel stock.
- **Edge Marking Gauge** — a fenced single-line gauge.
- **Tenon Mortise Gauge (8mm)** — a two-line gauge for 8 mm mortises.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Vee Register** (`profile`, internal) — the 90° inside corner defined by
    `stock_max`, `thick`; cradles round or square stock so the bisector slot
    lands on centre.
  - **Scribe Slot** (`pocket`, internal) — `scribe_w`, `beam_len`, `mortise_gap`;
    the pencil / scribe channel(s).
- **Material awareness:** `tolerance_by_material` — the scribe slot can be tuned
  to a specific pencil or knife width.
- **Societal benefit:** accurate layout without a machinist's set — find the
  centre of any stock and scribe repeatable edge and mortise lines.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**. The center-finder is a
  large-facet solid, so its default STL tessellates to a low face count.
