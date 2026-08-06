# Finger Guard & Blister Popper

Small hand-protection and dexterity aids for the kitchen and medicine cabinet,
generated with **CadQuery** (B-Rep): a blister-pack popper that presses a pill
through foil without hurting the thumb, a cut-resistant finger shield worn while
chopping, and a shorter thumb guard.

> **These are printable everyday-living _aids_, not certified medical devices or
> safety-rated PPE.** The finger guards reduce incidental knife contact with the
> nail; they are not a substitute for safe knife technique or rated cut gloves.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Blister Popper** | `pill_popper` | A fluted barrel grip with a domed nub sized under the blister pocket. |
| **Finger Guard** | `finger_guard` | A tall wraparound C-shield over the fingertip, open at the pad. |
| **Thumb Guard** | `thumb_guard` | A shorter, wider guard with more coverage for the thumb. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Finger | `finger_dia` | 17.0 mm | Fingertip diameter the guard slips over. |
| Finger | `finger_len` | 30.0 mm | How far the guard reaches down the finger. |
| Blister | `blister` | 9.0 mm | Blister pocket diameter (sets the nub size). |
| Body | `wall` | 2.4 mm | Shield / barrel wall. |
| Body | `clearance` | 0.6 mm | Per-side finger slip gap. |

## Presets

- **Standard Blister Popper**.
- **Index-Finger Guard**.
- **Thumb Guard**.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Blister Popper** (`snap`, internal) — the pressing/gripping geometry,
    defined by `blister`, `finger_dia`, `clearance`, `wall`. The nub is sized
    just under the blister pocket so pills push through the foil cleanly.
- **Material awareness:** `tolerance_by_material` is declared — guard fit tunes
  to a rigid or slightly flexible material.
- **Societal benefit:** reduces daily pain for arthritic thumbs and incidental
  kitchen cuts, using aids sized to the exact blister and finger.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
