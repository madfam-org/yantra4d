# Watch Band Adapters & Stands

Watch-lug hardware generated with **CadQuery** (B-Rep), sized to the standard
**18 / 20 / 22 mm** lug widths, all built around one spring-bar **lug interface**.
A lug-to-strap adapter, an angled watch display stand, and a charger dock.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Band Adapter** | `band_adapter` | Two lug ears (clip to the watch) plus a strap slot (thread a 2-piece strap / paracord). |
| **Watch Stand** | `watch_stand` | An angled cradle stand the watch head rests in, lugs down. |
| **Charger Dock** | `charger_dock` | A puck dock with a recessed well for a round charger and lug ears so the watch clips in face-up. |

## The lug interface (quick-release)

Every part shares one **Watch Lug** interface: two ears whose **gap equals the
lug width** (verified: 20.0 mm gap for the 20 mm setting) with a blind spring-bar
pin bore of `pin_dia` in each ear on the standard spring-bar axis. The
quick-release / spring bar itself is a metal part that drops in — the geometry is
the correct mating envelope, not a printed spring.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Watch Lug | `lug_width` | 20mm | 18 / 20 / 22 mm (the ear gap). |
| Watch Lug | `pin_dia` | 1.6 mm | Spring-bar / quick-release pin diameter. |
| Watch Lug | `ear_h` | 8.0 mm | Lug ear height. |
| Strap | `strap_t` | 3.0 mm | Strap thickness the adapter slot accepts. |
| Stand & Dock | `watch_dia` | 44 mm | Watch head diameter for cradle / well. |
| Stand & Dock | `stand_angle` | 55° | Display cradle lean. |
| Build | `wall` | 3.0 mm | Wall / ear thickness. |

## Presets

- **20 mm Strap Adapter** — lug-to-strap for a 20 mm watch.
- **44 mm Display Stand** — an angled cradle for a 44 mm head.
- **Nightstand Charger Dock** — a charger puck with lug ears.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Watch Lug** (`socket`, 18/20/22mm lug) — the spring-bar lug interface,
    defined by `lug_width`, `pin_dia`, `ear_h`, `wall`. Shared across all parts.
  - **Strap Slot** (`rail`, internal) — the adapter's strap pass-through, defined
    by `lug_width`, `strap_t`.
- **Material awareness:** the pin bore and ear clearances are exposed so the fit
  can be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** standard-lug adapters and stands let one watch head move
  between straps, a display cradle, and a charger without proprietary accessories.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard. The final solid is assigned to `result`.
- The lug ears carry blind pin bores on the spring-bar axis — the interface is
  dimensionally real for a 1.0-2.5 mm quick-release bar.
- All shipped presets and defaults render **watertight**.
