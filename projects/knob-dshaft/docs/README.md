# D-Shaft Replacement Knob

A right-to-repair **replacement knob** generated with **CadQuery** (B-Rep). When
a proprietary knob snaps off a drawer, cabinet, appliance, or dial, measure the
broken shaft and print a knob whose bore matches it — no part number required.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Knob** | `knob` | The plain replacement knob. |
| **Pointer Knob** | `pointer_knob` | Adds a raised indicator line up the side and across the top so it reads as a dial pointer. |

## Bore types

| `bore_type` | Geometry | Use |
| :--- | :--- | :--- |
| `round` | Plain circular bore | Smooth / press-fit shafts. |
| `D-flat` | Circle with **one** flat chord | The classic appliance / potentiometer D-shaft. |
| `double-D` | Circle with **two** opposing flats | Shafts flatted on both sides. |
| `splined` | A ring of 20 teeth (tip Ø = `shaft_dia`) | Serrated / knurled insert posts. |

The bore is cut with a `0.2 mm` print clearance so it slips onto the shaft, and
the D-flat is modelled correctly as a circle with a chord cut `flat_depth` in
from the wall (verified: bore stays full-radius on three sides, flat on one).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Knob Body | `knob_dia` / `knob_height` | 30 / 18 mm | Outer size. |
| Knob Body | `style` | `cylindrical` | `cylindrical`, `knurled`, or `fluted` grip. |
| Knob Body | `top_round` | on | Dome the top edge. |
| Shaft Bore | `bore_type` | `D-flat` | See table above. |
| Shaft Bore | `shaft_dia` | 6.0 mm | Measured round part of the shaft. |
| Shaft Bore | `flat_depth` | 0.5 mm | Chord depth for D-flat / double-D. |
| Shaft Bore | `bore_depth` | 14.0 mm | Socket depth (auto-clamped to keep a closed cap). |
| Set-Screw | `setscrew` | off | Radial locking hole into the bore. |
| Set-Screw | `setscrew_dia` | 3.2 mm | Clearance hole (≈ M3). |

## Presets

- **Cabinet Knob (round)** — knurled 32 mm, 4 mm round shaft, set-screw.
- **Appliance D-Shaft 6 mm** — fluted, single D-flat, the common 6 mm shaft.
- **Dial Pointer (double-D)** — pointer knob on a double-D shaft.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **D-Shaft Bore** (`socket`, internal (D-shaft / spline)) — the shaft
    interface, defined by `bore_type`, `shaft_dia`, `flat_depth`, `bore_depth`,
    and `setscrew`. Any knob generated with the same bore type + shaft diameter
    mates with the same shaft, so one measured shaft drives a whole family of
    knob bodies.
- **Material awareness:** the `0.2 mm` bore clearance is applied so the fit can
  be tuned per material and printer; `tolerance_by_material` is declared (a
  softer filament may want a tighter nominal for the same grip).
- **Societal benefit:** restores a whole appliance, cabinet, or dial for pennies
  when a proprietary knob snaps and the manufacturer no longer sells it — the
  archetypal right-to-repair part, sized to a shaft the user measures rather than
  a part number they cannot find.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The body is a solid barrel; the bore, set-screw, and flutes are cut with
  cutters that overshoot the faces, and the pointer / knurl are unioned features —
  so all four bore types, all three styles, both modes, and the parameter extremes
  render **watertight**.
