# Gravity Pet Dispenser

Turns an inverted PET bottle into a self-refilling water or feed station,
generated with **CadQuery** (B-Rep). A base screws onto the bottle neck (a real
**PCO-1881** finish thread) and holds the bottle over a trough; gravity refills
the pool to the bottle-mouth level as the animal drinks or eats.

Shares the bottle-neck thread interface with the
[`bottle-thread`](../../bottle-thread/) cartridge.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in **food-safe filament** and clean regularly.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Water Base** | `water_base` | A threaded socket on three legs over a broad drinking trough; water refills by gravity. |
| **Feed Hopper** | `feed_hopper` | The same neck thread over a steeper chute so dry food slides down as it is eaten. |
| **Bird Dispenser** | `bird_dispenser` | A compact perch-and-cup version for a bird feeder. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bottle Neck | `neck_standard` | PCO-1881 | Bottle neck finish (thread diameter + pitch). |
| Trough / Pool | `trough_dia` | 95.0 mm | Drinking / feed pool diameter. |
| Trough / Pool | `trough_h` | 32.0 mm | Pool wall height. |
| Trough / Pool | `gap` | 9.0 mm | Gravity gap under the bottle mouth (sets refill level). |
| Trough / Pool | `wall` | 3.0 mm | Pool / socket wall. |
| Thread Fit | `clearance` | 0.4 mm | Per-side female-thread gap for a printable screw fit. |
| Thread Fit | `extra_turns` | 0.0 | Extra engagement turns (slower render). |

## Presets

- **Dog Water Station** — 120 mm pool, PCO-1881.
- **Kibble Hopper** — 38-400 wide-mouth neck, chute feed.
- **Bird Water Cup** — compact 70 mm perch cup.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **PET Bottle Neck** (`thread`, `PCO 1881`, compatible with `bottle-thread`)
    — a real single-start helical female thread matched to the neck finish,
    defined by `neck_standard`, `clearance`, `wall`, `extra_turns`. Any part in
    the commons that threads a PCO-1881 neck mates with the same bottles.
- **Material awareness:** `tolerance_by_material` is declared — thread
  `clearance` tunes to the printer/material for a smooth screw fit.
- **Societal benefit:** a discarded soda bottle plus one printed base becomes a
  days-long pet water/feed supply with no proprietary reservoir or ongoing cost.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- The thread is swept along a genuine `makeHelix` with the rib root pushed into
  the wall so the boolean is volumetric — all outputs render **watertight** and
  fast (~2–8 s).
