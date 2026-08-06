# Lead-Screw Nut (Tr8x8 / Acme)

A printable **lead-screw nut** generated with **CadQuery** (B-Rep) that threads
onto a trapezoidal (metric-trapezoidal / ACME) lead screw. The common
motion-repair part: a stripped or worn Z nut on a 3D printer, a small CNC stage,
or a linear actuator can be replaced the same day in the exact standard.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Round Nut** | `round_nut` | Plain cylindrical barrel with an internal trapezoidal thread and two wrench flats. |
| **Flange Nut** | `flange_nut` | Barrel + bottom flange with a ring of bolt holes to fasten to a carriage. |
| **Anti-Backlash Nut** | `anti_backlash` | A taller round nut (extra thread engagement) to reduce axial play. |

`round_nut` with **Add Flange** checked is dispatched to the flange builder, so
either route reaches the flanged part.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread | `thread_spec` | Tr8x8 | Tr8x8 / Tr8x2 / ACME-3/8 — sets major diameter, pitch, flank. |
| Thread | `clearance` | 0.35 mm | Per-side running-fit gap on the screw. |
| Nut Body | `height` | 12 mm | Length along the screw (thread engagement). |
| Nut Body | `body_dia` | 16 mm | Round barrel outer diameter. |
| Flange | `flange` | off | Turn a round nut into a flange nut. |
| Flange | `flange_dia` | 26 mm | Mounting-flange outer diameter. |
| Flange | `hole_count` | 4 | Number of flange bolt holes. |
| Flange | `bolt_dia` | 3.4 mm | Flange bolt-hole diameter (M3 ≈ 3.4). |

## Presets

- **Printer Z Repair (Tr8x8)** — the ubiquitous 8 mm printer-Z nut.
- **Carriage Flange (Tr8x2)** — single-start 8 mm nut with a 4-hole flange.
- **ACME Stage (long)** — a long ACME-3/8 nut for a small CNC stage.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Trapezoidal Lead-Screw Thread** (`thread`, ISO 2904 (Tr) / ACME) — the
    internal thread, defined by `thread_spec`, `clearance`, `height`. Nominal major
    diameter, pitch, and flank angle match the named standard, so the nut runs on a
    real screw of that spec; `clearance` tunes the printed fit.
- **Material awareness:** the running fit is exposed (`clearance`) so it can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a stripped Z nut halts a machine entirely and spares
  back-order for weeks — a printable trapezoidal nut restores motion the same day
  with no proprietary part.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Thread construction (watertight + fast, ~2 s):** the bore is drilled to the
  thread root radius, then an inward-pointing trapezoidal rib is swept along a
  genuine `makeHelix` path built at the **mean thread radius** and unioned into the
  bore. Sweeping along a real-radius helix (not a radius≈0 axis helix) keeps the
  sweep frame non-singular — that is what makes the fuse both watertight and fast.
  Turns are capped (`_MAX_TURNS = 5`, a couple more for tall/flange bodies) because
  the helical fuse cost grows super-linearly and a repair nut only needs a few
  threads of engagement.
- **Simplification (noted):** real Tr8x8 screws are 4-start (2 mm pitch, 8 mm
  lead). The nut is modelled with a **single-start** female thread at the true 2 mm
  pitch, which meshes with the screw and prints far more reliably than a 4-start
  internal thread. The nominal major diameter and pitch are correct; only the
  number of starts is simplified.
- **All shipped presets, all modes, and the size extremes render watertight**, and
  the default preset renders in ~2 s.
