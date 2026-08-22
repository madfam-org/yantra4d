# Seam Strain Relief

A printable **e-textile seam strain relief** — two flat plates that sandwich a cable where
it exits a garment seam. Generated with **CadQuery** (B-Rep). Sewn face to face through the
seam allowance, they take the pull onto the stitch line so the solder joint or the
conductive-thread transition inside the garment never sees it.

Wearable-electronics garments almost always die at the cable exit. This finding is the
cheap, printable, replaceable thing that stops that.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Not the same as its siblings

| Cartridge | Scale | What it grips |
| :--- | :--- | :--- |
| **`seam-strain-relief`** (this one) | garment | Sewn into cloth; sized by seam-allowance width. |
| `strain-relief` | appliance / panel | Panel-mounted bend limiters at a plug or enclosure bore. |
| `cord-guard` | cable run | Abrasion and chew sleeves along a free cable, no garment interface. |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plate Pair** | `plate_pair` | Both clamp plates side by side with a print gap — two separate bodies. |
| **Single Plate** | `plate` | One plate. Both halves are identical, so print two of these if you prefer. |
| **Full Set (pair + tail sleeve)** | `set` | The pair plus a slotted tail sleeve for the cable run past the seam — three bodies on one plate. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Cable | `cable_dia` | 4.0 mm | 1.5–10 | Jacket OD. Silicone e-textile ribbon 3–5 mm, USB-C tail 4–6 mm. |
| Cable | `grip` | 0.35 mm | 0–0.8 | How far under the jacket OD the closed groove pair squeezes. 0 for stiff PVC. |
| Plate | `plate_len` | 26.0 mm | 12–60 | Length along the cable run. Longer spreads pull over more stitches. |
| Plate | `plate_w` | 14.0 mm | 10–40 | Width across the seam allowance. Auto-raised to `cable_dia + 8` so a stitch lane survives both sides of the groove. |
| Plate | `plate_t` | 2.2 mm | 1.4–5.0 | Plate thickness. See the flex note below. |
| Sewing | `sew_holes` | 6 | 4–12 | Stitch holes per plate, split evenly between the two lanes. |
| Sewing | `hole_dia` | 1.6 mm | 1.0–2.5 | Stitch hole diameter. 1.6 mm passes doubled upholstery thread. |

## The flex note (PETG / TPU)

The clamp is meant to bend slightly with the garment rather than sit on it like a rivet.
At `plate_t` 1.4–1.8 mm a PETG plate keeps enough live flex to follow a seam through a
wash cycle; above about 3 mm it stops flexing and starts levering on the fabric, which is
what tears stitches out. If the garment is a knit or the exit sits over a joint, print the
plates in TPU (95A or harder) at 2.5–3 mm instead — the softer material makes up the
stiffness and the groove grips better without needing `grip` above 0.3 mm. Do not set
`grip` above about 0.5 mm on a rigid filament: past that the groove pair crushes conductors
rather than gripping the jacket.

## Print notes

Print **flat, groove up** — every mode is self-supporting with no bridging and needs no
supports. 0.15 mm layers, 4 perimeters, 40 % infill for PETG; for TPU drop to 2 perimeters
and 20 % and slow the first layer. The tail sleeve in `set` mode prints lying on its side
with the relief slot facing up, so the slot bridges rather than overhangs.

Every mode exports watertight. The sew holes cut clean through both faces; the groove is a
cylinder overshooting both plate ends, so no coincident surfaces survive; the sleeve slot
opens the tube so no void is sealed.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewn Seam-Allowance Edge** (`flange`, internal) — **the sewn flange for the
    dimensional handshake**: the stitch lanes that land on the seam allowance, defined by
    `plate_len`, `plate_w`, `sew_holes`, `hole_dia`.
  - **Cable Clamp Channel** (`socket`, internal) — the groove pair that grips the jacket,
    defined by `cable_dia`, `grip`. Internal to the finding, not FC-driven beyond material
    tolerance.

## Fashion Cabinet bridge

Expected FC consumers: **wearable-electronics jackets and vests**, **heated garments** and
**sensor leggings** — any FC garment whose cable-exit notion needs the seam hardware, plus
**e-textile kits** where a charge tail leaves the shell.

FC-side `hardware_ref` block on the cable-exit notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "seam-strain-relief",
      "linked": true,
      "params_map": {
        "cable_dia": "cable_jacket_od_mm",
        "grip": "0.35",
        "plate_len": "min(seam_allowance_mm * 2.2, 60)",
        "plate_w": "seam_allowance_mm * 1.4",
        "plate_t": "shell_fabric_thickness_mm + 1.4",
        "sew_holes": "6",
        "hole_dia": "1.6"
      }
    }
  }
}
```

The mating geometry is sized by **`plate_len` and `plate_w`** (the sewn footprint on the
seam allowance) together with **`sew_holes` and `hole_dia`** (the stitch pattern FC's
notion places). The garment's finished seam-allowance width is the driving dimension;
`cable_dia` comes from the harness spec, not from the garment.

`CERN-OHL-W-2.0`.
