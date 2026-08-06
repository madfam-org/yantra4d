# SBS/SLAS Microplate Tray

Labware built on the ANSI/SLAS microplate footprint (**127.76 x 85.48 mm**),
generated with **CadQuery** (B-Rep), so it drops into standard lab automation,
stackers, and readers.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Holder Tray** | `holder` | A tray with a footprint-sized recess a commercial plate seats in, plus a finger cutout to lift it. |
| **96-Well Plate** | `plate_96` | 12 x 8 wells at 9 mm pitch (~6.5 mm wells). |
| **24-Well Plate** | `plate_24` | 6 x 4 wells (~18 mm pitch, ~15.6 mm wells). |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the
dispatched values (`holder` / `plate_96` / `plate_24`). The `plate_format`
selector mirrors the mode for the standalone/preview path.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Format | `plate_format` | holder | Mirrors the active mode. |
| Wells & Body | `plate_h` | 14 mm | Overall height. |
| Wells & Body | `well_depth` | 10 mm | Well depth (plates); a solid floor remains. |
| Wells & Body | `wall` | 2.0 mm | Rim around / floor beneath wells. |
| Wells & Body | `clearance` | 0.6 mm | Gap around a plate in the holder. |

The footprint length (127.76), width (85.48), 9 mm pitch, and ~3 mm corner radius
are fixed constants matching the standard.

## Presets

- **Standard Plate Holder** — a tray for a commercial microplate.
- **Shallow 96-Well** — a simple flat 96-well plate.
- **Deep 24-Well** — a deeper 24-well plate.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **SLAS Microplate Footprint** (`grid`, *ANSI/SLAS 1-2004 & 4-2004 (9mm
    pitch)*) — the standardized outer footprint and 9 mm well grid, driven by
    `plate_format`, `well_depth`, `plate_h`. Anything printed here matches the
    footprint that lab robots, readers, and stackers expect.
- **Material awareness:** `clearance` is exposed so the holder recess fit can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** the SLAS footprint is the universal interface of lab
  automation; printing to that exact standard lets low-resource and teaching labs
  integrate custom or single-use labware into equipment they already own.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- Every part is a solid SLAS-footprint slab; wells and the holder recess are
  blind pockets that keep a solid floor, and the lift cutout is a clean edge
  scallop — all shipped presets render **watertight**.
