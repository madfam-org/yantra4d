# Spool / Bobbin Holder

An organiser for **sewing-machine bobbins and thread spools**, generated with
**CadQuery** (B-Rep). The functional interface is the bobbin **bore** — sized to
real sewing standards — and a peg the bobbin drops onto.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bobbin Rack** | `bobbin_rack` | A base plate with a grid of upright pegs; each peg carries one bobbin/spool by its centre bore, spaced so flanges clear. |
| **Spool Pin** | `spool_pin` | A single tall spool post leaning on a weighted disc foot — a machine-top / free-standing thread stand. |
| **Well Tray** | `bobbin_tray` | A shallow tray whose top face carries a grid of round wells; loose bobbins lie flat so they can't unwind. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bobbin / Spool | `bobbin_type` | `class15` | Class 15 (20.3 mm, 6.1 mm bore), L-style (narrower flange), or thread spool (~6.5 mm core). |
| Layout | `count` / `rows` | 6 / 1 | Grid of pegs (rack) or wells (tray). |
| Layout | `peg_h` | 16.0 mm | Peg height (rack). |
| Bobbin / Spool | `peg_clear` | 0.4 mm | Per-side gap between peg and bore — tune per printer/material. |
| Layout | `base_th` | 4.0 mm | Base plate / tray floor thickness. |
| Spool Pin | `pin_h` / `pin_tilt` | 60.0 mm / 8° | Free-standing pin height and lean. |

## Real dimensions (why bobbins fit)

Household sewing settled on two interchangeable flat bobbins: **Class 15** and
**L-style**, both **20.3 mm** in outer diameter with a **6.1 mm** centre hole.
Class 15 is 11.7 mm wide; L-style is the narrower 8.9 mm. Small thread spools
have a ~6.5 mm core, so the **same 6 mm peg** carries both — one rack holds a
mixed drawer. The peg diameter is the bore minus `peg_clear` per side so the
bobbin slides on without wobble.

## Presets

- **6-Bobbin Class 15 Rack** — the everyday sewing-drawer rack.
- **Leaning Spool Pin** — a free-standing thread post that feeds off the top.
- **12-Well Bobbin Tray** — a flat tray that stops loose bobbins unwinding.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Bobbin Bore + Peg** (`socket`, *Class 15 / L-style bobbin,
  6.1 mm bore, 20.3 mm OD*) — the peg + spacing, defined by `bobbin_type` and
  `peg_clear`. Any holder built to the same bore interoperates with Singer,
  Janome, Juki, Brother and Elna bobbins.
- **Material awareness:** `tolerance_by_material` is declared — `peg_clear` is
  exposed so the bore fit tunes per material/printer.
- **Societal benefit:** bobbins and spools are a universal small-parts nuisance;
  a printed rack or tray organises any household sewing kit and adapts to how
  many spools a maker owns.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Pegs are **solid** cylinders unioned onto the base (no hollow-post cavity);
  wells are blind pockets bored from the open top (vented); the spool-pin cap is
  a **loft frustum** (no sphere-pole meshing crack). All modes render
  **watertight**, single-body, well under the estimate threshold.
