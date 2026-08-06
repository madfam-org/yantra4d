# Microphone Clip & Thread Adapter

Mounts a microphone to any stand, generated with **CadQuery** (B-Rep). The
functional interface is the audio-industry **5/8"-27** mic-stand thread, modelled
at its real nominal diameter (15.88 mm) and pitch (0.94 mm) as a short helical rib.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Mic Clip** | `mic_clip` | Sprung C-clip for the mic body on a 5/8"-27 socket. |
| **Thread Adapter** | `thread_adapter` | 5/8"-27 female → 3/8"-16 male reducer. |
| **Shock Mount Ring** | `shock_mount_ring` | Ring + inner cradle on flexible webs. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Microphone | `mic_dia` | 50 mm | Mic barrel outer diameter to grip. |
| Microphone | `grip_wrap` | 250° | How far the C-clip wraps the mic. |
| Thread Fit & Walls | `wall` | 3.0 mm | Body and thread wall thickness. |
| Thread Fit & Walls | `clearance` | 0.4 mm | Per-side printed-thread fit slop. |
| Thread Fit & Walls | `stem_len` | 26 mm | Threaded socket stem length. |
| Thread Fit & Walls | `extra_turns` | 0 | Extra engagement turns (slower render). |

## Presets

- **Vocal Mic (SM58-size)** — 51 mm clip.
- **5/8→3/8 Reducer** — the standard mic/light-stand thread adapter.
- **Large-Diaphragm Shock Mount** — 56 mm shock ring.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Mic Stand Thread** (`thread`, *5/8-27 mic thread*) — the standardized
    female socket that screws onto any mic stand, defined by `wall`, `clearance`,
    `stem_len`, `extra_turns`. The adapter also carries a real 3/8"-16 male stud.
- **Material awareness:** `tolerance_by_material` declared — `clearance` tunes the
  printed thread fit per material/printer.
- **Societal benefit:** proprietary, easily-lost mic hardware replaced by a commons
  part on the real 5/8"-27 thread.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Threads are genuine short `makeHelix` swept ribs (≈1.5-2 turns) whose root
  overlaps the wall for a watertight boolean union — the reducer is the densest
  render (both a female 5/8"-27 socket and a male 3/8"-16 stud).
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
