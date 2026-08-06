# Ball-Socket / Articulated Arm

A ball-and-socket joint generated with **CadQuery** (B-Rep) for adjustable arms —
phone, mic, camera, and light mounts. A **ball stud** snaps into a **socket cup**
whose opening is slightly smaller than the ball, so friction holds any angle.
Parts chain into arms of any length.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ball Stud** | `joint` | A ball on a stem rising from a base. |
| **Socket Cup** | `joint` | A cup that grips a ball, on a stem/base. Mouth faces up. |
| **Double Ball Link** | `joint` | A ball on both ends of a stem — a link between two sockets. |
| **Arm Segment** | `joint` | A socket on one end, the chosen end on the other — the chainable unit. |

The `end_type` selector sets the far end of the stem: `ball`, `socket`,
`1/4-20` (camera), or `flat_mount` (screw plate).

## How the joint grips

The socket cavity is a sphere of radius `ball_dia/2 + socket_clear`, so the ball
**pivots freely** inside it. The mouth (throat) radius is `ball_dia * socket_grip / 2`;
with `socket_grip < 1` the opening diameter is **smaller than the ball**, so the
ball snaps past the rim and is captured, held by friction at any angle.

At the default (`ball_dia` 16 mm, `socket_grip` 0.85): cavity radius 8.30 mm > ball
radius 8.00 mm (rotates), opening diameter 13.60 mm < ball diameter 16.0 mm (1.20 mm
snap interference). **A Ball Stud mates into a Socket Cup at the same `ball_dia`.**

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ball & Socket | `ball_dia` | 16 mm | Ball diameter; the socket matches it. |
| Ball & Socket | `socket_grip` | 0.85 | Opening as a fraction of ball diameter (< 1 grips). |
| Ball & Socket | `socket_clear` | 0.3 mm | Radial cavity clearance so the ball pivots. |
| Stem & Base | `stem_len` | 30 mm | Stem / arm length. |
| Stem & Base | `stem_dia` | 9 mm | Stem thickness. |
| Stem & Base | `base_dia` | 22 mm | Base plate / cup body diameter. |
| Ends | `end_type` | ball | Far-end feature: ball / socket / 1/4-20 / flat plate. |

## Presets

- **Phone-Mount Ball (16 mm)** — a ball stud for a phone clamp.
- **Matching Socket (16 mm)** — the socket cup that snaps onto it.
- **Gooseneck Link** — a double-ball link for chaining sockets into an arm.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Ball Joint** (`socket`, internal) — the friction ball-and-socket mate,
    defined by `ball_dia`, `socket_grip`, `socket_clear`. Any stud fits any cup
    at the same `ball_dia`; this is the interoperable interface.
  - **1/4-20 Camera Interface** (`thread`, `ASME B1.1 1/4-20 UNC`) — modelled as
    the nominal 5.5 mm clearance bore (`end_type = 1/4-20`) so it mates real
    camera/tripod hardware without a slow printed helix.
- **Material awareness:** clearance and grip are exposed so the snap fit can be
  tuned per material/printer; `tolerance_by_material` is declared (TPU grips
  differently than PLA).
- **Societal benefit:** one friction ball joint replaces a drawer of proprietary
  phone, camera, and light mounts — a broken arm is reprinted, not rebought.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Balls and socket shells are made watertight by piercing each exposed sphere
  pole with a thin **interior** axial rod. OCP's STL tessellation otherwise
  leaves degenerate pole-fan triangles that read as non-watertight; the boolean
  union re-tessellates the pole cleanly. The rod is fully inside the solid and
  never protrudes — a mesh-quality device only. All modes export watertight.
