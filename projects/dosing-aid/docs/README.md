# Syringe / Dosing Aid

Aids for precise medication dosing, generated with **CadQuery** (B-Rep) and sized
to the syringe barrel (Luer-style). Print a plunger stop, an upright holder, or a
volume-solved measuring cup.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> These are printable *aids*, not certified medical devices. Verify any dose
> against the prescribed volume; the plunger stop and cup are convenience aids for
> repeatable measurement by a carer.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plunger Stop** | `plunger_stop` | A C-clip that snaps onto the plunger shaft and caps the drawn volume at `stop_depth`. |
| **Syringe Holder** | `syringe_holder` | A weighted puck with a blind barrel socket that holds a syringe upright. |
| **Measuring Cup** | `med_cup` | A graduated cup whose inner bowl volume is solved from `cup_ml`. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids match the
dispatched values (`plunger_stop` / `syringe_holder` / `med_cup`). The `aid_type`
selector mirrors the mode for the standalone/preview path.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Aid Type | `aid_type` | plunger_stop | Mirrors the active mode. |
| Syringe | `barrel_dia` | 20 mm | Syringe barrel outer diameter. |
| Syringe | `shaft_dia` | 7 mm | Plunger shaft diameter (stop). |
| Syringe | `stop_depth` | 15 mm | Plunger stop height / holder socket depth. |
| Measuring Cup | `cup_ml` | 30 mL | Target inner volume; cup dims are solved from it. |
| Build | `wall` | 2.4 mm | Ring / wall thickness. |
| Build | `clearance` | 0.5 mm | Radial fit gap over shaft/barrel. |

## Presets

- **10 mL Oral Syringe Stop** — a plunger clip for a common oral syringe.
- **Upright Holder (20 mm)** — a stand for a 20 mm barrel.
- **30 mL Measuring Cup** — a graduated cup solved to 30 mL.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Syringe Barrel Fit** (`socket`, *Luer barrel*) — the barrel/shaft fit,
    defined by `barrel_dia`, `shaft_dia`, `clearance`. The holder socket and
    plunger-stop bore are both derived from these, so a syringe that fits one
    part fits the family.
- **Material awareness:** `clearance` is exposed so the clip/socket fit can be
  tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** dosing errors are a leading cause of paediatric and elder
  medication harm; a printed stop, holder, or volume-solved cup makes a repeatable
  dose achievable by carers, matched to the exact syringe on hand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`.
- The stop is a solid C-ring (a radial slot keeps it one manifold solid), the
  holder keeps a solid floor under a blind socket, and the cup bowl is solved from
  `V = pi r^2 h` — all shipped presets render **watertight**.
