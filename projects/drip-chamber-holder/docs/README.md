# Drip Chamber Holder

A real ward-workflow gap, closed with **CadQuery** (B-Rep). The drip chamber of a
gravity infusion set has to hang **vertical and still** for the drop count to mean
anything — a chamber swinging on its tubing gives a false rate, and one tilted past
a few degrees runs dry or floods. This holder clips the chamber upright and rides
the dovetail accessory face of `iv-pole-clamp`, so the whole stack is one printed
assembly on any pole.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **A printable ward convenience, not a certified medical device.** It holds the
> chamber; it does not regulate flow. Nothing here replaces a clinician reading the
> actual drip rate, and it must not be used with a device whose fall or mis-rate
> could harm a patient.

## Why this cartridge exists

Gravity infusion is still the dominant delivery method wherever pumps are scarce,
and in that setting **the drop count IS the flow measurement**. A chamber that
swings or tilts makes that measurement wrong in a way nobody notices, so the
improvised fix — taping the chamber to the pole — is both universal and
unreliable.

This cartridge extends the IV-pole family: it inherits `iv-pole-clamp`'s dovetail,
and its bore is bound to a real standard (**ISO 8536** gravity infusion sets, whose
chamber bodies run nominally 15–22 mm) rather than one hard-coded set.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Dovetail Holder** | `dovetail_holder` | C-clip chamber cradle on a dovetail tongue. |
| **Twin Holder** | `twin_holder` | Two cradles on one tongue, for a piggyback / dual-line set. |
| **Tube Guide** | `tube_guide` | A dovetail-mounted guide that routes the downstream tubing so it does not tug the chamber out of vertical. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Chamber | `chamber_dia` | 18.0 mm | Chamber body diameter — ISO 8536 sets run about 15–22 mm. |
| Chamber | `chamber_fit` | 0.4 mm | Per-side cradle clearance. |
| Chamber | `cradle_h` | 24.0 mm | Cradle height; taller holds vertical better. |
| Chamber | `wall` | 3.4 mm | Cradle wall thickness. |
| Chamber | `mouth_frac` | 0.72 | Snap opening as a fraction of the bore. |
| Mount | `dove_w` | 18.0 mm | Dovetail width — **must match the clamp it rides**. |
| Mount | `dove_h` | 8.0 mm | Dovetail projection — match the clamp. |
| Mount | `dove_angle` | 60 deg | Flank angle — match the clamp. |
| Extras | `stack_gap` | 30.0 mm | Twin cradle centre spacing. |
| Extras | `tube_dia` | 4.4 mm | Infusion tubing outer diameter (tube guide). |

## Presets

- **ISO 8536 Set (18 mm)** — the default.
- **Narrow Set (15 mm)** — the small end of the standard range.
- **Piggyback Dual Line** — two cradles.
- **Tubing Guide (4.4 mm)** — the downstream router.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Accessory Dovetail Tongue** (`rail`, mates the `iv-pole-clamp` accessory
    face) — `dove_w`, `dove_h`, `dove_angle`. Compatible with `iv-pole-clamp`.
  - **Drip Chamber Bore Series** (`socket`, ISO 8536 gravity infusion set,
    nominal 15–22 mm body) — `chamber_dia`, `chamber_fit`, `wall`, `cradle_h`,
    `mouth_frac`.
  - **Tubing Route Guide** (`socket`, internal) — `tube_dia`, `wall`.
- **Material awareness:** `chamber_fit` and `mouth_frac` are exposed so the snap
  can be tuned per material; `tolerance_by_material` is declared.
- **Societal benefit:** a repeatable vertical hold for the cost of a few grams of
  filament, on a pole clamp already in the family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- **Watertight strategy:** every body is one solid. The cradle is a **full ring
  first**, then the mouth is cut once; the dovetail tongue is unioned with a 0.2 mm
  overlap; every cut is full-depth. The mouth width is clamped to stay strictly
  less than the bore diameter, so **the C can never open into two arcs**, and the
  tongue is clamped inside the body width so the union can never leave a floating
  stub.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
