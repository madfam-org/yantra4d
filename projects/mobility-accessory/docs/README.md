# Wheelchair / Walker Accessory

Accessories that **clamp to the round tube** of a wheelchair, walker, rollator,
or mobility frame and carry the small things a user needs within reach — a cup, a
phone, or a cane/crutch. Generated with **CadQuery** (B-Rep). The shared
interface is a **C-shaped snap clamp** sized to standard mobility tube
(**3/4-1 in / 19-25 mm OD**) that opens on one side to snap over the tube and
pinches shut with a strap or zip tie through its ears.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Fit is user-specific.** Measure your frame's tube diameter (mobility tube is
> commonly 3/4-1 in / 19-25 mm, but varies) and confirm the clamp and load with
> an occupational therapist (OT) — a heavy full cup or a leaning cane changes the
> balance and reach of the chair. Snap the clamp on with a strap or zip tie
> through the ears; do not rely on the snap alone under load. Print a test clamp
> and check the fit and clearance first.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cup Holder** | `cup_holder` | The clamp with a cup ring and a floor (with a drain hole) to hold a drink or can. |
| **Phone Cradle** | `phone_cradle` | The clamp with a slotted phone tray — a floor with a front lip and side lips, open back for a charging cable. |
| **Cane Holder** | `cane_holder` | The clamp with a second C-cradle that a cane or crutch shaft clips into, so it stays upright and reachable. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids (`cup_holder` /
`phone_cradle` / `cane_holder`) match the dispatched values, so every mode
renders its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tube Clamp | `tube_dia` | 25 mm | Frame tube OD (3/4-1 in = 19-25 mm). |
| Tube Clamp | `clamp_wall` | 5 mm | C-clamp wall thickness. |
| Tube Clamp | `clamp_w` | 22 mm | Clamp length along the tube. |
| Tube Clamp | `opening` | 120° | Arc of the C mouth — wider snaps on easier, narrower grips tighter. |
| Tube Clamp | `clearance` | 0.4 mm | Radial fit gap over the tube. |
| Carrier | `cup_dia` | 74 mm | Cup ring inner diameter (a soda can is ~66 mm) (`cup_holder`). |
| Carrier | `cup_h` | 55 mm | Cup ring height (`cup_holder`). |
| Carrier | `tray_w` | 78 mm | Phone tray width (`phone_cradle`). |
| Carrier | `tray_d` | 14 mm | Tray lip height (`phone_cradle`). |
| Carrier | `cane_dia` | 26 mm | Cane / crutch shaft diameter (`cane_holder`). |

## Presets

- **Can / Cup Holder (25mm tube)** — a cup ring on a 25 mm tube clamp.
- **Phone Tray (25mm tube)** — a lipped phone tray on the clamp.
- **Cane / Crutch Cradle** — a second C-ring cradle for a cane shaft.

## The C-clamp (why it stays one solid, and how it holds)

The clamp is a single **extruded annular sector** — a C. Its 2D profile is the
region between an outer arc (`bore_r + clamp_wall`) and the bore arc (`tube_dia/2
+ clearance`), spanning `360 - opening` degrees; extruding that closed region
once yields one manifold body whose mouth vents to outside and whose bore is a
through-passage along the tube axis. Two ears flank the mouth with strap holes, so
a strap or zip tie cinches the C shut on the tube. Carriers (cup ring, tray,
cradle) union onto the clamp back through a solid connector web with overlap, so
the whole accessory is a single watertight solid.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Mobility Tube Clamp** (`socket`, *3/4-1in tube*) — the C-clamp bore that
    grips the frame tube, defined by `tube_dia`, `clamp_wall`, `opening`, and
    `clearance`. Any frame whose tube matches `tube_dia` (within `clearance`)
    accepts the clamp; carriers are interchangeable on the same clamp.
- **Material awareness:** `clearance` and `opening` are exposed so the snap grip
  can be tuned for rigid (PLA/PETG) or springy (PETG/TPU) filament;
  `tolerance_by_material` is declared.
- **Societal benefit:** a clamp-on accessory sized to the frame's tube puts a
  drink, phone, or cane within reach without a costly proprietary bracket, mounts
  tool-free via a strap, and can be reprinted for a different tube, cup, or device.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; `target_part` dispatches the part; the final solid is `result`.
- Every part is one manifold solid. The clamp is a single extruded C-section (the
  tube-clamp guidance): the mouth vents to outside, the bore is a through-passage.
  The cup ring has a drain hole so its pocket is not a sealed cavity; carriers
  union onto the clamp back through a solid overlapping web; the cane cradle is a
  second extruded C-section. All shipped modes and both parameter extremes render
  **watertight**, `body_count == 1`.
