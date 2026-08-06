# Mobility Tube Tip

Printable replacement tips and holders for the round tubes of **canes,
crutches, and walkers**, generated with **CadQuery** (B-Rep). Sized by the
outer tube diameter so the socket press-fits the tube; the ground-contact face
carries a concentric tread for grip.

> **This is a printable mobility _aid_ for personal use, not a certified medical
> device.** Print the socket in a tough material (TPU is ideal for the ground
> tip), verify the fit is snug, and test it under load before relying on it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cane Tip** | `cane_tip` | Closed tip cup: a tube socket capped by a treaded, chamfered ground face. |
| **Quad Foot** | `quad_foot` | A wide four-lobe stability base with the tube socket rising from its centre. |
| **Clip Holder** | `clip_holder` | A C-clip that snaps onto the tube to park it against a wall or table edge. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tube Fit | `tube_dia` | 19.0 mm | Outer diameter of the tube the part fits. |
| Tube Fit | `clearance` | 0.3 mm | Per-side press-fit gap. |
| Body & Tread | `wall` | 3.0 mm | Wall around the tube socket. |
| Body & Tread | `socket_h` | 28.0 mm | Tube seating depth. |
| Body & Tread | `floor` | 5.0 mm | Ground-contact base thickness. |
| Body & Tread | `tread` | 1.2 mm | Depth of concentric grip grooves (0 = smooth). |
| Quad Foot | `foot_dia` | 55.0 mm | Overall diameter of the stability base. |

## Presets

- **Standard 19 mm Cane** — the common walking-cane tube.
- **Walker Leg (25 mm)** — a deeper socket for a walker leg.
- **Stability Quad Foot** — a wide four-lobe base for extra stability.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Tube Tip Socket** (`socket`, internal) — the tube-to-part press-fit,
    defined by `tube_dia`, `clearance`, `wall`, `socket_h`. Any tip, foot, or
    clip generated at the same tube diameter fits the same tube.
- **Material awareness:** press-fit `clearance` is exposed so the socket can be
  tuned per material/printer; `tolerance_by_material` is declared (soft TPU
  needs less clearance than rigid PLA).
- **Societal benefit:** restores a hard-to-source mobility-aid consumable at
  near-zero cost, independent of a single supplier.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
