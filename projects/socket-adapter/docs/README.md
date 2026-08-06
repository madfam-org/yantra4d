# LED Bulb / Socket Adapter

Lamp socket adapters and bulb-base converters generated with **CadQuery**
(B-Rep) around the **real bulb-base standards**. Two families are represented
with their true geometry:

- **Edison screw** (threaded): **E26** (26.05 mm major, 7-TPI Edison → 3.629 mm
  pitch, the North-American medium base) and **E27** (26.4 mm major, same pitch,
  the European medium base) — modelled as **functional helical threads**.
- **Twist-lock (bayonet):** **GU10** (two pins, 10 mm centre span) and **B22 /
  BA22d** (22 mm bayonet, two diametric pins) — modelled with **real pins**.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Safety:** printed adapters are mechanical only — they carry no live current.
> Electrical contact is always made by the mains fixture's own metal contacts.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Screw Shell** | `screw_shell` | A hollow male Edison shell (E26/E27) with a top collar and a central wiring bore — screws into a lamp socket and carries a device up top. |
| **Base Converter** | `base_converter` | Female Edison thread (base **A**) on the bottom + male Edison thread (base **B**) on top: an E26↔E27 translator with a wiring channel. |
| **Bayonet Base** | `bayonet_base` | A GU10 / B22 twist-lock puck: a skirt with two real bayonet pins and a central bore. |

## Base Standards

| Base | Type | Key dims |
| :--- | :--- | :--- |
| **E26** | Edison screw | 26.05 mm major, 3.629 mm pitch (7 TPI) |
| **E27** | Edison screw | 26.4 mm major, 3.629 mm pitch |
| **GU10** | Twist-lock | 26 mm skirt, pins Ø 4.7 mm, 10 mm span |
| **B22** | Bayonet | 22 mm skirt, two diametric pins |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Base Standard | `edison_a` / `edison_b` | E26 / E27 | Bottom / top Edison base. |
| Base Standard | `bayo` | GU10 | Twist-lock standard (bayonet base). |
| Thread & Walls | `clearance` | 0.4 mm | Per-side printed-thread gap. |
| Thread & Walls | `wall` | 2.4 mm | Shell / skirt wall thickness. |
| Thread & Walls | `turns` | 3.0 | Engagement; snapped to a half-integer, capped at 3.5. |
| Body & Bore | `bore` | 12 mm | Central wire / device bore. |
| Body & Bore | `height` | 22 mm | Bayonet puck body height. |

## Presets

- **E26 Screw Shell** — a male E26 shell with a device collar.
- **E26 → E27 Converter** — fit a US bulb into an EU lamp (or vice-versa).
- **GU10 Twist-Lock Base** — a GU10 bayonet puck.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Edison Screw Thread** (`thread`, *IEC 60061 E26 / E27, 7 TPI*) — the
    functional screw base (`edison_a`, `edison_b`, `clearance`, `turns`).
  - **Bayonet Twist-Lock** (`snap`, *GU10 / IEC 60061 B22d*) — the twist-lock
    pins (`bayo`, `wall`).
  - **Central Bore** (`socket`, *internal*) — the wiring / device bore (`bore`).
- **Material awareness:** the printed-thread fit is exposed as `clearance`;
  `tolerance_by_material` is declared.
- **Societal benefit:** bulb bases fragment the world into incompatible fixtures;
  a printed shell / converter / bayonet base bridges the base you have to the
  fixture you own, keeping working bulbs and lamps in service.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Edison threads are real helical ribs** (`makeHelix` + swept trapezoid, root
  pushed into the wall for a watertight volumetric union). The engagement is
  snapped to a **half-integer** turn count (`floor(turns)+0.5`, clamped 1.5–3.5):
  an integer count degenerates the OCCT helical sweep to a negative-volume body.
- **Bayonet pins** are solid cylinders placed with explicit direction vectors and
  fused into the skirt (no fragile sweep). The central bore opens through both
  ends. All three modes and the MIN/MAX extremes render watertight, one body.
