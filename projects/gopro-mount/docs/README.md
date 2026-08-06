# GoPro-Style Mount Fingers

The **de-facto action-cam mounting standard**, generated with **CadQuery**
(B-Rep): the interlocking "finger" clevis. A two-prong (female) and three-prong
(male) joint interleave on a shared finger pitch, then a thumbscrew through the
aligned **5 mm knuckle holes** pivots and clamps them. Pairs with flat
screw/adhesive plates and the ubiquitous **1/4-20** tripod adapter.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **2-Prong (Female)** | `dual` | Two fingers on the outer slots of the 3-slot grid, on a base. The gap slot is left open for a mating centre finger. |
| **3-Prong (Male)** | `triple` | Three fingers filling the grid, on a base. The centre finger nests into a 2-prong's open gap. |
| **Base Plate** | `base_plate` | The 3-prong finger bank on a flat plate with optional corner screw holes — for adhesive or screw mounting. |
| **1/4-20 Tripod Adapter** | `quarter20_adapter` | Prongs (2 or 3, selectable) on a puck carrying a 1/4-20 socket underneath — the standard camera↔tripod adapter. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Finger Clevis | `finger_thick` | 3.0 mm | Single finger thickness (GoPro standard). |
| Finger Clevis | `finger_gap` | 3.2 mm | Gap between fingers; **must be ≥ thickness** so a mating prong interleaves. |
| Finger Clevis | `knuckle_d` | 15.0 mm | Rounded pivot knuckle diameter (~15 mm standard). |
| Finger Clevis | `bolt_hole_d` | 5.0 mm | Axle thumbscrew through-hole (M5). |
| Finger Clevis | `reach` | 18.0 mm | Knuckle-centre height above the base top. |
| Base | `base_thick` / `base_len` | 4.0 / 30.0 mm | Base slab thickness and length (Y). |
| Base | `base_margin` | 4.0 mm | Base overhang beyond the finger span. |
| Mounting Plate | `plate_width` / `plate_len` | 40 / 40 mm | Flat plate footprint (`base_plate` mode). |
| Mounting Plate | `screw_holes` / `screw_hole_d` | on / 4.2 mm | Corner screw holes (M4 clearance). |
| 1/4-20 Adapter | `adapter_prongs` | triple | Which prong set sits on the puck (2 or 3). |
| 1/4-20 Adapter | `quarter20_d` / `quarter20_depth` | 5.5 / 8.0 mm | Plain 1/4-20 socket size and depth. |

## The interleave (why the standard works)

Fingers sit on a shared **pitch = `finger_thick` + `finger_gap`** (default
3.0 + 3.2 = 6.2 mm) grid, symmetric about centre. On a 3-slot grid:

- the **2-prong** fills slots 0 and 2, leaving slot 1 open;
- the **3-prong** fills slots 0, 1, 2.

When mated, the 3-prong's centre finger drops into the 2-prong's open gap, and
its outer fingers straddle the 2-prong's pair. A mating 3.0 mm finger fits the
3.2 mm gap with **0.1 mm per side** of clearance. Aligning the knuckle holes and
running a bolt through completes the pivot. The `finger_gap ≥ finger_thick`
constraint is enforced as an error so an un-mateable joint can't be exported.

## Presets

- **Standard 3-Prong** — the reference male clevis at spec dimensions.
- **Adhesive Pad Mount** — 40×40 plate, no screw holes, for a stick-on pad.
- **Tripod Adapter (3-Prong)** — prongs over a 1/4-20 socket.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **GoPro Finger Clevis** (`snap`, *GoPro action-cam mount*) — the two/three
    finger interlock, defined by `finger_thick`, `finger_gap`, `knuckle_d`,
    `bolt_hole_d`. Any prong built at the same pitch, knuckle and bolt size
    mates with any other, and with the millions of commercial GoPro-pattern
    accessories.
  - **1/4-20 UNC Tripod Thread** (`thread`, *ASME B1.1 1/4-20 UNC*) — the
    adapter's socket, defined by `quarter20_d`, `quarter20_depth`. Modelled as a
    plain nominal-diameter socket (no slow swept helix); tap it or thread-insert
    it for the 1/4-20 screw common to every camera tripod.
- **Material awareness:** `tolerance_by_material` is declared — finger gap and
  socket diameter are exposed so the interleave fit and thread socket can be
  tuned per material/printer.
- **Societal benefit:** the action-cam mount is a planet-spanning interface
  standard; on-demand prongs, plates and 1/4-20 adapters keep gear mountable to
  anything and repair a snapped finger instead of replacing the whole rig.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. `target_part` dispatches which part to build. The final
  solid is assigned to `result`.
- Fillets on bases/plates are clamped and wrapped in try/except with a
  non-fatal fallback. All shipped modes and presets render **watertight** in
  well under 20 s.
