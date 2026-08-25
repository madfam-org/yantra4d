# Corset Busk

The **two-part front-closure busk** of a corset — generated with **CadQuery** (B-Rep).
The rigid hard good Fashion Cabinet's `printed-corset-busk` notion places and bridges to
**here**. One plate carries stud knobs; the mating plate carries keyhole slots that drop
over them, so the corset front opens and closes **without unlacing**. A hard finding
printed rigid (PLA/PETG), it replaces the traditional spring-steel busk.

Part of the AM-fashion capsule. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Busk** | `busk` | Both plates side by side, print-ready. |
| **Knob plate** | `knob_side` | The stud-knob plate. |
| **Keyhole plate** | `loop_side` | The keyhole-slot plate. |

## Parameters

| Parameter | Default | Notes |
| :--- | :--- | :--- |
| `busk_len` | 300 mm | Length down the corset front. |
| `plate_w` | 16 mm | Width of each plate. |
| `plate_t` | 3.0 mm | Thicker = stiffer front. |
| `knobs` | 5 | Closure points. |
| `knob_dia` | 6 mm | Knob head size. |
| `post_dia` | 3.5 mm | Knob post; the keyhole slot fits this. |

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Sewn Busk Edge (`flange` — `busk_len`, `plate_w`, `plate_t`) and
  Knob-and-Keyhole Cell (`snap` — `knob_dia`, `post_dia`).

## Fabrication notes

Each plate is a thin box; knobs are cylinders on posts; keyholes are a round hole plus a
drop slot cut through the mating plate, leaving a margin so it never splits. Print flat
in a rigid filament; the knob plate needs no support.
