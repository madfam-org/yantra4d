# Snap Hook with Swivel

The printable **bolt-snap hook with a swivel eye** — generated with **CadQuery** (B-Rep).
The clip that joins a bag strap to its D-ring, a lanyard to a key ring or a lead to a
collar, with a swivel behind it so the strap never winds itself into a twist. The gate is a
**compliant flexure**: a slim arm moulded into the hook body that sweeps open under a thumb
and springs back closed, so there is no loose spring to lose. Fashion Cabinet's
`snap-hook-swivel` notion owns the fashion semantics (strap-end finishing and hook
placement) and bridges to **this** solid for the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Hook + Swivel Eye** | `set` | Both pieces laid side by side with a print gap — two separate solids on one plate. |
| **Hook (with gate and post)** | `hook` | The C-arc, the compliant gate flexure, the neck, and the swivel post with its retaining head. |
| **Swivel Eye** | `eye` | The webbing loop plate with the bore that drops over the post. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Webbing | `webbing_w` | 25.0 mm | 10–50 | Tape width. The eye's slot spans this + 1 mm. |
| Webbing | `webbing_t` | 1.6 mm | 0.8–4.0 | Tape thickness. The slot opens to 2× this, since the strap end folds back. |
| Hook | `hook_r` | 9.0 mm | 5–20 | Throat inner radius. Must clear whatever the hook clips onto. |
| Hook | `stock_d` | 5.0 mm | 3.0–9.0 | Hook rod section — the whole strength of the part. |
| Hook | `gate_t` | 1.6 mm | 1.0–3.0 | Compliant gate spring thickness. Keep ≥ 1.4 mm in PLA. |
| Swivel | `swivel_d` | 5.0 mm | 3.0–9.0 | Swivel post diameter. The eye's bore is this + 0.4 mm. |

## Presets

- **Bag Strap** — the 25 mm default.
- **Lanyard Clip** — 10 mm fine section for key fobs.
- **Dog Lead** — 38 mm heavy section.

## Assembly

The two parts are **not** print-in-place. Print both, then press the swivel eye down over
the hook's post: the lofted retaining head flexes past the bore and snaps captive behind
it, leaving the eye free to rotate on the post shank. Warm the eye slightly (a few seconds
in hot water) if the head will not pass — that is easier and safer than reaming the bore,
which would leave the swivel loose enough to pop off later.

If the head still will not pass, raise `swivel_d` by one step and reprint the eye: the
head diameter derives from the post, so the eye's bore grows with it.

## Print notes

Print **flat on the bed** as laid out in `set` mode. The gate flexure is the critical
feature: printed flat, its layer lines run **along** the arm, which is the only orientation
that survives repeated flexing — a gate printed standing up will snap off on the first
open. PETG or nylon; PLA works for a key fob but the gate fatigues.

Four perimeters, 40 % infill, 0.15 mm layers. The gate root is deliberately fattened into a
land, so the spring never begins at a knife edge — do not "clean up" that bulge.

Every mode exports watertight. The hook's C is a trimmed `makeTorus` (never a swept arc,
which degenerates), the retaining head is a lofted frustum with a flat cap (never a sphere
cap, whose pole singularity reads non-watertight), and the gate nose is a flat-topped loft.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Eye Webbing Slot** (`flange`, internal) — **the threaded tape edge for the
    dimensional handshake**: the slot the strap end loops through and is stitched back
    onto. Defined by `webbing_w`, `webbing_t`, `stock_d`.
  - **Swivel Joint** (`socket`, internal) — the post-and-bore rotating joint between the
    two parts, defined by `swivel_d`, `stock_d`.
  - **Gate Flexure** (`snap`, internal) — the compliant spring gate, defined by `gate_t`,
    `hook_r`, `stock_d`.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **detachable bag and tote straps**,
**crossbody and camera slings**, **lanyard and badge-holder** notions, **dog leads and
harness clips**, and any garment notion with a **removable strap** that must not twist.

FC-side `hardware_ref` block on the `snap-hook-swivel` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "snap-hook-swivel",
      "linked": true,
      "params_map": {
        "webbing_w": "strap_width_mm",
        "webbing_t": "strap_thickness_mm",
        "hook_r": "max(5.5, mating_ring_bar_dia_mm * 2.2)",
        "stock_d": "max(3.2, strap_width_mm * 0.20)",
        "gate_t": "max(1.2, strap_width_mm * 0.065)",
        "swivel_d": "max(3.2, strap_width_mm * 0.20)"
      }
    }
  }
}
```

The garment drives the hardware from two directions: the finished strap width flows into
`webbing_w` (sizing the eye's slot) and into the section sizes, while the **mating** ring's
bar diameter — the D-ring or O-ring the FC garment already places — caps `hook_r` so the
throat always clears it. `eye_webbing_slot` is the interface FC uses for the dimensional
handshake when finishing the strap end.

`CERN-OHL-W-2.0`.
