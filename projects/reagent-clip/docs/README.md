# Reagent Bottle Clip

Snap-on identification hardware for reagent and solution bottles, generated with
**CadQuery** (B-Rep): a C-clip that grips the bottle body and presents a flat
label window, a keyhole neck tag, and a cap marker disc that colour-codes a
screw cap.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Label Clip** | `label_clip` | A C-clip band around the bottle with a recessed write-on label window. |
| **Neck Tag** | `neck_tag` | A keyhole collar that slides over the neck, joined to a label panel. |
| **Cap Marker** | `cap_marker` | A thin disc for the cap top with an index notch and a label ring. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bottle | `bottle_dia` | 54.0 mm | Bottle body diameter (clip). |
| Bottle | `neck_dia` | 28.0 mm | Neck / cap diameter (tag, marker). |
| Label Window | `label_w` / `label_h` | 40 / 24 mm | Write-on window size. |
| Body | `wall` | 3.0 mm | Clip band / plate thickness. |
| Body | `clearance` | 0.5 mm | Per-side grip gap. |
| Body | `clip_h` | 18.0 mm | Clip band height. |

## Presets

- **Wash-Bottle Clip (54 mm)**.
- **Reagent Neck Tag**.
- **Cap Colour-Code Marker**.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Bottle Label Clip** (`profile`, internal) — the snap-on grip profile,
    defined by `bottle_dia`, `neck_dia`, `wall`, `clearance`. The clip mouth is
    a fixed fraction of the bottle diameter so it snaps and retains.
- **Material awareness:** `tolerance_by_material` is declared — a springier
  material snaps on with less clearance.
- **Societal benefit:** durable, relabelable identification for solvent bottles
  where adhesive labels fail, reducing mislabelling hazards.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- The label window is a shallow recess that never perforates the plate, so all
  outputs are **watertight**.
