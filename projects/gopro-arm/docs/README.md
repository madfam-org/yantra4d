# GoPro Extension Arm

An **extension arm** for the **GoPro**-style action-cam mount, generated with
**CadQuery** (B-Rep). A finger clevis on each end of a connecting bar lets you
extend, offset or couple mounts: one end is a 2-prong (female) bank, the other a
3-prong (male) bank facing the opposite way, so the arm passes a mount through
while adding reach. Every finger set is the real GoPro clevis, so it mates any
GoPro mount, base or accessory.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Straight Arm** | `straight_arm` | 2-prong (up) at one end, 3-prong (down) at the other — a plain pass-through extension. |
| **Male-to-Male Coupler** | `coupler` | 2-prong up + 2-prong down on a short bar — couples two male (3-prong) mounts back-to-back. |
| **Long Lightened Arm** | `long_arm` | A long straight arm with two round lightening holes through the bar (vented) — extra reach at lower mass. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| GoPro Fingers | `finger_thick` | 3.0 mm | GoPro finger thickness (standard ~3 mm). |
| GoPro Fingers | `finger_gap` | 3.2 mm | Gap between fingers; a mating finger nests here. |
| GoPro Fingers | `knuckle_d` | 15.0 mm | Knuckle diameter (standard ~15 mm). |
| GoPro Fingers | `bolt_hole_d` | 5.0 mm | M5 thumbscrew axle through-hole. |
| GoPro Fingers | `reach` | 12.0 mm | Knuckle pivot height above the bar face. |
| Arm | `arm_len` | 60.0 mm | Connecting-bar length between the banks. |
| Arm | `arm_th` | 6.0 mm | Bar thickness. |

## How the clevis chains

Each finger set is the GoPro clevis: fingers of thickness `finger_thick` on a
pitch of `finger_thick + finger_gap` (~6.2 mm) so a mating prong's finger drops
into each gap, then an M5 thumbscrew runs through the aligned `bolt_hole_d`
knuckle holes. The far-end bank is rotated 180° about X so its knuckles point the
other way; both banks' shafts overlap into the connecting bar with real material,
so the whole arm is one watertight body. Axle holes and the long arm's lightening
holes are through-cuts that vent to outside — no trapped voids.

## Presets

- **Standard Extension Arm** — 60 mm reach, 2↔3 pass-through.
- **Male-to-Male Coupler** — a short link joining two female mounts.
- **Long Reach Arm** — 120 mm lightened arm for maximum offset.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **GoPro Finger Clevis** (`snap`, *GoPro action-cam mount*) — defined by
    `finger_thick`, `finger_gap`, `knuckle_d`, `bolt_hole_d`. **Mates:**
    [`gopro-mount`](../../gopro-mount/) (its 2-prong / 3-prong banks interleave
    with each end of this arm).
- **Material awareness:** `tolerance_by_material` is declared — the finger gap is
  exposed so the interleave fit tunes per material/printer.
- **Societal benefit:** the GoPro finger mount is the open lingua franca of
  action-cam accessories, but off-the-shelf arms come in fixed lengths. Printing
  an arm to the exact reach a rig needs — and a coupler to join two mounts —
  means building a custom camera rig from printed links. It gives the one-member
  `gopro-mount` family a companion.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Fingers are knuckle-cylinder + shaft-box unions overlapping into the bar; the
  far bank is rotated 180° about X; axle and lightening holes are through-cuts
  (vented). All shipped modes and extreme-parameter cases render **watertight**,
  single-body, in well under 30 s.
