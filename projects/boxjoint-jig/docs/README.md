# Box-Joint Indexing Jig

A box- (finger-) joint indexing jig generated with **CadQuery** (B-Rep). The
registration key is exactly one finger wide and sits one finger-width from the
cut, so each pass drops onto the previous notch and steps the workpiece over by
a perfect pitch. Choose the master index key, a backer fence with a fixed index
pin, or an adjustable slotted carrier for fine tuning.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Index Key** | `index_key` | A comb of `n_fingers` fingers at `finger_w` pitch — the reference that sets the joint spacing. |
| **Fence + Index Pin** | `fence_jig` | A backer fence with a bit-clearance slot and one index pin standing one finger-width to the side. |
| **Adjustable Carrier** | `adjustable` | A fence whose index pin rides a slotted carrier locked by a fixing bolt for fine pitch adjustment. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Joint Geometry | `finger_w` | 6.0 mm | Finger width — equals the joint pitch (finger and gap are equal). |
| Joint Geometry | `mat_thick` | 12.0 mm | Stock thickness — sets the finger depth. |
| Joint Geometry | `n_fingers` | 7 | Fingers on the master index key. |
| Fence & Base | `fence_len` / `fence_h` | 160 / 50 mm | Backer fence length and height. |
| Fence & Base | `base_t` | 10.0 mm | Jig base rail thickness. |
| Adjustment | `bolt_bore` / `slot_len` | 5.5 / 30 mm | Fixing-bolt bore and slotted-carrier travel. |

## Presets

- **Small Box Key (6mm)** — a seven-finger master key for small boxes.
- **Drawer Fence (10mm)** — a fixed-pin backer fence for 10 mm drawer joinery.
- **Fine-Adjust Carrier (8mm)** — a slotted carrier for tuning an 8 mm joint.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Finger-Joint Index** (`profile`, internal) — the finger/gap comb defined
    by `finger_w`, `mat_thick`, `n_fingers`. Two jigs of the same `finger_w`
    cut mating halves that interlock.
  - **Adjustment Slot** (`rail`, internal) — `slot_len`, `bolt_bore`; the
    slotted carrier that tunes pin position.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` —
  finger width can be trimmed for a snug fit per material and blade/bit kerf.
- **Societal benefit:** repeatable, tight box joints — the strongest simple
  corner joinery — from a shop-made jig instead of a dedicated dovetail machine.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
