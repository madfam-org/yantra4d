# Hose / Faucet Thread Adapter

Bridges mismatched water threads with **CadQuery** (B-Rep): garden-hose thread
(GHT 3/4"), faucet-aerator threads (M22 male / M24 female), and plain hose barbs.
Each end carries a **real single-start helical thread** or a barbed nozzle, so a
hose reaches a sink, a filter, or another hose.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Garden Hose → Barb** | `ght_to_barb` | GHT housing on one end, a barbed hose nozzle on the other. |
| **Faucet → Garden Hose** | `faucet_to_ght` | M22 aerator spigot to GHT — put a hose on a tap. |
| **Hose Coupler** | `coupler` | GHT on both ends — join two hoses. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread Standards | `thread_a` / `thread_b` | GHT_3/4 / barb | End standards (barb allowed on B). |
| Flow & Barb | `bore_dia` | 12.0 mm | Central fluid channel. |
| Flow & Barb | `barb_dia` | 13.0 mm | Hose ID the barb grips. |
| Flow & Barb | `barb_count` | 3 | Number of barb ridges. |
| Fit & Grip | `wall` | 2.6 mm | Wall around threads and bore. |
| Fit & Grip | `clearance` | 0.35 mm | Per-side printed-thread fit slop. |
| Fit & Grip | `grip_knurl` | on | Grip flutes around the middle. |

## Presets

- **Garden Hose → 1/2" Barb** — hose onto bare drip/utility tubing.
- **Kitchen Tap → Hose** — M22 aerator to garden hose.
- **Hose-to-Hose Join** — GHT coupler.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Garden Hose Thread** (`thread`, GHT 3/4 / M22–M24 aerator) — the helical
    mating interface, defined by `thread_a`, `thread_b`, `clearance`, `wall`. Any
    adapter carrying the same standard + clearance mates with the same fixtures.
- **Material awareness:** `clearance` is exposed so the printed thread fit tunes per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** water-access adapters on demand — connect a hose to a tap,
  filter, or bare tubing without a drawer of brass adapters.
- **License:** CERN-OHL-W-2.0

## Engine / thread notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Thread method:** single-start helical ribs swept along a genuine
  `cq.Wire.makeHelix` path built at the **mean thread radius** (non-singular sweep
  frame) and **unioned** into the wall as positive material with an `overlap` so the
  fuse is volumetric and watertight. Turns are capped (~2.5) for speed. Typical
  render 9–14 s per part.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
