# GoPro Ball-Head Mount

An angle-adjustable base for the **GoPro**-style action-cam mount, generated with
**CadQuery** (B-Rep). A ball-and-socket lets the camera tilt to any angle, then a
pinch bolt locks it. The ball stud carries a GoPro finger bank so it seats into a
GoPro accessory; the socket clamp grips the ball and carries its own GoPro
fingers, so a whole articulating mount drops into any GoPro ecosystem.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ball Stud** | `ball_stud` | A ball on a stem on a puck with GoPro 3-prong fingers underneath — insert the ball into a socket clamp, the fingers into a GoPro accessory. |
| **Socket Clamp** | `socket_clamp` | A cup with a ball cavity, a compression slit and a cross pinch bolt, GoPro 2-prong fingers underneath — grips a ball stud and locks it at any angle. |
| **Ball → 1/4-20** | `ball_to_quarter` | A ball stud on a puck with a 1/4-20 socket bored into the underside — screws a ball onto any tripod. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ball & Socket | `ball_d` | 12.0 mm | Ball diameter; the socket cavity matches it plus clearance. |
| Ball & Socket | `stem_d` | 6.0 mm | Neck diameter between ball and puck. |
| Ball & Socket | `wall` | 4.0 mm | Socket cup / puck wall thickness. |
| Ball & Socket | `grip_clear` | 0.4 mm | Per-side ball↔socket clearance. |
| GoPro Fingers | `finger_thick` / `finger_gap` | 3.0 / 3.2 mm | GoPro finger thickness and mating gap. |
| GoPro Fingers | `knuckle_d` / `bolt_hole_d` | 15.0 / 5.0 mm | Knuckle diameter and M5 axle hole. |
| GoPro Fingers | `reach` | 10.0 mm | Knuckle pivot height below the puck. |
| 1/4-20 Socket | `quarter20_d` / `quarter20_depth` | 5.5 / 8.0 mm | 1/4-20 socket diameter and depth. |

## The watertight ball joint

A naive sphere is a trap: CadQuery's `.sphere()` tessellates to a pole apex that
leaves open edges, so trimesh reports it non-watertight. Here the ball is a
**truncated sphere** built by revolving a **true circular arc** (`threePointArc`)
around a straight axis segment, leaving small flat discs at both poles — no apex
singularity, so every ball is a single watertight solid. The socket cavity is the
same truncated ball subtracted from the cup and opened to the top by a
cylindrical mouth (vents to outside); the compression slit and pinch bolt are
through-cuts. The GoPro fingers' shafts overlap into the puck with real material.

## Presets

- **Standard Ball Stud** — a 12 mm ball with 3-prong GoPro fingers.
- **Pinch-Lock Socket** — the matching socket clamp with slit and bolt.
- **Tripod 1/4-20 Ball** — a ball on a 1/4-20 base for any tripod.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **GoPro Finger Clevis** (`snap`, *GoPro action-cam mount*) — defined by
    `finger_thick`, `finger_gap`, `knuckle_d`, `bolt_hole_d`. **Mates:**
    [`gopro-mount`](../../gopro-mount/) (its finger banks interleave with this
    mount's fingers).
  - **Ball & Socket Detent** (`socket`, *internal*) — the ball and its matching
    cavity, defined by `ball_d`, `grip_clear`, `wall` (the ball stud and socket
    clamp in this cartridge mate each other).
  - **1/4-20 Tripod Socket** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — defined by
    `quarter20_d`, `quarter20_depth`, for the tripod screw.
- **Material awareness:** `tolerance_by_material` is declared — the socket
  clearance and finger gap are exposed so both fits tune per material/printer.
- **Societal benefit:** action cameras mount rigidly by default; adding a tilt
  axis usually means a proprietary ball head. A printable ball-and-socket that
  speaks the GoPro finger language gives the `gopro-mount` family an
  angle-adjustable companion.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The ball is a flat-poled truncated-sphere arc-revolve; the socket cavity is
  opened to a face; slit/bolt/1-4-20 are through-cuts (vented); fingers overlap
  into the puck. All shipped modes and extreme-parameter cases render
  **watertight**, single-body, in well under 30 s.
