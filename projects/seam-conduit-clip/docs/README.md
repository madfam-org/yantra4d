# Seam Conduit Clip

A printable **sew-on C-clip that routes a wire bundle along a garment's seam allowance**.
Generated with **CadQuery** (B-Rep).

An e-textile harness that is not captured migrates inside the shell, snags in the wash, and
eventually pulls a solder joint apart. Two flanking sew tabs stitch this clip flat onto the
seam allowance; the open C channel above them takes the bundle. The bundle stays put but
still slides a little, so the garment can move without dragging the harness with it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Non-garment sibling: `conduit-clip`

The existing **`conduit-clip`** cartridge is the **building-scale** part with the same
idea — snap clips and standoffs that fasten EMT or metric electrical conduit to a wall.
They are not interchangeable:

| | `conduit-clip` (sibling) | `seam-conduit-clip` (this one) |
| :--- | :--- | :--- |
| World | building / appliance | garment |
| Fastens with | a screw into a bore | stitches through sew tabs |
| Sized by | conduit OD (EMT / metric standard) | wire-bundle OD **and** the seam allowance |
| Wants to be | rigid and immovable | thin, flexible, following cloth |
| Standard | real conduit trade sizes | none — the garment drives it |

If you are clipping conduit to a wall, use `conduit-clip`. If you are routing a harness
along a seam, use this one.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Clip** | `clip` | One sew-on C-clip. |
| **Harness Run** | `clip_run` | `run_count` clips on one plate at `run_pitch` — the layout mirrors the spacing you will sew. |
| **Open + Closed Pair** | `set` | An open C-clip beside a closed-ring variant, for a bundle that must never escape (thread the bundle through before terminating it). |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Bundle | `bundle_dia` | 5.0 mm | 2–16 | Bundle OD. Four thin silicone leads ≈ 4–5 mm; sleeved harness with a charge pair 7–10 mm. |
| Bundle | `mouth_frac` | 0.62 | 0.35–0.9 | C mouth width as a fraction of bundle OD. Under 0.6 the bundle snaps in and cannot fall out. |
| Clip | `wall` | 1.4 mm | 0.8–3.5 | Channel wall. Thin springs open around the bundle; thick holds a heavy harness. |
| Clip | `clip_len` | 9.0 mm | 4–30 | Length along the bundle. Short lets the harness curve; long resists twist. |
| Sewing | `tab_w` | 7.0 mm | 4–20 | Sew tab width per side. |
| Sewing | `tab_t` | 1.6 mm | 1.0–4.0 | Tab plate thickness. Keep it thin so the clip follows the seam. |
| Sewing | `hole_dia` | 1.6 mm | 1.0–2.5 | Stitch hole per tab; auto-clamped to the tab width. |
| Run Layout | `run_count` | 4 | 2–8 | Clips in the `clip_run` layout. |
| Run Layout | `run_pitch` | 45.0 mm | 15–140 | Spacing along the run. 40–60 mm keeps a light bundle from sagging. |

## Print notes

Print **flat, channel up** — no supports anywhere. The C mouth faces straight up so it
bridges nothing, and the tabs sit on the bed. PETG at 0.15 mm layers, 3 perimeters, 30 %
infill gives the mouth enough spring to snap around a bundle without cracking; PLA cracks
at the mouth root after a few dozen open-close cycles. TPU works and is more forgiving, but
a TPU mouth will not hold a heavy bundle — raise `wall` if you go soft.

The `clip_run` layout is deliberately spaced at the real `run_pitch` rather than packed
tight: laid on the seam allowance in printed order, the run is already at the right spacing
and you sew straight down the line.

Every mode exports watertight. The mouth cutter overshoots every face; the channel is
unioned into the tab plate with real Z overlap; the closed variant's bore runs through both
tube ends so nothing is a sealed void; multi-clip layouts are Compounds of separate bodies.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewn Seam-Allowance Tabs** (`flange`, internal) — **the sewn flange for the
    dimensional handshake**: the tab footprint and stitch positions on the seam allowance,
    defined by `tab_w`, `tab_t`, `clip_len`, `hole_dia`.
  - **Open C Bundle Channel** (`socket`, internal) — the harness capture, defined by
    `bundle_dia`, `mouth_frac`, `wall`. Driven by the harness spec, not the garment.

## Fashion Cabinet bridge

Expected FC consumers: **wearable-electronics jackets and vests**, **heated garments**,
**sensor sleeves and leggings**, and **e-textile kits** — any FC garment whose
harness-routing notion places a run of clips down a seam. Pairs naturally with
`seam-strain-relief` at the cable exit and `snap-electrode-carrier` at the contact.

FC-side `hardware_ref` block on the harness-routing notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "seam-conduit-clip",
      "linked": true,
      "params_map": {
        "bundle_dia": "harness_bundle_od_mm",
        "mouth_frac": "0.62",
        "wall": "1.4",
        "clip_len": "min(seam_allowance_mm * 0.9, 30)",
        "tab_w": "seam_allowance_mm * 0.55",
        "tab_t": "shell_fabric_thickness_mm + 0.8",
        "hole_dia": "1.6",
        "run_count": "harness_run_clip_count",
        "run_pitch": "harness_run_length_mm / max(harness_run_clip_count - 1, 1)"
      }
    }
  }
}
```

The mating geometry is sized by **`tab_w` and `clip_len`** (the footprint that lands on the
seam allowance) with **`hole_dia`** setting the stitch. The garment's finished
seam-allowance width is the driving dimension — it caps how wide a tab can hide under the
allowance without showing through on the face side. `run_count` and `run_pitch` come
straight from the FC notion's placed run.

`CERN-OHL-W-2.0`.
