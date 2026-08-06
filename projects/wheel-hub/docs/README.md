# Robot Wheel / Hub

A **robot drive wheel or hub** with a **shaft bore matched to a real motor
shaft**, generated with **CadQuery** (B-Rep). The bore keys the wheel to the shaft
so it actually drives — a D-flat for D-shafts, a round bore plus a radial
set-screw for round shafts, or a hex bore for the TT gearmotor.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Shaft table

| Shaft | Bore style | Keying |
| :--- | :--- | :--- |
| 3 mm D-shaft | round + one flat | D-flat |
| 4 mm D-shaft | round + one flat | D-flat |
| 6 mm round | round bore | radial set-screw |
| TT gearmotor | hex bore | hex flats |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Drive Wheel** | `wheel` | A rim built as stacked cylinders so a narrower mid-band forms a tyre groove between two flanges, with lightening holes and the keyed bore. |
| **Hub Adapter** | `hub_adapter` | A keyed boss on the shaft side and a flat flange with a ring of bolt holes to carry a wheel, disc or arm. |
| **Pulley Wheel** | `pulley_wheel` | A flanged pulley whose mid-section tapers in to a groove root and back out (a V-groove for cord / round belt), with the same keyed bore. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shaft | `shaft` | 3mm-D | `3mm-D`, `4mm-D`, `6mm-round`, `hex-TT-motor`. |
| Shaft | `bore_clear` | 0.2 mm | Bore clearance over the shaft (fit). |
| Shaft | `set_d` | 3.0 mm | Radial set-screw (round shaft). |
| Wheel | `wheel_d` / `wheel_w` | 60 / 12 mm | Outer diameter and width. |
| Wheel | `groove_d` | 3.0 mm | Tyre / belt groove depth (radial). |
| Wheel | `hub_d` | 16 mm | Central hub diameter around the bore. |
| Adapter | `bolt_circle` / `bolt_d` / `bolt_n` | 24 mm / 3.4 mm / 4 | Output bolt circle. |

## The shaft bore (why it drives)

A wheel only drives if it can't spin on the shaft. Each shaft standard is keyed
differently, so the bore is the negative of the real shaft: **D-shafts** get a
round bore with a chord flat (the flat transmits torque); **round shafts** get a
plain bore plus a radial **set-screw** that clamps onto the shaft; the **TT
gearmotor** double-flat shaft is driven by a **hex** bore adapter. `bore_clear`
tunes the press-to-slip fit per printer. The wheel's tyre groove and the pulley's
V-groove are built from **stacked cylinders / tapered frusta** (not boolean
groove-cuts), so every mode is watertight by construction.

## Presets

- **TT Motor Wheel** — hex-bore drive wheel for a TT gearmotor.
- **3 mm D Hub** — shaft-to-bolt-circle adapter for a 3 mm D-shaft.
- **6 mm Cord Pulley** — round-shaft pulley with a deep cord groove.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Motor Shaft Bore** (`socket`, *3/4/6mm / TT hex*) — the keyed bore, defined
    by `shaft`, `bore_clear`, `set_d`. Keys onto the motor's output shaft.
  - **Output Bolt Circle** (`bolt_pattern`, *internal*) — the adapter's output
    holes, defined by `bolt_circle`, `bolt_d`, `bolt_n`.
- **Material awareness:** `tolerance_by_material` is declared — the bore clearance
  can be tuned per material.
- **Societal benefit:** a printed wheel or hub keyed to the exact shaft turns any
  of a handful of common motors into drive without buying a matching wheel.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. All modes render **watertight**.
