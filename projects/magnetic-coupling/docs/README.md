# Magnetic Coupling Hub

A **contactless magnetic shaft coupling**, generated with **CadQuery** (B-Rep).
Two hubs each carry a ring of **disc magnets**; placed face to face — or across a
thin non-magnetic barrier — they lock magnetically and transmit torque with **no
physical connection**. So one shaft can drive another **through a sealed wall**
(pumps, stirrers, robots), and the coupling **slips harmlessly on overload**
instead of breaking. It **grows the shaft-spline family**: the shaft bore is a
round or **D-flat 6/8 mm** fit with a set-screw — the same shaft interface as
`knob-dshaft`.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Watertight note.** Every part is a **printable single-body solid**. The disc-
> magnet pockets are **blind bores that open to one face** (the coupling face),
> so they vent to outside — no trapped void, and the whole mesh is watertight.
> Drop in disc magnets and glue.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Coupling Hub** | `coupling_hub` | The driving/driven hub: a disc with a shaft bore (round or D-flat), a radial set-screw, and a ring of N disc-magnet pockets on the coupling face. |
| **Magnet Disc** | `disc_rotor` | A thinner magnet-carrier disc (no boss) for a pancake / axial coupling face or an encoder magnet ring, with a through shaft bore. |
| **Cup Shell** | `cup_shell` | A cup-shaped shell that houses the opposing hub across a wall — the outer half of a sealed (through-barrier) coupling, magnets on the inner floor. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Hub | `hub_d` | 36 mm | Coupling disc outer diameter. |
| Hub | `hub_h` | 16 mm | Hub / shell height. |
| Shaft Bore | `shaft_dia` | 6.0 mm | Shaft bore (6 or 8 mm common). |
| Shaft Bore | `bore_type` | D-flat | `round` or `D-flat` fit (as knob-dshaft). |
| Shaft Bore | `flat_depth` | 0.5 mm | How far the D-flat cuts in. |
| Shaft Bore | `setscrew_dia` | 3.2 mm | Radial M3 set-screw. |
| Magnets | `n_magnets` | 6 | Disc magnets in the ring (alternate N/S). |
| Magnets | `magnet_d` | 8.0 mm | Disc-magnet diameter. |
| Magnets | `magnet_h` | 3.0 mm | Disc-magnet thickness (pocket depth). |

## How it couples (and why it's watertight)

Each hub is a disc with a ring of **blind magnet pockets** on its coupling face
and a **shaft bore** on the opposite face — a round hole, optionally with a
**D-flat** chord milled off and a **radial set-screw** through the rim (exactly
the round/D-flat + set-screw interface the `knob-dshaft` cartridge uses, so the
two share the same shafts). The magnet pockets open to the coupling face, so
there is no enclosed cavity: `is_watertight == True`, `body_count == 1` for every
mode. Two hubs with alternating magnet polarity attract into alignment and carry
torque across the air gap; a **cup shell** lets the driven hub sit in a sealed
recess across a thin wall for leak-free magnetic drive.

## Presets

- **Standard 6 mm Hub** — a general D-flat coupling hub.
- **8 mm Magnet Disc** — a pancake / encoder magnet disc.
- **Through-Wall Cup** — the sealed-barrier outer shell.

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Disc-Magnet Ring** (`socket`, *6/8mm shaft + magnets*) — the disc-magnet
    pocket ring, defined by `n_magnets`, `magnet_d`, `magnet_h`.
  - **Shaft Bore** (`socket`, *internal round / D-flat*) — the shaft fit, defined
    by `shaft_dia`, `bore_type`, `flat_depth`. **Compatible with `knob-dshaft`** —
    both take the same round / D-flat 6/8 mm shaft with a set-screw.
- **Material awareness:** `tolerance_by_material` is declared — bore and pocket
  fits tune per material (stiff PLA vs tougher PETG/nylon).
- **Societal benefit:** magnetic couplings transmit torque with no contact — they
  drive pumps through a sealed wall and slip safely on overload; an open,
  parametric hub on the standard disc-magnet + 6/8 mm shaft grid lets a maker
  build a contactless drive to their exact shaft.
- **License:** CERN-OHL-W-2.0
- **Family:** mates the **shaft-spline** family (`knob-dshaft`).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Magnet pockets open to a face (no trapped void); every
  mode is a single watertight body.
