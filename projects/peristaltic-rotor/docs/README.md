# Peristaltic Pump Rotor

The rotating core of a **peristaltic (roller) pump**, generated with **CadQuery**
(B-Rep). A rotor carries rollers that squeeze a flexible tube against a curved
**race**, pushing fluid along **without the pump ever touching it** — only the
disposable tube contacts the liquid. That is why peristaltic pumps run dialysis,
IV lines, lab reagents, food, and aquaria. Sized for standard **3/16 in
(4.76 mm)** and **1/4 in (6.35 mm)** OD silicone tubing.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rotor** | `rotor` | The roller-carrier disc: a central drive-shaft bore with a **D-flat** and set-screw, plus N roller-pin bores and clearance pockets on a bolt circle. |
| **Tube Race** | `tube_race` | The **semicircular pump race** — a housing block with a toroidal channel that cradles the tube at the squeeze radius, tube entry/exit ports, and M3 corner mounting holes. |
| **Roller** | `roller` | A single chamfered **roller** with a central pin bore — rolls on a rotor pin and pinches the tube. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pump | `tube` | 1/4 in | Tubing OD: `3/16in` (4.76 mm) or `1/4in` (6.35 mm). |
| Rotor & Roller | `rotor_d` | 50 mm | Rotor outer diameter (sets pump size). |
| Rotor & Roller | `n_rollers` | 3 | Roller count (more = smoother flow). |
| Rotor & Roller | `rotor_h` | 16 mm | Rotor / roller height. |
| Rotor & Roller | `shaft_d` | 6.0 mm | Drive-shaft bore (D-flat + set-screw). |
| Rotor & Roller | `roller_d` | 12 mm | Roller outer diameter. |
| Rotor & Roller | `pin_d` | 4.0 mm | Roller pin / axle. |
| Race | `wall` | 4.0 mm | Race housing wall thickness. |

## How it pumps (and how it stays watertight)

The **rotor** is a disc with roller pockets cut around the rim and pin bores
through them; the central shaft bore is a circle with a chord cut off (the
**D-flat**) plus a radial set-screw hole — all boolean cuts, one solid. The
**tube race** cradles the tube in a **toroidal channel** built with `makeTorus`
(a clean filled-torus subtraction, avoiding the revolve-of-a-cut trap), then the
block is halved to a 180° race and the tube **entry/exit ports** are bored
through the side into the channel — so every internal passage vents to a face:
`is_watertight == True`, `body_count == 1`. As the rotor turns, each roller
occludes the tube at the squeeze radius and carries a slug of fluid around the
semicircle.

## Presets

- **Standard 3-Roller Rotor** — a general dosing-pump rotor.
- **1/4 in Tube Race** — the matching race for 1/4 in tubing.
- **Single Roller** — one roller (print `n_rollers` of them).

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Tube Race Channel** (`socket`, *3/16-1/4in tube*) — the toroidal tube
    channel + ports, defined by `tube`, `rotor_d`, `roller_d`, `wall`. Cradles
    standard 3/16 in / 1/4 in OD silicone tubing.
  - **Roller & Shaft Bores** (`socket`, *internal*) — the drive-shaft and roller
    pin bores, defined by `shaft_d`, `pin_d`, `roller_d`.
- **Material awareness:** `tolerance_by_material` is declared — wall and bore
  sizes are exposed so fits tune per material (stiff PLA vs tougher PETG/nylon).
- **Societal benefit:** peristaltic pumps dose fluids without contamination
  because only the disposable tube touches the liquid; an open, parametric rotor
  and race for standard tubing let a lab build a pump to the flow it needs and
  swap the tube instead of the pump.
- **License:** CERN-OHL-W-2.0
- **Family:** new hybrid/fluidics cluster (no existing mate).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. The tube channel is a `makeTorus` subtraction; every
  passage vents to a face (no trapped void).
