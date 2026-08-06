# Aquarium Fitting

Rim-mounted hardware for a glass aquarium, generated with **CadQuery** (B-Rep):
a clip that hooks over the tank rim and cradles a filter hose or lily pipe, a
feeding ring that corrals floating flake food, and a slim clip for a thin glass
lily pipe. Sized by the tube diameter and the tank-rim thickness.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in **aquarium-safe filament** (uncoloured PETG is a common choice) and
> rinse before use.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Hose Holder** | `hose_holder` | A J-hook over the tank rim with a C-cradle that grips a hose or return pipe. |
| **Feeding Ring** | `feeding_ring` | A brimmed ring wall that corrals floating food, with a tether lug. |
| **Lily-Pipe Clip** | `lily_pipe_clip` | A slim rim hook with a small C-clip for a thin glass lily pipe. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tube & Rim | `tube_dia` | 16.0 mm | Hose / lily-pipe outer diameter. |
| Tube & Rim | `rim_th` | 8.0 mm | Tank glass rim thickness the hook straddles. |
| Hook | `hook_depth` | 22.0 mm | How far the hook reaches down the inside. |
| Hook | `wall` | 3.0 mm | Hook / clip / ring wall. |
| Hook | `clearance` | 0.4 mm | Per-side gap on rim slot and tube cradle. |
| Hook | `width` | 14.0 mm | Hook width along the rim. |
| Feeding Ring | `ring_dia` | 65.0 mm | Inner diameter of the food-corral ring. |

## Presets

- **Canister-Filter Hose (16 mm)**.
- **Flake Feeding Ring** — 65 mm corral.
- **Glass Lily-Pipe Clip (13 mm)**.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Tube/Rim Clip** (`socket`, internal) — the rim-straddle slot plus tube
    cradle, defined by `tube_dia`, `rim_th`, `wall`, `clearance`. The same
    interface fits any tank glass thickness and tube diameter in range.
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material grips the rim and tube with less clearance.
- **Societal benefit:** keeps hoses tidy and food contained on any tank without
  marked-up, poorly-fitting commercial accessories.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
