# Soap Dispenser / Pump Adapter

Refill and pump adapters for soap / lotion / sanitizer dispensers, generated
with **CadQuery** (B-Rep) around the **real SPI "410" continuous-thread**
bottle-neck finishes those bottles use: **20-410, 24-410, 28-410** (major Ø
20 / 24 / 28 mm, 8-TPI continuous thread → **3.175 mm pitch**). The threads are
**functional single-start helical ribs**, not cosmetic grooves.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pump Collar** | `pump_collar` | A female-threaded collar that screws onto a bottle neck and presents a top opening for a standard pump-stem insert. |
| **Neck Reducer** | `neck_reducer` | Female thread (neck **A**) on the bottom + male thread (neck **B**) on top: a 410-to-410 size translator with a through channel for product. |
| **Travel Cap** | `travel_cap` | A sealing screw cap (female thread + solid top and an inner sealing lip) that closes a dispenser bottle for travel. |

## Neck Finishes

`neck_a` (and `neck_b` for the reducer) select the SPI 410 finish. Each is an
8-TPI continuous thread (3.175 mm pitch):

| Finish | Major Ø | Pitch |
| :--- | :---: | :---: |
| **20-410** | 20 mm | 3.175 mm |
| **24-410** | 24 mm | 3.175 mm |
| **28-410** *(default A)* | 28 mm | 3.175 mm |

The female bore is the male major diameter **plus `clearance` per side** so a
printed part threads on despite tolerances. Male threads are cut the male major
**minus** clearance per side so they fit a real female of the same finish.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Neck Finish | `neck_a` / `neck_b` | 28-410 / 24-410 | Bottom / top 410 finish. |
| Thread & Walls | `clearance` | 0.4 mm | Per-side printed-thread gap. |
| Thread & Walls | `wall` | 2.6 mm | Radial wall around the thread. |
| Thread & Walls | `top_th` | 2.4 mm | Cap top / reducer shoulder thickness. |
| Thread & Walls | `turns` | 3.0 | Engagement; snapped to a half-integer, capped at 3.5. |
| Thread & Walls | `knurl` | on | Vertical grip flutes. |
| Pump Opening | `pump_bore` | 20 mm | Pump-stem opening diameter (collar). |

## Presets

- **Standard 28-410 Pump Collar** — the common dispenser collar.
- **Reducer 28-410 → 24-410** — move a 28-410 pump onto a 24-410 refill.
- **24-410 Travel Cap** — seal a dispenser for travel.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **SPI 410 Bottle-Neck Thread** (`thread`, *SPI 20-410 / 24-410 / 28-410,
    8 TPI*) — the functional screw interface (`neck_a`, `neck_b`, `clearance`,
    `turns`). Declared `compatible_with: [bottle-thread]` — a collar / reducer /
    cap for a finish mates with any part built to the same 410 neck.
  - **Pump-Stem Opening** (`socket`, *internal*) — the top opening (`pump_bore`)
    that receives a pump stem.
- **Material awareness:** the printed-thread fit is exposed as `clearance` so the
  screw fit tunes per material / printer; `tolerance_by_material` is declared.
- **Societal benefit:** a working pump becomes landfill the moment its refill
  uses a different neck; threading to the real 410 finishes keeps pumps and
  bottles in service across brands.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Threads are real, not cosmetic.** A trapezoidal profile is swept along a
  genuine `makeHelix` path; the rib's **root radius is pushed into the wall**
  (`overlap`) so the boolean union is a clean volumetric merge → watertight (a
  rib whose root sits exactly on the bore surface tessellates into cracks).
- **Half-integer turn count.** The engagement is always snapped to
  `floor(turns) + 0.5` (clamped to 1.5–3.5). An *integer* turn count degenerates
  the OCCT helical sweep — the profile closes on itself, orientation flips, and
  the boolean yields a negative-volume / null body. A half-integer count is
  well-conditioned and fast; the 3.5-turn cap keeps the dual-thread reducer
  robust. All three modes and the MIN/MAX extremes render watertight, one body.
