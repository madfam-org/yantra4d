# 15mm Rod Bridge Plate

A **bridge** that spans two **15 mm LWS** cinema rods at the **60 mm** standard
spacing and carries an accessory platform across them, generated with **CadQuery**
(B-Rep). Rails on 15 mm rods spaced 60 mm centre-to-centre are the backbone of a
camera rig; this bridge clamps both rails at once and gives a flat 1/4-20 cheese
plate, a raised riser plate, or a vertical accessory face. Every rod socket is
the real 15 mm LWS bore, so it shares rails with any 15 mm rod clamp.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cheese Plate Bridge** | `bridge_plate` | Dual rod clamps spanned by a wide flat cheese plate with a 6-hole 1/4-20 grid — a baseplate that rides both rails. |
| **Riser Bridge** | `riser_bridge` | Dual rod clamps + two riser columns lifting a top plate above the rails — raises a plate or monitor over the rail plane. |
| **Angle Face Bridge** | `angle_bridge` | Dual rod clamps + a vertical face plate on one side with 1/4-20 holes — mount a monitor or accessory upright. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| 15 mm Rods | `rod_d` | 15.0 mm | Rod diameter (LWS cinema standard). |
| 15 mm Rods | `rod_clear` | 0.3 mm | Per-side bore clearance for a sliding fit. |
| 15 mm Rods | `rod_spacing` | 60.0 mm | Centre-to-centre rod spacing (LWS standard). |
| Clamp | `body_th` | 20.0 mm | Clamp block length along the rod. |
| Clamp | `wall` | 6.0 mm | Material around the rod bore. |
| Clamp | `clamp_bolt_d` / `slit_w` | 5.2 / 2.0 mm | Pinch bolt hole and flex slit width. |
| Platform | `plate_th` | 6.0 mm | Cheese / top / face plate thickness. |
| Platform | `face_hole_d` | 6.6 mm | 1/4-20 accessory hole diameter. |
| Platform | `riser_h` | 30.0 mm | Riser height (`riser_bridge`). |
| Platform | `face_h` | 50.0 mm | Vertical face height (`angle_bridge`). |

## How the bridge holds

Each rod clamp is a block with a **through-bore** along Y (the rod slides through,
so the cavity vents to outside) at the LWS `rod_spacing`. A pinch slit from the
top reaches into the bore and a cross bolt squeezes the jaws to lock the rod.
The spanning plate, riser columns and vertical face all overlap into the clamp
blocks with real material, so the whole bridge is one watertight body. Flat-plate
1/4-20 holes are open pockets drilled from above that leave a floor and nick
through the top face (vented); the angle face's holes are through-holes.

## Presets

- **Standard Cheese Bridge (60mm)** — a flat baseplate at the LWS spacing.
- **Monitor Riser** — a 40 mm riser to lift a monitor over the rails.
- **Upright Accessory Face** — a vertical face for a side-mounted accessory.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **15 mm LWS Rod Socket** (`socket`, *15mm LWS rod*) — the twin rod bores at
    the 60 mm spacing, defined by `rod_d`, `rod_clear`, `rod_spacing`. **Mates:**
    [`rod-rig-clamp`](../../rod-rig-clamp/) (shares the same 15 mm rails).
  - **1/4-20 Accessory Holes** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the
    accessory holes, defined by `face_hole_d`. **Mates:**
    [`rod-rig-clamp`](../../rod-rig-clamp/) (shared 1/4-20 accessory thread).
- **Material awareness:** `tolerance_by_material` is declared — the bore
  clearance is exposed so the sliding/clamping fit tunes per material/printer.
- **Societal benefit:** the 15 mm LWS rod system is the open backbone of camera
  rigging, but bridge and top plates are pricey machined parts. A printable rod
  bridge lets an owner-operator build the exact accessory platform a shoot needs.
  Sharing the 15 mm bore, it grows the cinema-rod family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Rod bores are through-holes (vented); pinch slit and bolt are through-cuts;
  the platform overlaps into the clamps with real material; 1/4-20 pockets are
  vented. All shipped modes and extreme-parameter cases render **watertight**,
  single-body, in well under 30 s.
