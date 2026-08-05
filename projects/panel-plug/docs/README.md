# Panel / Blind Grommet & Plug

A snap-in plug generated with **CadQuery** (B-Rep) that fills an unused knockout
hole in a panel or enclosure. The body passes through the hole; a **flange** caps
the top face; a **snap lip** below the panel retains it. The snap groove is sized
to the panel thickness so flange and lip clamp the panel between them.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Blind Plug** | `blind_plug` | A solid closed plug that blanks the hole (hollowed underside so the lip flexes). |
| **Cable Grommet** | `cable_grommet` | A ring with a central cable bore `cable_dia` that protects a wire run. |
| **Vented Plug** | `vented_plug` | Radial slots for airflow while keeping the hole covered. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## How the snap works

- The **shank** is `hole_dia − 2·hole_fit` so it slips into the hole.
- The **flange** overhangs the hole edge by `flange_w` and seats on the top face.
- The **snap lip** widens to `shank_r + snap_fit` just below the panel; on
  insertion it flexes inward, then springs out to catch under the panel. The
  clamped span equals `panel_t`.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Knockout Hole | `hole_dia` | 20.0 mm | The knockout it fills. |
| Knockout Hole | `panel_t` | 2.0 mm | Panel thickness (sets the snap groove). |
| Knockout Hole | `hole_fit` | 0.3 mm | Per-side shank clearance. |
| Flange & Snap | `snap_fit` | 1.2 mm | Lip engagement under the panel. |
| Flange & Snap | `flange_w` / `flange_t` | 3.0 / 2.0 mm | Flange overhang / cap height. |
| Flange & Snap | `wall` | 2.0 mm | Wall around the flex cavity / cable bore. |
| Type Options | `cable_dia` | 8.0 mm | Cable grommet through-bore. |
| Type Options | `vents` | 6 | Vented-plug slot count. |

## Presets

- **M20 Conduit Blank** — blanks a 20 mm knockout in a 2 mm panel.
- **6 mm Cable Pass-Through** — a grommet for a 6 mm cable in a 1.5 mm panel.
- **Vented Fan Blank** — an 8-slot vented cover for a 30 mm hole.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Panel Knockout Plug** (`snap`, internal) — the retaining snap interface,
    defined by `hole_dia`, `panel_t`, `hole_fit`, `snap_fit`, `flange_w`. Any
    plug built to the same hole + panel thickness snaps into the same panel.
  - **Cable Bore** (`socket`, internal) — the grommet through-bore, `cable_dia`,
    `wall`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` are
  declared. Snap fits are clearance-sensitive; `hole_fit` and `snap_fit` are
  exposed so the fit can be tuned per material/printer.
- **Societal benefit:** finishes enclosures without buying vendor blanking plugs
  — one parametric snap plug blanks any knockout, protects a cable run, or vents
  a panel.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
