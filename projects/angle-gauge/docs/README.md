# Angle Gauge / Setup Block

Precision angle references generated with **CadQuery** (B-Rep) for setting saw
blades, bevels, miters and fences. A setup block stacks several known-angle
wedges into one stepped tool; a protractor gauge fans reference edges from a
common vertex; a saw gauge is a single-angle reference block that seats against a
blade to set the bevel.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Setup Block** | `setup_block` | A staircase of wedges, one per angle in the chosen set, each hypotenuse a known reference angle. |
| **Protractor Gauge** | `protractor_gauge` | A quarter-round plate with an engraved reference ray for each angle, fanning from a common vertex. |
| **Saw Gauge** | `saw_gauge` | A single wedge of `single_ang` on a flat base with a finger notch, to set a saw or table bevel. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Angle Set | `angles` | common | **common** (15/22.5/30/45), **fine** (5/10/15/20), **roofing** (18.4/26.6/33.7/45 pitches). |
| Size | `size` | 50.0 mm | Length of each angle's reference face. |
| Size | `width` | 30.0 mm | Tool width (bearing surface). |
| Size | `base_t` | 8.0 mm | Thickness of the flat base under the wedges. |
| Saw Gauge | `single_ang` | 45.0° | The single reference angle of the saw gauge. |

## Presets

- **Shop Setup Block (common)** — the four everyday angles in one block.
- **Bevel Protractor (fine)** — a low-angle protractor for fine bevels.
- **45° Miter Saw Gauge** — a single-angle miter reference.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Angle Reference** (`profile`, internal) — the reference faces defined by
    `angles`, `size`, `single_ang`. The `angles` select maps to a real set of
    degrees (roofing angles are the standard 4:12 … 12:12 pitches).
  - **Register Base** (`profile`, internal) — `width`, `base_t`; the flat base
    that seats the gauge on the table.
- **Material awareness:** `shrinkage_compensation` — angle faces stay accurate
  when the print's dimensional shrink is compensated.
- **Societal benefit:** a machinist's setup-block set for pennies — repeatable,
  accurate angles for saw bevels, miters and fences.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`. `math` is used
  for the wedge trigonometry.
- All shipped presets and defaults render **watertight**. Note that an XZ
  workplane extrudes along −Y, so each wedge is re-centred on Y=0.
