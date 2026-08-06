# Paracord Buckle / Jig

Cord tooling for **550 paracord** (7-strand nylon, **~4 mm outer diameter**),
generated with **CadQuery** (B-Rep). One cord-diameter interface drives a
single-piece webbing buckle, an adjustable bracelet weaving jig, and a friction
barrel cord lock — size them all to your cord and weave, buckle and finish in the
field.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Side-Release Buckle** | `side_buckle` | A single-piece tri-glide / ladder-lock webbing slider: a closed frame with a centre bar and two windows. The strap threads over the bar and back, and tension locks it — the standard one-piece printable buckle. |
| **Bracelet Weaving Jig** | `bracelet_jig` | A flat board with two end blocks (each with a cord anchor bore) and a row of pins that set the finished bracelet length. |
| **Barrel Cord Lock** | `cord_lock` | A rounded barrel with two parallel bores for a doubled cord and an angled pinch slot — friction holds, squeeze to slide. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cord & Fit | `cord_d` | 4.0 mm | Cord outer diameter. 550 paracord is ~4 mm. |
| Cord & Fit | `wall` | 3.0 mm | Structural wall / part thickness. |
| Cord & Fit | `clearance` | 0.35 mm | Per-side clearance for cord bores and snap fits. |
| Buckle | `strap_w` | 25.0 mm | Webbing width the buckle wraps. 25 mm = 1 inch. |
| Jig | `jig_len` | 120.0 mm | Board length; sets the maximum bracelet size. |
| Jig | `pin_count` | 6 | Number of pins in the length-setting row. |
| Cord Lock | `lock_len` | 22.0 mm | Length of the cord-lock barrel. |

## Why the cord diameter is the interface

Every part sizes to `cord_d`, so a single value keeps a whole kit consistent.
The buckle's clear width is `strap_w + 2·clearance`; the jig's anchor bores and
the cord lock's twin bores are `cord_d + clearance` in diameter. 550 paracord's
nominal OD is ~4 mm, so the 4 mm default fits genuine 550 cord with a light
friction; drop `clearance` for a tighter grip or raise it for a free slide. The
buckle defaults to a 25 mm (1 in) strap, the most common webbing width.

## Presets

- **Standard 550 Buckle (1 in)** — the reference webbing buckle at 25 mm.
- **Bracelet Jig (6 pins)** — a 120 mm board for typical wrist sizes.
- **Double-Cord Lock** — a barrel sized for a doubled 4 mm cord.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **550 Paracord Channel** (`snap`, *550 paracord (~4mm)*) — the cord bore /
    grip interface, defined by `cord_d`, `clearance`. Any part built to the same
    cord diameter shares cordage with the rest of the kit.
  - **1 in Webbing Slot** (`profile`, *25mm webbing*) — the buckle's strap
    windows, defined by `strap_w`, for 1-inch webbing.
- **Material awareness:** `tolerance_by_material` is declared — `clearance` and
  the cord/strap dimensions are exposed so the grip fit tunes per material and
  printer.
- **Societal benefit:** 550 paracord is the universal field cordage; printable
  buckles, jigs and cord locks sized to the same cord let anyone make and repair
  cord tools without proprietary hardware, keeping a survival kit self-sufficient.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Each part is **one solid**: the buckle is a filleted slab with two obround
  (`slot2D`) windows bored through; the jig's pins are solid cylinders unioned to
  a solid base and the anchor bores vent top-and-bottom; the cord lock's bores
  and pinch slot vent to outside faces. Fillets are applied to clean blanks
  before feature cuts and wrapped in try/except. All shipped modes and presets —
  and the parameter extremes — render **watertight** (`body_count == 1`) in well
  under 20 s.
