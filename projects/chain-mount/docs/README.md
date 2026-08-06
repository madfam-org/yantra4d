# Cable Drag-Chain Mount

A **cable drag-chain mount bracket**, generated with **CadQuery** (B-Rep). It
bolts the end bracket of a cable drag chain (energy chain / cable carrier) to a
frame. The chain end is a small plate with two bolt holes on a known width; this
mount presents those holes and carries its own surface-mounting holes.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **End Bracket** | `end_bracket` | A flat plate — chain-end bolt holes at one end, two surface-mounting holes at the other — to anchor the fixed end to a base plate. |
| **2020 Extrusion Bracket** | `extrusion_bracket` | An L-foot for a 2020 T-slot extrusion: chain-end holes on the upstand, M5 T-nut holes on 20 mm centres in the foot. |
| **Moving End** | `moving_end` | A plate with the chain-end holes plus a lengthwise adjustment **slot** so the moving end can be tuned along the carriage travel. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Chain | `chain_w` | 15 mm | Chain-end bolt spacing across the width. |
| Chain | `chain_h` | 12 mm | Chain-end plate height (extrusion upstand). |
| Chain | `chain_hole` | 3.4 mm | Chain-end bolt clearance (M3). |
| Plate | `plate_t` | 4.0 mm | Bracket thickness. |
| Plate | `margin` | 5.0 mm | Material margin around holes. |
| Mount | `mount_d` | 4.5 mm | Surface / T-nut bolt (M4/M5). |
| Mount | `slot_len` | 14 mm | Moving-end adjustment slot travel. |
| Mount | `foot_len` | 30 mm | Extrusion foot length. |

## The chain-end mount (why it fits)

Drag-chain end connectors bolt on through **two holes a fixed distance apart**
across the chain width (10 / 15 / 18 mm series and clones). The mount cuts exactly
that hole pair (`chain_w`) so the chain's own end bracket bolts straight on, then
adds its own surface, extrusion or slotted mounting on the other side. Plates are
filleted **as clean blanks before** holes and slots are cut, so every mode is
watertight — and this interface is declared `compatible_with: ["drag-chain"]` so
it inter-operates with the drag-chain family in the commons.

## Presets

- **15 mm Chain End** — fixed-end bracket for a 15 mm chain.
- **18 mm Chain on 2020** — extrusion-frame bracket for an 18 mm chain.
- **10 mm Moving End** — slotted moving-end mount for a 10 mm chain.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Drag-Chain End Mount** (`bolt_pattern`, *internal*, `compatible_with:
    drag-chain*) — the chain-end hole pair, defined by `chain_w`, `chain_h`,
    `chain_hole`.
  - **Surface Mount** (`bolt_pattern`, *internal*) — the surface / T-nut / slot
    mounting, defined by `mount_d`, `slot_len`, `foot_len`.
- **Material awareness:** `tolerance_by_material` is declared — bolt clearances can
  be tuned per material.
- **Societal benefit:** a printed mount that presents the chain-end bolt holes and
  its own surface / extrusion mounting lets any drag-chain run be anchored on a
  printer, CNC or robot from parts on hand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. All modes render **watertight**.
