# Keyed / Spline Hub Adapter

A **torque-transmitting hub** generated with **CadQuery** (B-Rep) that couples a
printed part (pulley, arm, gear, knob) to a motor shaft, gearbox output, or
actuator. Three interchangeable internal bores — **keyway**, **involute spline**,
and **hex** — plus an optional outer mounting flange with a bolt-hole circle.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Parts

| Part | Bore | Description |
| :--- | :--- | :--- |
| **Keyed Hub** (`keyed_hub`) | `keyway` | A round bore plus a rectangular key slot — a parallel key transmits torque. |
| **Spline Hub** (`spline_hub`) | `involute_spline` | A toothed bore with N teeth so many flanks share the load. |
| **Hex Hub** (`hex_hub`) | `hex` | A hexagonal bore for hex shafts / hex drivers. |

The studio dispatches the active part via `target_part`; each part forces its
matching `bore_type`.

## Bore geometry (verified)

| Bore | Key dimension | Result |
| :--- | :--- | :--- |
| Keyway | round bore = `shaft_dia + clearance`; slot = `key_width + clearance` wide, `key_depth` deep past the bore | At 8 mm / 0.2 mm: bore Ø 8.2 mm, slot walls at ±1.6 mm, slot 1.8 mm deep. |
| Hex | across-flats = `shaft_dia + clearance` | At 8 mm / 0.2 mm: across-flats **8.20 mm** (6 corners at R = 4.73 mm). |
| Spline | `spline_teeth` grooves around a pitch bore = `shaft_dia + clearance` | 6 teeth → 6 grooves; 12 teeth → 12 grooves. |

> **Note on the spline:** the involute spline is an **approximate**, printable
> toothed engagement keyed to the shaft diameter and tooth count — **not** a
> precision DIN 5480 flank form. It is dimensionally real (correct pitch bore and
> tooth count) and mates a matching printed or 3D-modelled shaft; for a metal
> DIN 5480 shaft, treat the fit as a slip coupling and rely on the key/hex parts
> where a true standard flank is required.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bore | `bore_type` | `keyway` | Keyway / involute spline / hex (forced per part). |
| Bore | `shaft_dia` | 8.0 mm | Bore diameter (keyway/spline) or across-flats (hex). |
| Bore | `clearance` | 0.2 mm | Added to the bore for a printable slip fit. |
| Bore | `spline_teeth` | 6 | Involute-spline tooth count (4–24). |
| Bore | `key_width` | 3.0 mm | Keyway slot width. |
| Bore | `key_depth` | 1.8 mm | Keyway slot depth past the bore. |
| Hub Body | `hub_od` | 0 (auto) | Outer Ø; 0 auto-sizes to 2.2× shaft + 4 mm. |
| Hub Body | `length` | 16.0 mm | Axial hub length (more = more grip). |
| Mounting Flange | `flange` | off | Add an outer flange with a bolt-hole circle. |
| Mounting Flange | `flange_bolts` | 4 | Number of bolt holes. |
| Mounting Flange | `flange_bolt_dia` | 4.5 mm | Bolt-hole diameter. |

## Presets

- **Keyed Hub 8 mm Shaft** — a keyway hub for a standard 8 mm keyed shaft.
- **Spline Coupler 12-tooth** — a 12-tooth spline coupler with a mounting flange.
- **Hex Hub 6 mm** — a 6 mm hex bore for hex shafts / drivers.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Torque Spline / Keyway** (`socket`, DIN 5480 (spline) / keyway) — the shaft
    coupling, defined by `bore_type`, `shaft_dia`, `spline_teeth`, `key_width`,
    `key_depth`, `clearance`. Any hub at the same shaft size + bore type couples
    to the same shaft.
  - **Flange Bolt Circle** (`bolt_pattern`, internal) — `flange`, `flange_bolts`,
    `flange_bolt_dia`.
- **Material awareness:** the fit clearance is exposed (`clearance`) so the bore
  tunes per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a keyed or splined hub is how printed pulleys, arms, gears,
  and knobs actually transmit torque from a motor without slipping — adapting any
  printed part to any shaft without machined metal couplers.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Each bore is cut with a solid that overshoots both hub faces (and is re-cut
  through the flange when present); every shipped preset, part, and extreme renders
  **watertight**.
