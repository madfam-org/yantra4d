# Garter Clip

The printable **two-part suspender grip** — generated with **CadQuery** (B-Rep). A nub
plate carries a mushroom-headed button; a loop plate with a keyhole slot drops over the
head and slides so its narrow throat traps the nub. The stocking welt is pinched between
the two plates and cannot slip. This is the finding on garter belts, sock suspenders and
shirt stays. Fashion Cabinet's `garter-clip` notion owns the fashion semantics (strap
placement and welt allowance) and bridges to **this** solid for the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Clip Set (nub + loop)** | `set` | Both plates laid side by side with a print gap — two separate solids on one plate. |
| **Nub Plate (button)** | `nub` | The plate with the button post, mushroom head, and the strap slot. |
| **Loop Plate (keyhole)** | `loop` | The keyhole plate with its thumb ridge. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Strap | `strap_w` | 12.0 mm | 6–30 | Finished garter elastic width. Lingerie suspenders run 10–16 mm. |
| Strap | `strap_t` | 1.4 mm | 0.6–4.0 | Elastic thickness. It also sets the fabric gap the post must clear. |
| Plate | `plate_t` | 2.4 mm | 1.5–5.0 | Thickness of both plates. Thin lies flat and invisible under a skirt. |
| Grip | `nub_d` | 5.0 mm | 3.0–12.0 | Button post diameter — what actually holds the load. |
| Grip | `head_over` | 2.2 mm | 1.0–5.0 | Mushroom head overhang per side. More grip, bigger eye needed. |
| Grip | `grip_clear` | 0.35 mm | 0.15–0.8 | Keyhole running clearance. Raise it if the loop will not slide home. |

## Presets

- **Lingerie Suspender** — the 12 mm default.
- **Sock Suspender** — 8 mm fine section.
- **Shirt Stay** — 25 mm heavy section.

## Use

Thread the garter elastic through the nub plate's slot and stitch it back on itself. To
clip: lay the stocking welt over the button, drop the loop plate's wide eye down over the
mushroom head, then push the loop plate sideways by its thumb ridge until the narrow
throat of the keyhole is around the post. The head now overhangs the throat on both sides
and cannot lift; the welt is trapped between the plates. Reverse to release.

## Print notes

Print **both plates flat on the bed**, button up, as laid out in `set` mode. No supports:
the mushroom head is a shallow lofted frustum, not a true overhang, and the keyhole is a
plain through-cut. PETG is the right material — it stays slightly springy where PLA goes
brittle at the post root, and the post root is the stress path. Three perimeters, 40 %
infill, 0.12 mm layers (the finer layers matter here because the head's flare is only a
couple of millimetres tall and coarse layers turn it into a staircase the loop plate
catches on).

If the loop plate will not slide home, raise `grip_clear` by one step and reprint the
**loop** only. If the clip lets go under a heavy stocking, raise `head_over` — and reprint
both, since the eye must grow to pass the bigger head.

Every mode exports watertight. The keyhole is one union of eye, throat and rounded blind
end cut in a single operation, so no sliver survives at their junctions; the mushroom head
is a lofted frustum with a flat cap, never a sphere cap.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Strap Slot** (`flange`, internal) — **the threaded elastic edge for the dimensional
    handshake**: the slot the garter elastic loops through and is stitched back onto.
    Defined by `strap_w`, `strap_t`, `plate_t`.
  - **Keyhole Grip** (`snap`, internal) — the internal mating contract between the two
    plates, defined by `nub_d`, `head_over`, `grip_clear`.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **garter belts and suspender belts**,
**stocking suspenders** on corsetry and basques, **sock suspenders**, **shirt stays**, and
any lingerie notion where an elastic strap must grip a fabric edge without a metal clasp.

FC-side `hardware_ref` block on the `garter-clip` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "garter-clip",
      "linked": true,
      "params_map": {
        "strap_w": "suspender_elastic_width_mm",
        "strap_t": "suspender_elastic_thickness_mm",
        "plate_t": "max(1.8, suspender_elastic_width_mm * 0.20)",
        "nub_d": "max(3.6, suspender_elastic_width_mm * 0.42)",
        "head_over": "max(1.5, suspender_elastic_width_mm * 0.18)",
        "grip_clear": "0.35"
      }
    }
  }
}
```

The garment drives the hardware: the finished elastic width flows into `strap_w`, which
sizes the slot and, through it, both plate outlines; the elastic **thickness** flows into
`strap_t`, which sets how far the button post must stand clear so a plush elastic still
seats. `strap_slot` is the interface FC uses for the dimensional handshake when placing the
suspender strap.

`CERN-OHL-W-2.0`.
