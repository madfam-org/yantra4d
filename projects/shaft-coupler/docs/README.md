# Universal / D-Shaft Coupler

A parametric shaft coupler generated with **CadQuery** (B-Rep) that joins two
shafts end-to-end. Each end has its own bore — a round hole or a D-flat for a
flatted shaft — and is locked by radial set screws or a pinch clamp.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Bore geometry

- **Round** — a plain circular bore of the given diameter plus a small print
  clearance.
- **D-Flat** — a circle with ONE flat chord cut `flat_depth` in from the wall,
  matching a shaft with a machined flat (the classic motor / potentiometer
  D-shaft), built as a circle-minus-chord.

In **rigid** and **flexible** modes both bores match Bore A; in **stepped** mode
Bore B is independent (a reducing coupler).

## Locking & flex

- **Set Screws** — one radial grub-screw hole into each bore, near each end.
- **Pinch Clamp** — an axial slit through the wall into each bore plus a cross
  bolt to squeeze the ears. The slit is a thin slab so the part stays watertight.
- **Flexible Section** — a band of interleaved beam slots in the middle,
  alternating side to leave a central spine, evoking a helical flex coupler while
  remaining a single watertight solid.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rigid** | `rigid` | Solid coupler, both bores equal. |
| **Flexible** | `flexible` | Adds the interleaved beam-slot flex section. |
| **Stepped / Reducing** | `stepped` | Two different bore diameters. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bore A | `bore_a` / `bore_a_type` | 6.35 mm / round | Shaft A diameter and hole type. |
| Bore B | `bore_b` / `bore_b_type` | 5 mm / round | Shaft B (stepped mode only). |
| Body | `outer_dia` / `length` | 19 / 25 mm | Coupler body. |
| Body | `flat_depth` | 0.5 mm | D-flat cut depth. |
| Locking & Flex | `clamp_style` / `setscrew_dia` | setscrew / 3.2 mm | Set screws or pinch clamp. |
| Locking & Flex | `flexible` | off | Interleaved beam-slot flex section. |

## Presets

- **Rigid 1/4" (6.35 mm)** — a rigid coupler for a 1/4" shaft.
- **Flexible 5 mm D-Shaft** — a flexible coupler for a 5 mm D-shaft motor.
- **Reducing 8 → 5 mm** — a clamp-style reducing coupler.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Shaft Bore (A & B)** (`socket`, internal) — the shaft interface, defined by
    `bore_a`, `bore_a_type`, `bore_b`, `bore_b_type`, `flat_depth`.
  - **Set-Screw / Clamp Locking** (`custom`, internal) — `clamp_style`,
    `setscrew_dia`.
- **Material awareness:** `tolerance_by_material` is declared; each bore carries a
  small print clearance for a tuned slip fit.
- **Societal benefit:** a printable coupler with the exact two bore sizes lets a
  maker join mismatched shafts or add a flexible link without sourcing a specific
  metal part.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
