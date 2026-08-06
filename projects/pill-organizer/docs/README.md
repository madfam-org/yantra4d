# Pill Organizer

A compartmentalized pill box generated with **CadQuery** (B-Rep). Lay out
compartments as a 7-day week, a 7-day AM/PM (14) grid, or a custom `cols x rows`
arrangement.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Tray (open)** | `tray` | Open compartment tray sized by the schedule. |
| **Tray + Sliding Lid** | `tray_lidded` | The tray with side rails plus a sliding lid that seals every compartment (printed alongside). |
| **Single Travel Box** | `single_day` | One compartment as a friction-cap travel box (cap printed alongside). |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the
dispatched values (`tray` / `tray_lidded` / `single_day`) so every mode renders
its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Schedule | `days` | 7day | `7day` (1x7), `7day_2x` (AM/PM 2x7), or `custom`. |
| Schedule | `custom_cols` / `custom_rows` | 4 / 2 | Grid when `days = custom`. |
| Compartment | `cell` | 26 mm | Inner square size of each compartment. |
| Compartment | `cell_depth` | 18 mm | Compartment depth. |
| Compartment | `wall` / `floor` | 2.0 / 2.0 mm | Walls between/around, and tray floor. |
| Closure | `lid` | sliding | `sliding`, `individual`, or `none` (lidded mode). |
| Closure | `clearance` | 0.4 mm | Lid / friction-cap fit gap. |

## Presets

- **Classic Weekly (1x7)** — the standard seven-day organizer.
- **AM/PM Lidded (2x7)** — fourteen compartments with a sliding lid.
- **Travel Box** — a single friction-cap compartment for the pocket.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Compartment Grid** (`grid`, internal) — the compartment field, defined by
    `days`, `custom_cols`, `custom_rows`, `cell`, `wall`.
  - **Sliding Lid Rail** (`rail`, internal) — the tongue-and-groove rail the lid
    rides in, tuned by `clearance` and `wall`.
- **Material awareness:** `clearance` is exposed so the sliding/friction fit can
  be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** medication adherence is a daily-living challenge for
  older and disabled people; an organizer sized to the user's own pill count and
  grip needs supports independent, correct dosing.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- Pockets always leave a floor beneath them and full walls between them; the lid
  and cap are separate manifold solids — all shipped presets render **watertight**.
