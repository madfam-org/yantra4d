# Sew-Through Button

The flat 2- or 4-hole button — generated with **CadQuery** (B-Rep). Fashion
Cabinet's [`sew-through-button`](https://fc.madfam.io) notion owns the fashion
semantics (ligne sizing, placket spacing, buttonhole math) and bridges to **this**
solid for the hardware.

This is the companion to [`shank-button-solid`](../../shank-button-solid), which
covers the shank and toggle forms. Most Fashion Cabinet garments call for the flat
sew-through form documented here.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Ligne sizing

Buttons are sold in **ligne** (L): 1 L = 0.635 mm — the button trade's unit, and
the same convention `shank-button-solid` uses. The cartridge computes
`diameter_mm = button_ligne × 0.635` internally, so an 18 L shirt placket in
Fashion Cabinet produces an 11.43 mm button here. Common sizes: shirt 16–20 L,
jacket 24–30 L, coat 32–45 L.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **One Button** | `button` | A single button. |
| **Button Card (batch)** | `card` | `card_count` identical buttons laid out in a row or grid for one print run. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Size | `button_ligne` | 24 L | Button size in ligne. `diameter_mm = button_ligne × 0.635`. |
| Size | `thickness` | 3.0 mm | Disc thickness. Caps the dish at 45% of this value. |
| Size | `dish_depth` | 0.8 mm | Concave thread dish around the holes; 0 gives a flat face. |
| Sew Holes | `hole_count` | 4 | 2 holes on a line, or 4 on a square. |
| Sew Holes | `hole_dia` | 1.5 mm | Sew hole diameter. |
| Sew Holes | `hole_spacing` | 4.0 mm | Centre-to-centre spacing, clamped inside the dish. |
| Batch | `card_count` | 6 | Buttons per card (`card` mode only). |

Hole size and spacing are solved together against the button diameter: on a small
ligne the cartridge pulls the spacing in and shrinks the holes rather than letting
them break into the dish wall or merge with each other. That is why `constraints`
is empty — every invalid combination is made impossible in `main.py`.

## Print notes

Print **face up** on the bed: the concave dish is cut from above and needs no
support, and the flat back becomes the seat against the placket. PLA or PETG at
0.12–0.16 mm layers gives clean hole walls; PETG survives laundering better. Small
buttons print well from recycled and offcut material
(`recycled_material_toggle` in the hyperobject profile). Every mode exports as a
watertight solid — holes are cut clean through both faces.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sew Face** (`flange`, internal) — the sewn face and its hole pattern,
    defined by `button_ligne`, `hole_count`, `hole_dia`, `hole_spacing`. **This is
    the dimensional-handshake flange** Fashion Cabinet measures against.
  - **Placket Seat** (`surface`, internal) — the footprint the button occupies on
    the garment, defined by `button_ligne`, `thickness`.
- **Commons license:** CERN-OHL-W-2.0

## Fashion Cabinet bridge

The FC-side `sew-through-button` notion carries:

```json
{
  "hardware_ref": {
    "platform": "yantra4d",
    "project_slug": "sew-through-button",
    "linked": true,
    "params_map": {
      "button_ligne": "button_ligne",
      "thickness": "button_thickness_mm",
      "hole_count": "button_hole_count",
      "hole_dia": "thread_dia_mm * 2.2",
      "hole_spacing": "button_ligne * 0.635 * 0.26",
      "card_count": "placket_button_count"
    }
  }
}
```

`button_ligne` passes straight through — FC already sizes plackets in ligne, and
the 0.635 mm conversion happens here. `hole_spacing` defaults to about 26% of the
button diameter, the classic sew-through proportion; `hole_dia` follows the thread
or cord FC specifies. `card_count` maps to the number of buttons a garment's
placket calls for, so one render produces the whole run.
