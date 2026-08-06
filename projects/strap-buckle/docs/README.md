# Webbing Buckle & Adjusters

Standard side-release buckle and strap adjusters generated with **CadQuery**
(B-Rep), sized to **20 / 25 / 38 mm** webbing. A two-part buckle whose male
prongs snap into the female housing, a ladder-lock slider, and a tri-glide. Every
part shares one webbing-slot helper, so the bar a strap threads through is
identical across the family.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Side-Release Buckle** | `side_release` | An **assembly**: the female housing and male plug nested together, male barbs seated in the female side windows. |
| **Strap Slider** | `slider` | A single-bar ladder-lock strap adjuster. |
| **Tri-Glide** | `tri_glide` | A three-bar slide (two slots) for fixing a webbing end. |

## The snap fit (male → female)

The male has two cantilever prongs. At rest their **outer span equals the female
cavity width minus `snap_clear` per side** (0.4 mm each side at defaults), so they
slide in; each prong carries a **barb standing proud by `snap_ledge`** (1.4 mm)
that springs out and catches behind the female's side windows. The prongs flex
inward during insertion. Verified dimensionally: at 25 mm webbing the female
cavity is 25.8 mm and the male prong span is 25.0 mm → 0.4 mm per-side clearance.
`show_gap` slides the male out for an exploded view.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Webbing | `webbing` | 25mm | 20 / 25 / 38 mm nominal width. |
| Webbing | `web_t` | 2.0 mm | Strap thickness. |
| Snap Fit | `snap_clear` | 0.4 mm | Per-face gap between the halves. |
| Snap Fit | `snap_ledge` | 1.4 mm | Barb ledge that latches the windows. |
| Snap Fit | `show_gap` | 0 mm | Exploded-view offset (cosmetic). |
| Build | `wall` | 2.4 mm | Structural wall / bar thickness. |

## Presets

- **25 mm Side-Release Buckle** — the everyday pack/strap buckle.
- **38 mm Pack Buckle** — heavier webbing.
- **20 mm Strap Slider** — a narrow strap adjuster.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Side-Release Snap** (`snap`, 20/25/38mm webbing) — the male/female snap
    engagement, defined by `webbing`, `snap_clear`, `snap_ledge`, `wall`.
  - **Webbing Slot** (`rail`, 20/25/38mm webbing) — the strap pass-through,
    defined by `webbing`, `web_t`. One helper feeds every slot in the cartridge.
- **Material awareness:** `snap_clear` is exposed so the printed fit can be tuned
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** field-replaceable buckle hardware for the standard
  webbing widths — repair a pack, sling, or strap instead of discarding gear.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard. The final geometry is assigned to
  `result`; `side_release` returns a two-body `cq.Assembly`.
- All shipped presets and defaults render **watertight**.
