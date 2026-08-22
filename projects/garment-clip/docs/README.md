# Garment Clip

The **print-in-place spring clip** for garments — generated with **CadQuery**
(B-Rep). Two jaws joined by an integral flexure hinge, printed flat on the bed as
one solid. No assembly, no separate spring, no rivet.

Squeeze the tails, the flexure bends, the jaws open. It clips a hanger's shoulder
to hold trousers, pins a size ticket to a sample, closes a bag of trim, or holds a
hem while it is pressed.

This is a **flexure** clip, not a torsion-spring clothespin. A printed torsion
spring needs a loose coil and an assembly step; a flexure is one piece of material
bending in its elastic range. That is what lets the clip come off the bed
finished — and it is also what constrains the material, below.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plain Clip** | `clip` | Two jaws and the flexure. Smooth jaw faces. |
| **Toothed** | `toothed` | Gripping ribs added across both jaw faces, for slippery fabric. |
| **Hanger Clip** | `hanger` | The toothed clip with a **closed** rod loop on its spine, so it hangs on a rail by itself. |

The loop is closed rather than an open hook on purpose: a small clip on an open
hook shakes off a rail.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Jaw | `jaw_len` | 34 mm | Nose to hinge. Longer jaws give more leverage over the flexure — easier to squeeze, less grip for the same web. |
| Jaw | `jaw_w` | 16 mm | Bite width. Wide spreads pressure so it does not mark a pressed hem. |
| Jaw | `jaw_t` | 4.0 mm | Jaw slab thickness. Keep it at least 3 × the web, or the squeeze bends the jaws instead of the spring. |
| Jaw | `bite_gap` | 1.6 mm | Relaxed gap as printed. 1.6 suits shirt fabric; 4–6 for a folded trouser waistband. |
| Flexure | `flex_t` | 1.2 mm | **The number that matters.** Sets clamping force and decides whether the clip survives. Clamped to 0.8 mm minimum and 55 % of `jaw_t`. |
| Flexure | `flex_len` | 16 mm | Free length. Longer spreads the bending strain over more material. Clamped to 90 % of `jaw_len`. |
| Grip | `tooth_n` | 4 | Ribs per jaw (toothed / hanger only). |
| Grip | `rod_dia` | 25 mm | Rail the loop clears (hanger only). |

## Presets

- **Shirt Clip** — 34 mm, toothed.
- **Trouser Clip** — 46 mm with a 32 mm rod loop.
- **Sample Ticket Clip** — 20 mm, minimum flexure.
- **Trim Bag Clip** — 55 × 40 mm, seven ribs.

## Print notes — PETG, and why

**Print in PETG.** This is not a preference, it is the working range of the part.
A flexure stores energy by straining material elastically; PLA's elastic range is
narrow and it creeps under sustained load, so a PLA clip left clipped to a hanger
for a week comes off permanently open. PETG has the strain-to-failure and the
creep resistance for a hinge that spends its life deflected. TPU is too soft to
clamp; ABS/ASA work but warp at the thin web. **PETG, 0.15 mm layers, 4
perimeters, ≥ 40 % infill.**

Print **flat on the bed, jaws stacked in Z**, which is how the model is
oriented — the flexure's layers then run **along** its bending axis. A flexure
printed with layers across the bend delaminates on the first squeeze regardless of
material. Do not rotate this part.

No supports: the bite gap is a small self-supporting bridge at the default
`bite_gap`, and the jaw noses are chamfered with a lead-in wedge cut on a clean
blank rather than a post-cut `.chamfer()`.

If the clip is too weak, raise `flex_t` by 0.1 mm at a time — force scales roughly
with its cube, so 1.2 → 1.4 mm is a large change. If it cracks at the web root
instead of flexing, `flex_len` is too short: lengthen it before thickening it.

## Geometry notes

The jaws **overlap the flexure generously** — the arms run `blend` (at least 1.1 ×
`jaw_t`) *inside* each jaw's back edge — so the load path through the hinge is
continuous material, not a butt joint. The web's land is `flex_t` everywhere; the
model carries no knife edges, which is where a printed flexure actually fails.

The gripping ribs are **added**, not cut. A rib unioned onto a clean face,
overlapping into the jaw by half its own height, cannot produce the sealed voids
or knife edges a cut rib pattern can, and it prints without support.

The rod loop is a rounded slab minus an oversized rounded-slab bore — no torus and
therefore no tangency to manage — and the bore overshoots both faces in Y.

The three sub-solids are folded in **one at a time**
(`jaw.union(flexure).union(jaw)`) rather than pre-fused, because OCCT's fuse is
order-sensitive on this composition.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Bite Face** (`surface`, internal) — the fabric the jaws close on; defined by
    `jaw_w`, `jaw_len`, `bite_gap`.
  - **Flexure Hinge** (`custom`, internal) — the compliant spring web; defined by
    `flex_t`, `flex_len`, `jaw_t`.
  - **Rod Loop** (`socket`, internal) — the closed rail engagement; defined by
    `rod_dia`, `jaw_t`, `jaw_w`.

The clip **grips** fabric rather than being sewn to it, so the fabric contact is a
`surface` interface, not a flange-style edge interface. Nothing on this part is
stitched or threaded.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **trouser**, **skirt** and
**shorts** records (waistband thickness drives the bite), the **sample** and
**size-ticket** workflow records, and any **trim** or **notion** package that
needs closing.

FC-side `hardware_ref` block:

```json
{
  "garment": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "garment-clip",
      "linked": true,
      "params_map": {
        "bite_gap": "waistband_thickness_mm * 0.7",
        "jaw_w": "min(45, waistband_width_mm * 0.6)",
        "flex_t": "min(3.0, 0.9 + waistband_thickness_mm * 0.12)",
        "jaw_t": "max(2.5, min(3.0, 0.9 + waistband_thickness_mm * 0.12) * 3)"
      }
    }
  }
}
```

The garment drives the hardware: FC's **waistband thickness** — the folded,
interfaced, topstitched stack a clip actually has to close on — sets `bite_gap`
through the `bite_face` interface and, through `flex_t` on the `flexure_hinge`
interface, sets how hard it closes. A heavier waistband gets both a wider opening
and a stiffer spring, which is the coupling a fixed-size retail clip cannot make.

`CERN-OHL-W-2.0`.
