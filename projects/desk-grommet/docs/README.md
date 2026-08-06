# Cable Grommet / Desk Port

A grommet that drops into a round cable pass-through hole in a desk, generated
with **CadQuery** (B-Rep). A tubular body sized to the desk bore, a flange lip
that rests on the desktop, and an open cable slot so cords route in from the side
without threading. Includes a closed round variant and a matching lid.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Grommet (slotted)** | `grommet` | Ring + flange with an open side cable slot; cords drop in without unplugging. |
| **Round Grommet (closed)** | `round_grommet` | The closed ring (no slot); cords are threaded through. |
| **Lid** | `grommet_lid` | A cap that seats in the flange, with its own cable slot. |

Render each mode with `target_part` set to that mode's part id to see the
distinct part.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Desk Bore | `bore_dia` | 60 mm | Diameter of the desk hole the grommet fits into. |
| Desk Bore | `depth` | 25 mm | How far the body drops below the flange (desk thickness). |
| Desk Bore | `wall` | 2.5 mm | Tube wall thickness. |
| Desk Bore | `fit_clear` | 0.4 mm | Per-side slip-fit clearance into the bore. |
| Flange | `flange` | 6.0 mm | Lip width beyond the bore. |
| Flange | `flange_t` | 3.0 mm | Flange plate thickness. |
| Cable Slot & Lid | `slot` | on | Open cable channel (slotted grommet). |
| Cable Slot & Lid | `slot_w` | 20 mm | Cable slot width. |
| Cable Slot & Lid | `lid` | on | Recess the flange top so the lid sits flush. |
| Cable Slot & Lid | `lid_slot_w` | 14 mm | Cable slot width in the lid. |

## Presets

- **Standard 60 mm Port** — the common desk grommet size, slotted.
- **Small Closed 35 mm** — a closed round grommet.
- **60 mm Lid** — the matching cap.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Desk Bore Grommet** (`profile`, internal) — the body cross-section, defined
    by `bore_dia`, `depth`, `wall`, `fit_clear`. Sized to whatever hole is
    already drilled.
  - **Open Cable Slot** (`profile`, internal) — `slot`, `slot_w`: the side channel
    that lets cords route in without threading.
  - **Lid Seat** (`snap`, internal) — `lid`, `bore_dia`, `flange`, `flange_t`: the
    flange rebate the matching lid seats into.
- **Material awareness:** `fit_clear` is exposed and `tolerance_by_material` is
  declared so the bore slip fit can be tuned per filament/printer.
- **Societal benefit:** a slotted desk grommet tidies cable clutter without
  unplugging anything and replaces the mismatched plastic ports desks ship with.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`
  and the active part is selected through `target_part`.
- All shipped presets and defaults render **watertight**.
