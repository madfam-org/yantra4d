# Net Cup / Hydroponic Collar

A tapered mesh net cup for hydroponics, generated with **CadQuery** (B-Rep):
its wide rim lip rests on a hole in a lid, bucket or PVC pipe, and slots in the
tapered wall pass roots and water while retaining clay pebbles or rockwool.
Sized by the 2" (50 mm rim) and 3" (85 mm rim) net-cup standards.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in **food-safe, opaque filament** (uncoloured PETG is a common choice)
> so light does not reach the reservoir and feed algae.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Net Cup** | `net_cup` | The full tapered mesh basket — conical wall + rim lip, open draining base, staggered mesh slots. |
| **Seating Collar** | `collar` | A short tapered collar that seats a rockwool cube or bare plug in a lid hole, with one band of slots. |
| **Lid Grommet** | `lid_grommet` | A plain tapered eyelet (no mesh) that lines a drilled lid hole so a smooth cup or tube seats without chafing. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cup Body | `top_od` | 44.0 mm | Body outer diameter at the rim (2" body ≈ 44 mm, 3" ≈ 68 mm). |
| Cup Body | `base_od` | 35.0 mm | Base outer diameter — the taper that stops medium falling through. |
| Cup Body | `cup_h` | 48.0 mm | Overall basket height. |
| Cup Body | `wall` | 2.0 mm | Basket wall thickness. |
| Rim & Lip | `lip_w` | 3.0 mm | Rim-lip radial overhang that rests on the hole edge. |
| Rim & Lip | `lip_h` | 3.0 mm | Rim-lip thickness. |
| Mesh | `slot_w` | 3.0 mm | Mesh slot width — narrow enough to retain clay pebbles. |
| Mesh | `slot_rows` | 3 | Vertical rows of mesh slots. |
| Mesh | `slot_cols` | 8 | Slots around the circumference. |

## Presets

- **2" Net Cup (50 mm rim)** — the DWC/Kratky standard.
- **3" Net Cup (85 mm rim)** — larger plants and NFT channels.
- **Rockwool-Cube Collar** — seats a starter cube.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Net-Cup Taper** (`socket`, "2/3in net cup") — the truncated-cone body plus
    rim lip, defined by `top_od`, `base_od`, `cup_h`, `lip_w`. The lip rests on a
    hole cut a hair under the rim, so the same taper drops into any matching lid,
    bucket or pipe.
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material seats in the hole with less clearance.
- **Societal benefit:** lets a home or community garden expand a Kratky/DWC
  system for pennies and replace algae-fouled cups without a supply run.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy: the basket wall is an outer cone frustum minus an inner
  frustum (a `makeCone` open tube — a closed 2-manifold); mesh openings are
  obround slots swept fully through the wall (open both faces). All slot cutters
  are grouped into one compound and subtracted in a single boolean pass so even
  the densest mesh renders fast and watertight.
- All shipped presets and defaults render **watertight**, single-body.
