# Epaulette Board

A **structured shoulder board** — generated with **CadQuery** (B-Rep). The rigid hard
good Fashion Cabinet's `printed-epaulette` notion places and bridges to **here**. A
tapered plate (wide at the shoulder seam, narrow at the collar) with a raised rim and a
collar button post, it gives a uniform or costume shoulder its crisp military line.

Part of the AM-fashion capsule. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Shoulder Board** | `board` | Plate + raised rim + button post. |
| **Flat Plate** | `plate` | The tapered plate, no rim, for a softer look. |

## Parameters

| Parameter | Default | Notes |
| :--- | :--- | :--- |
| `board_len` | 140 mm | Shoulder seam to collar. |
| `wide_w` | 60 mm | Width at the shoulder seam. |
| `narrow_w` | 40 mm | Width at the collar end. |
| `plate_t` | 2.5 mm | Thicker = stiffer board. |
| `rim_h` / `rim_w` | 3 / 3 mm | Raised edge height and wall width. |
| `button_dia` | 10 mm | Collar button post size. |

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:** Shoulder-Seam Edge (`flange` — `board_len`, `wide_w`, `narrow_w`)
  and Collar Button Boss (`boss` — `button_dia`, `plate_t`).

## Fabrication notes

The plate is an extruded trapezoid (straight segments — no arcs); the rim is a taller
trapezoid with the plate footprint cut from its top so only a wall stands proud; the
button post is a small cylinder. Small boolean count → fast, watertight.
