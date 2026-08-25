# Button

The printable solid button — generated with **CadQuery** (B-Rep). Fashion
Cabinet's [`shank-button`](https://fc.madfam.io) notion owns the fashion
semantics (ligne sizing and the placket placement guide) and bridges to **this**
solid for the hardware.

Slug is `shank-button-solid` to disambiguate from the Fashion Cabinet notion
(`shank-button`), which is the 2-D placement guide, not the solid.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Ligne sizing

Buttons are sold in **ligne** (L): 1 L = 0.635 mm. Fashion Cabinet maps
`diameter_mm = button_ligne × 0.635`, so a shirt's 18 L placket produces an
18 L → 11.43 mm button here. Common sizes: shirt 16–20 L, jacket 24–30 L, coat
32–45 L.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Shank Button** | `shank` | A domed button with a closed thread loop on the back (no face holes). |
| **Sew-through (2 / 4 hole)** | `sew_through` | A flat button with a raised rim, a shallow thread well, and 2 or 4 face holes. |
| **Barrel Toggle** | `toggle` | A rounded barrel toggle with a transverse thread channel (duffle-coat closure). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Size | `diameter_mm` | 15.24 mm | Button diameter (24 L). `diameter_mm = button_ligne × 0.635`. |
| Size | `thickness` | 3.2 mm | Body thickness (also sets the toggle barrel radius). |
| Size | `rim` | 0.8 mm | Raised rim on a sew-through button. |
| Holes | `holes` | 4 | 2-hole or 4-hole sew-through. |
| Holes | `hole_dia` | 1.6 mm | Sew-hole / shank bore / toggle channel diameter. |

## Presets

- **Shirt Button** — 18 L, 4-hole sew-through.
- **Coat Button** — 36 L shank.
- **Duffle Toggle** — a barrel toggle.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Thread Path** (`socket`, internal) — the holes/bore/channel the thread runs
    through, defined by `hole_dia`, `holes`.
  - **Button Face** (`boss`, internal) — the visible face, defined by
    `diameter_mm`, `thickness`.
- **Fashion Cabinet bridge:** `shank-button.hardware_ref.params_map` maps
  `diameter_mm → button_ligne * 0.635`.

## Fabrication notes

Every part exports as a watertight solid; sew holes and the toggle channel are cut
clean through both faces. The shank ring is a **half/closed torus** loop; print the
shank button face-down so the loop bridges cleanly. Buttons print well in recycled
and offcut material (`recycled_material_toggle` in the profile).
