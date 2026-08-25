# Cold-Shoe Extension Bar

Multiplies a camera's single accessory shoe into several, generated with
**CadQuery** (B-Rep). The **ISO 518** accessory shoe — the ~18.7 mm-wide rail
with rounded-corner flanges that every on-camera light, microphone, monitor and
flash slides onto — is the standard. This bar carries **three** male shoe feet
plus 1/4-20 holes, so a rig can host a light, a mic and a monitor at once. Every
foot is the real ISO 518 shoe, so it mates any accessory-shoe socket.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Triple Shoe Bar** | `triple_shoe_bar` | A bar with three male shoe feet along its length plus 1/4-20 holes between them — rig three accessories onto one camera shoe or handle. |
| **Shoe Relocator** | `shoe_relocator` | A short bar with a male foot on one end and a female shoe socket on the other — moves a shoe to a more convenient spot. |
| **Shoe + 1/4-20 Rail** | `shoe_quarter_rail` | One male shoe foot on a rail with a row of 1/4-20 holes — mix a shoe with screw-mounted accessories. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| ISO 518 Shoe | `foot_width` | 18.7 mm | ISO 518 accessory-shoe outer width. |
| ISO 518 Shoe | `channel_w` | 14.9 mm | Recessed centre tongue width. |
| ISO 518 Shoe | `flange_th` | 1.6 mm | Flange lip thickness a socket grips. |
| ISO 518 Shoe | `shoe_len` | 20.0 mm | Length of each shoe foot. |
| ISO 518 Shoe | `corner_r` | 1.0 mm | Rounded outer flange corner radius. |
| Bar & Base | `base_th` | 5.0 mm | Bar / base slab thickness. |
| Bar & Base | `base_pad` | 5.0 mm | Bar overhang around each shoe foot. |
| Bar & Base | `quarter_d` | 6.6 mm | 1/4-20 clearance hole diameter. |
| Bar & Base | `bar_span` | 110.0 mm | Overall bar length. |
| Socket Fit | `wall` / `clearance` | 3.0 / 0.35 mm | Socket lip wall and per-side fit slop (`shoe_relocator`). |

## The shoe (why it slides and holds)

Each foot is the ISO 518 cross-section: a full-width flange plate (`foot_width`)
with a raised central tongue (`channel_w`), the outer corners rounded (`corner_r`)
in the 2D profile before extrusion — that rounding is what a socket's radiused
lips capture. Feet, sockets and the bar are all extruded 2D sections and
axis-aligned boxes that **overlap into shared material** (no tangent kisses), so
each part is one watertight body. The relocator's socket channel is a through-cut
that vents both Y ends; 1/4-20 holes are through / open pockets that vent to
outside. Feet are centred on the bar so they seat with real overlap even at the
smallest sizes.

## Presets

- **Standard Triple Bar** — three ISO 518 feet at spec dimensions.
- **Shoe Relocator** — a foot-to-socket extender.
- **Shoe + Screw Rail** — one shoe plus a 1/4-20 hole row.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **ISO 518 Accessory Shoe** (`rail`, *ISO 518*) — the shoe foot, defined by
    `foot_width`, `channel_w`, `flange_th`, `corner_r`. **Mates:**
    [`shoe-mount`](../../shoe-mount/) (its socket and dual bar receive these feet).
  - **1/4-20 Accessory Holes** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the
    mounting holes, defined by `quarter_d`. **Mates:**
    [`shoe-mount`](../../shoe-mount/) (shared 1/4-20 accessory thread).
- **Material awareness:** `tolerance_by_material` is declared — the socket fit
  clearance is exposed so the slide fit tunes per material/printer.
- **Societal benefit:** a camera has one accessory shoe, but a working rig needs a
  light, a mic and a monitor at once. A printable shoe bar that carries three ISO
  518 feet lets an owner-operator fan out a single shoe into the exact layout a
  shoot needs. Sharing the ISO 518 shoe, it grows the shoe family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Feet are extruded 2D shoe sections (rounded corners in the profile); the socket
  channel is a through-cut (vented); 1/4-20 holes vent to outside; feet are
  centred on the bar with real overlap. All shipped modes and extreme-parameter
  cases render **watertight**, single-body, in well under 20 s.
