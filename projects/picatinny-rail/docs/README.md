# Picatinny / M-LOK Accessory Rail

The universal accessory-mounting interface, generated with **CadQuery** (B-Rep).
Models the **MIL-STD-1913 (Picatinny)** rail cross-section and the **M-LOK**
negative-slot standard so printed adapters mate real hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rail Section** | `rail_section` | A length of MIL-STD-1913 rail: trapezoidal cross-section (flat top, 45° clamping flanks, lower locating flange) with transverse recoil grooves on the 10 mm pitch. Set `standard = mlok` to emit an M-LOK bar instead. |
| **M-LOK Slot Strip** | `mlok_strip` | A flat bar carrying the M-LOK negative slots (7 × 32 mm rounded slots on 40 mm centres) plus bolt-down holes. |
| **Rail Adapter** | `rail_adapter` | A short base with a Picatinny cross-section on top and a flat, bolt-down bottom — fasten an accessory to a rail. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rail Standard | `standard` | picatinny | `picatinny` (MIL-STD-1913) or `mlok` (negative slots). |
| Size | `slots` | 5 | Recoil grooves / M-LOK slots — drives length. |
| Size | `base_th` | 4.0 mm | Substrate thickness under the rail / strip. |
| Size | `extra_w` | 0.0 mm | Widen the base beyond the 21.2 mm rail footprint. |
| Mounting | `bolt_dia` | 5.2 mm | Bolt-hole clearance diameter (≈ M5; 0 = none). |
| Mounting | `bolt_count` | 2 | Bolt-down holes along the base centreline. |

## MIL-STD-1913 geometry (nominal)

- Overall rail width **21.20 mm**; flat top width **~15.70 mm**.
- 45° angled clamping flanks forming the recoil recess.
- Recoil-groove pitch **10.0 mm** (0.394"), groove width **5.35 mm** (0.206").
- M-LOK slots: 7 mm × 32 mm rounded, 40 mm on-centre.

Printed threads are not involved (rail/slot interface), so every render is fast.

## Presets

- **Short 5-Slot Rail** — a compact Picatinny section.
- **Long Optic Rail (13-slot)** — a full-length scope base.
- **M-LOK Handguard Strip** — a bolt-on M-LOK slot bar.
- **Accessory Adapter Base** — a Picatinny-topped bolt-down adapter.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Picatinny 1913 Rail** (`rail`, *MIL-STD-1913 / M-LOK*) —
  defined by `standard` and `slots`. Any part built on the same standard shares
  the mating cross-section / slot geometry.
- **Material awareness:** `tolerance_by_material` is declared; the clamping fit of
  a printed rail depends on filament, so tune it per material/printer.
- **Societal benefit:** the most widely-adopted open accessory-mounting standards —
  a printable, dimensionally-real rail lets makers fabricate mounts and adapters on
  demand instead of buying single-purpose hardware.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
