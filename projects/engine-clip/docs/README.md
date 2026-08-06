# Engine Bay / Hose Clip

Under-hood routing that tidies vacuum hoses, fuel lines and wire looms,
generated with **CadQuery** (B-Rep), so they don't chafe, rattle or melt on hot
parts. Snap a hose three ways: a screw-down clip, a push-on sheet-metal edge
clip, and a routing comb for a loom bundle. Sized to real split-loom and hose
outer diameters (1/4"–3/4", ~10–25 mm).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Under-hood parts near heat should be printed in a **high-temperature material**
> (ASA, nylon or PC); keep clips away from the exhaust and manifold.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Screw Clip** | `hose_clip` | A snap C-clip that grips a hose/loom, with a flat screw tab to fasten to a bracket. |
| **Edge Clip** | `edge_clip` | A clip that presses onto a sheet-metal edge/flange and carries a hose C-cradle. |
| **Loom Comb** | `loom_rail` | A flat comb carrying several hose C-clips in a row to route a wire-loom bundle together. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Hose / Loom | `hose_od` | 13.0 mm | Outer diameter (1/4" loom ~10, 3/8" ~13, 1/2" ~17, 3/4" ~25; vacuum hose 6–13). |
| Hose / Loom | `wall` | 2.6 mm | Wall of the clip C-section. |
| Hose / Loom | `clip_w` | 10.0 mm | Clip width along the hose. |
| Hose / Loom | `mouth` | 0.8 | Mouth opening as a fraction of hose OD (smaller grips harder). |
| Hose / Loom | `screw_d` | 4.5 mm | Fastening screw clearance. |
| Hose / Loom | `clearance` | 0.3 mm | Per-side gap on the bore and edge slot. |
| Edge Grip | `edge_th` | 2.0 mm | Sheet-metal edge/flange thickness (~1–3 mm typical). |
| Edge Grip | `edge_reach` | 12.0 mm | How far the grip reaches onto the panel. |
| Loom Comb | `n_clips` | 3 | Clips on the comb. |
| Loom Comb | `clip_pitch` | 20.0 mm | Center-to-center clip spacing. |

## Presets

- **Vacuum-Hose Clip (10 mm)**.
- **Fender-Edge Hose Clip**.
- **4-Way Loom Comb**.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Hose Snap Clip** (`snap`, internal) — the C-section that snaps around the
    hose/loom, defined by `hose_od`, `wall`, `mouth`, `clearance`. The same clip
    scales across the split-loom OD family.
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material snaps over the hose and retains it with a tighter mouth.
- **Societal benefit:** keeps an engine bay tidy and safe (loose lines are a fire
  and reliability risk) from durable printed parts, and lets a mechanic
  standardise routing instead of hunting a discontinued OEM clip.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy (the snap C-section rule): every clip is a full ring minus a
  mouth slot narrower than the diameter — one manifold C-section, never a tangent
  kiss. The screw tab, edge-grip jaw and rail are solid and overlap into the clip
  body; the edge grip is a C-slot open on one side (vented).
- All shipped presets and defaults render **watertight**, single-body.
