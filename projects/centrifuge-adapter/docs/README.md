# Centrifuge Tube Adapter

Step-down sleeves that let a centrifuge rotor bored for one tube size carry a
smaller tube, generated with **CadQuery** (B-Rep). The outer diameter matches
the rotor bore; the inner bore matches the tube (Falcon **15 mL ≈ 17 mm**,
**50 mL ≈ 29 mm**) with a conical seat so the tapered bottom is fully supported
for balanced spinning.

> **Printable lab _aid_ for personal / educational use, not a certified medical
> device.** Sleeves are axisymmetric so they spin balanced, but always verify
> balance and the rotor's rated speed before use, and print in a tough material.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **15 mL Adapter** | `adapter_15` | Rotor bore stepped down to a 15 mL Falcon tube (conical seat). |
| **50 mL Adapter** | `adapter_50` | A large rotor bore stepped down to a 50 mL Falcon tube. |
| **Microtube Adapter** | `microtube_adapter` | A 15 mL bore stepped down to a 1.5 mL microtube (rounded seat). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rotor Fit | `rotor_bore` | 30.0 mm | Diameter of the rotor pocket the sleeve drops into. |
| Rotor Fit | `clearance` | 0.4 mm | Per-side gap on both rotor fit and tube bore. |
| Sleeve Body | `wall_min` | 2.5 mm | Minimum wall around the tube bore. |
| Sleeve Body | `depth` | 70.0 mm | Tube seating length. |
| Sleeve Body | `floor` | 3.0 mm | Closed bottom carrying the tube tip. |

## Presets

- **50 mL Rotor → 15 mL Tube** — the most common step-down.
- **Large Rotor → 50 mL Tube**.
- **15 mL Rotor → 1.5 mL Microtube**.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Rotor Tube Adapter** (`socket`, `15/50mL Falcon`) — the rotor-to-tube
    step-down, defined by `rotor_bore`, `clearance`, `wall_min`, `depth`. The
    inner bores use the Falcon 15 mL / 50 mL nominal diameters.
- **Material awareness:** `tolerance_by_material` is declared — fit tunes to the
  print material; a tougher material is advised for g-force loading.
- **Societal benefit:** lets one shared rotor serve many protocols at near-zero
  cost instead of buying size-specific adapters.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
