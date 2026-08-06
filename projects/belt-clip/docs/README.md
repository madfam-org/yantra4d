# Belt Clip & Holster

Belt-worn carry hardware generated with **CadQuery** (B-Rep), sized to your real
belt width and thickness. A sprung belt clip that snaps over the belt, a device
pocket holster with an integral belt loop, and a bare belt loop you can graft
onto anything.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Belt Clip** | `clip` | A back plate with a curved sprung tongue that hooks over the belt's top edge and pinches it against the plate. |
| **Holster** | `holster` | A device pocket (open-top box) with an integral belt loop on the back. |
| **Belt Loop** | `belt_loop` | The bare belt-loop tube plus mounting holes. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Belt Fit | `belt_w` | 38 mm | Belt width the clip/loop rides on. Drives every part. |
| Belt Fit | `belt_t` | 4.0 mm | Belt thickness (leather ≈ 3-5 mm). |
| Belt Fit | `loop_clear` | 1.5 mm | Slide clearance inside the loop. |
| Clip | `clip_reach` | 46 mm | How far the sprung tongue reaches down. |
| Clip | `clip_clear` | 0.6 mm | Tongue-to-plate gap = belt bite. |
| Pocket | `pocket_w` / `pocket_d` / `pocket_h` | 62 / 16 / 90 mm | Interior pocket size. |
| Build | `wall` | 3.0 mm | Structural wall thickness. |

## Presets

- **Standard 38 mm Clip** — the everyday belt clip.
- **Phone Holster** — a slim 76×12×158 pocket on a 40 mm belt loop.
- **Wide Work-Belt Loop** — a 50 mm loop for a thick work belt.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Belt Clip** (`snap`, internal) — the sprung clip geometry, defined by
    `belt_w`, `belt_t`, `clip_reach`, `clip_clear`, `wall`. The belt bite is
    `belt_t + clip_clear`.
  - **Belt Loop Slot** (`snap`, internal) — the belt pass-through, defined by
    `belt_w`, `belt_t`, `loop_clear`, `wall`. Shared with the holster via one
    webbing-slot helper so every pass-through sizes identically.
- **Material awareness:** clip and loop clearances (`clip_clear`, `loop_clear`)
  are exposed so the fit can be tuned per material/printer; `tolerance_by_material`
  is declared.
- **Societal benefit:** belt carry sized to the exact belt, extending the life of
  tools, phones, and gear instead of single-fit store accessories.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The clip's spring is a printed compliant tongue (a living hinge at the top
  root) — no separate parts, no hardware.
- All shipped presets and defaults render **watertight**.
