# Pill Cutter & Crusher

A small home kit for managing solid medication, generated with **CadQuery**
(B-Rep): a splitter that centres a tablet in a V-pocket under a razor-blade slot
for a clean half, a crusher cup with a domed grinding floor, and a graduated
dosing cup for liquid medicine.

> **These are printable everyday medication-handling _aids_, not certified
> medical devices.** Do not rely on printed parts where sterility or exact
> dosing is required; the dosing-cup graduations are approximate visual guides.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pill Splitter** | `splitter` | A block with a centring V-pocket and a transverse blade slot; end scallops help pick out the halves. |
| **Pill Crusher** | `crusher` | A stout cup with a domed grinding floor and a fluted grip. |
| **Dosing Cup** | `dosing_cup` | A tapered graduated cup sized to a target mL volume. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tablet | `pill_dia` | 12.0 mm | Tablet diameter. |
| Tablet | `pill_th` | 5.0 mm | Tablet thickness (sets pocket depth). |
| Tablet | `blade_slot` | 1.2 mm | Razor-blade guide slot width. |
| Body | `wall` | 3.0 mm | Body / cup wall. |
| Dosing | `cup_ml` | 30.0 mL | Target interior volume of the dosing cup. |

## Presets

- **Standard Round Tablet** — 12 mm × 5 mm.
- **Large Tablet Crusher** — 20 mm × 9 mm.
- **30 mL Dosing Cup**.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Pill Pocket** (`pocket`, internal) — the tablet-centring cavity, defined
    by `pill_dia`, `pill_th`, `blade_slot`. A pocket sized to the tablet gives a
    repeatable split.
- **Material awareness:** `tolerance_by_material` is declared — pocket fit
  varies with print material/shrinkage.
- **Societal benefit:** a repeatable clean split and simple crusher sized to the
  exact tablet, for dose adjustments and people who cannot swallow whole
  tablets.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
