# Enclosure Vent / Louvre Panel

Ventilation panels for electronics enclosures, generated with **CadQuery**
(B-Rep): a **solid mounting panel** with an airflow cutout pattern and a corner
screw-mount border. Three distinct profile modes trade open area for shielding.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Louvre Panel** | `louvre_panel` | Angled downward-raked louver slats cut through the panel — air passes but straight-on sight and falling debris do not. |
| **Hex Grille** | `hex_grille` | A honeycomb of hexagonal through-holes on a staggered grid: maximum open area with a stiff cell wall (the classic fan grille). |
| **Slot Vent** | `slot_vent` | Parallel straight (obround) slots — the simplest high-flow vent, easy to print without supports. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Panel | `panel_w` / `panel_h` | 80 / 80 mm | Overall panel size. |
| Panel | `thick` | 3 mm | Panel wall thickness. |
| Panel | `border` | 6 mm | Solid frame border around the vented area. |
| Openings | `open_size` | 6 mm | Slat gap / hex across-flats / slot width. |
| Openings | `rib` | 2 mm | Material between openings. |
| Openings | `louvre_ang` | 30° | Louver slat rake angle. |
| Mount | `screw_d` | 3.2 mm | Corner mount screw clearance (M3 ~3.2 mm). |

## Presets

- **80 mm Louvre Vent** — a raked-slat vent for an 80 mm fan opening.
- **80 mm Hex Fan Grille** — the honeycomb fan grille.
- **80 mm Slot Vent** — straight slots.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Vent Opening Pattern** (`profile`, *internal*) — the airflow cutout profile
    (`open_size`, `rib`, `louvre_ang`); the interface that sets open area vs.
    shielding.
  - **Corner Screw Mount** (`bolt_pattern`, *ISO 7045 M3*) — the mount holes.
- **Material awareness:** opening / rib fit tunes with `open_size` and `rib` per
  printer; `tolerance_by_material` is declared.
- **Societal benefit:** a hot printer, PC, or project box needs airflow, but a
  vent sized to your exact cutout with the open area and shielding you want is a
  bespoke part; a parametric louver / grille / slot on a screw-mount border fits
  ventilation to any enclosure opening.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **A vent is still a solid body.** Every opening is a boolean cut through a
  solid panel (each opens front→back — no trapped void); the border is filleted
  **before** cutting; the whole opening pattern is unioned into **one** cutter
  and subtracted once (fast + robust). Louver slots are obround (stadium) prisms
  cut on a raked plane; hex holes are polygon prisms; slots are obround. The hex
  and slat counts are capped so a large panel with tiny holes cannot explode the
  boolean. All three modes and the MIN/MAX extremes render watertight, one body.
