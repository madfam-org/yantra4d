# Sprung Bag Clip

A one-piece **sprung clip** that reseals bags, generated with **CadQuery**
(B-Rep). The clip's side cross-section is a single **C profile** — a curved back
spine joining an upper and a lower jaw — extruded once across the width, so the
part is inherently watertight. The back spine is a **living spring**: squeeze the
finger tails, the mouth opens; release and the printed beam clamps the bag shut.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Clip** | `clip` | The standard clip at `clip_width`. |
| **Wide Clip** | `wide_clip` | The same profile at 1.8× width for cereal / freezer bags. |

Both share one grip geometry (spine + mouth), so a family of sizes reseals the
same way — a wide clip and a narrow clip are the same interface at different
spans.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Clip Size | `clip_width` | 40 mm | Jaw width (×1.8 in Wide Clip mode). |
| Clip Size | `jaw_length` | 28 mm | Forward reach of the jaws. |
| Clip Size | `jaw_height` | 12 mm | Overall C height (throat opening). |
| Spring & Mouth | `beam_thick` | 2.4 mm | Spine / jaw wall — tunes grip force. |
| Spring & Mouth | `mouth_gap` | 1.2 mm | Resting gap at the tips (0.4 mm floor keeps it printable). |
| Spring & Mouth | `tail_len` | 8.0 mm | Finger tails behind the spine. |
| Grip & Catch | `catch` | `friction` | `friction` mouth or `snap-hook` latch. |
| Grip & Catch | `grip_teeth` | on | Shallow ribs on the inner jaw faces. |

## Presets

- **Chip Bag Clip** — 40 mm friction clip for snack bags.
- **Freezer / Cereal Bag** — wide, thicker beam, snap-hook latch.
- **Coffee Bag (heavy latch)** — 55 mm, near-closed mouth, snap-hook.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Sprung Bag Clamp** (`snap`, internal) — the resealing interface, defined by
    `clip_width`, `beam_thick`, `mouth_gap`, `jaw_height`, and `catch`. The beam
    thickness sets the spring force and the mouth gap sets how thick a bag mouth
    the clip seals; the snap-hook option latches the same clamp closed.
- **Material awareness:** the mouth gap and beam thickness are exposed so the
  grip / spring can be tuned per material and printer; `tolerance_by_material` is
  declared (a stiffer filament wants a thinner beam for the same flex).
- **Societal benefit:** keeps food fresh with a printed clip instead of a bought
  bag-clip or a wasted zip bag — a trivially reprintable household staple that
  reduces single-use packaging and store dependency.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The whole clip is one extruded C profile; ribs and the snap-hook are unioned as
  features that solidly interpenetrate the jaws, and comfort fillets are clamped
  strictly below the thinnest local feature — so every shipped preset, both
  modes, and the parameter extremes render **watertight**.
