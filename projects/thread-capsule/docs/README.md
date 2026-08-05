# Threaded Storage Capsule

A screw-together waterproof EDC canister, generated with **CadQuery** (B-Rep). A
tube body with an external thread mates a lid with a matching internal thread, an
O-ring seat groove, and a keyring loop.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part(s) | Description |
| :--- | :--- | :--- |
| **Body** | `body` | A tube: closed bottom, open top with an external male thread. |
| **Lid** | `lid` | A cap: internal female thread + O-ring groove in the seat + keyring loop. |
| **Capsule (both)** | `body` + `lid` | A 2-part preview: the lid perched above the body so the mating pair is visible at once. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Interior Size | `inner_dia` | 24 mm | Usable diameter — also sets the thread nominal. |
| Interior Size | `inner_len` | 50 mm | Usable body length. |
| Thread & Walls | `wall` | 2.4 mm | Body and lid wall. |
| Thread & Walls | `clearance` | 0.4 mm | Per-side thread fit gap. |
| Seal & Loop | `oring` | on | O-ring groove in the lid seat. |
| Seal & Loop | `oring_dia` | 2.0 mm | O-ring cord diameter. |
| Seal & Loop | `loop` | on | Keyring loop on the lid. |

## Thread technique & mating

Threads use the repo's watertight thread idiom — a trapezoidal profile swept along a
real `makeHelix` path for ~2.5 turns, unioned as a rib whose root is pushed **into**
the wall (the overlap), with the wall extending a pitch beyond the thread ends so the
helix embeds in solid material. Render time is ~4–6 s per part.

**Body ↔ lid mate (verified):** both threads use the same pitch (`≈ inner_dia ×
0.12`) and depth (`0.5 × pitch`). The lid's female bore clears the body's male
**crest** by exactly `clearance` per side (`bore_r = male_major_r + thread_depth +
clearance`), so the female crest lands just outside the male pitch line and the two
threads interlock with a printable screw fit. Print the body and lid at the same
`inner_dia`, `wall`, and `clearance` and they screw together.

## Presets

- **Pocket Capsule Body** — a 24 mm × 50 mm body.
- **Matching Lid (O-ring)** — the mating lid with an O-ring groove and loop.
- **Big Waterproof Lid** — a 40 mm lid with a 3 mm O-ring cord.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Capsule Screw Thread** (`thread`, internal) — defined by
  `inner_dia`, `clearance`, `oring`, `oring_dia`. Any body and lid built on the same
  nominal + clearance mate.
- **Material awareness:** `tolerance_by_material` — the screw fit and O-ring seal
  depend on filament; tune `clearance`.
- **Societal benefit:** a waterproof, reusable canister sized to its contents —
  matches, medication, cash, electronics, geocaching — instead of single-use packaging.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
