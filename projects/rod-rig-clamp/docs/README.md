# 15mm Rod Rig Clamp

The backbone of a cinema camera rig, generated with **CadQuery** (B-Rep): the
**15 mm LWS** (Lightweight Support) rod clamp. Rails run on 15 mm rods spaced
**60 mm** centre-to-centre; matte boxes, follow-focus, monitors and cages all
clamp to them. Build a single clamp, a dual-rod bridge, or a riser.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Rod Clamp** | `single_clamp` | One 15 mm rod bore with a pinch slit + bolt, and an accessory face carrying a 1/4-20 hole. |
| **Dual Rod Bridge (60mm)** | `dual_rod_bridge` | Two rod clamps joined by a spine at the 60 mm LWS spacing, with a central 1/4-20 face — rides both rails at once. |
| **Riser Clamp** | `riser_clamp` | A single clamp with a tall riser column lifting a 1/4-20 face above the rod plane, for a monitor or EVF. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| 15mm Rod | `rod_d` | 15.0 mm | Rod bore diameter (LWS standard). |
| 15mm Rod | `rod_clear` | 0.3 mm | Per-side sliding-fit clearance over the rod. |
| 15mm Rod | `rod_spacing` | 60.0 mm | Centre-to-centre spacing (`dual_rod_bridge`). |
| Clamp Body | `body_th` | 20.0 mm | Clamp length along the rod (Y). |
| Clamp Body | `wall` | 6.0 mm | Material around the bore. |
| Clamp Body | `clamp_bolt_d` | 5.2 mm | Pinch-bolt clearance (M5). |
| Clamp Body | `slit_w` | 2.0 mm | Flex-slit width. |
| Accessory Face | `face_th` | 6.0 mm | Accessory face thickness. |
| Accessory Face | `face_hole_d` | 6.6 mm | 1/4-20 accessory hole. |
| Riser | `riser_h` | 30.0 mm | Riser column height (`riser_clamp`). |

## How the clamp grips

Each clamp block has a **through-bore** along the rod axis (open at both ends,
so it slides onto a rod and the cavity always vents to outside). A thin **pinch
slit** runs from the block top down past the bore centre, splitting it into two
jaws; a **pinch bolt** crosses the slit above the bore. Tightening the bolt
closes the slit and squeezes the jaws onto the rod. The dual bridge places two
such clamps at `rod_spacing` and fuses them with an overlapping spine into a
single solid.

## Presets

- **Monitor Rod Clamp** — a single 15 mm clamp for a monitor arm.
- **LWS Baseplate Bridge (60mm)** — the standard two-rod bridge at 60 mm.
- **EVF Riser** — a 40 mm riser to lift a viewfinder over the rails.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **15mm LWS Rod** (`socket`, *15mm LWS rod*) — the rod bore and spacing,
    defined by `rod_d`, `rod_clear`, `rod_spacing`. Any clamp built for a 15 mm
    rod at 60 mm spacing interoperates with the entire LWS accessory ecosystem.
  - **1/4-20 Accessory Hole** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the
    accessory face hole, defined by `face_hole_d`, for the camera-accessory
    thread.
- **Material awareness:** `tolerance_by_material` is declared — `rod_clear` and
  bore diameter are exposed so the clamp fit tunes per material/printer.
- **Societal benefit:** the 15 mm LWS rod system is the open backbone of
  professional and indie filmmaking; on-demand clamps, bridges and risers let a
  filmmaker build the exact rig they need from stock rod and printed parts, and
  repair a cracked clamp on location.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The rod bore is a through-hole and the pinch slit/bolt are through-cuts, so
  no trapped voids form. Accessory 1/4-20 pockets are drilled from above the top
  face (vented). Fillets are applied to clean blanks before feature cuts and
  wrapped in try/except. All shipped modes and presets render **watertight** in
  well under 20 s.
