# Boning Stay and Channel

The printable boning of corsetry and structured garments — generated with
**CadQuery** (B-Rep). A flat flexible **stay** holds a seam line straight; the
sew-in **channel** is the casing that carries it. Fashion Cabinet's `boning`
notion owns the fashion semantics (which seams get boned, and how long each run
is) and bridges to **this** solid for the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Stay and Channel** | `set` | A stay and its matching channel side by side, print-ready. |
| **Stay only** | `stay` | One flat blade — rounded rectangle, rounded tips. |
| **Channel only** | `channel` | The C-profile casing: slot through both ends, sew flange on each long edge. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Stay | `stay_length` | 150 mm | Length along the seam. The channel is cut to match. |
| Stay | `stay_width` | 7 mm | Flat-face width; wider resists buckling edge-on. |
| Stay | `stay_t` | 1.5 mm | Thickness; thinner flexes more around the body. |
| Stay | `tip_r` | 3 mm | Tip corner radius, clamped to `stay_width / 2` so it never degenerates. |
| Channel | `channel_wall` | 1.2 mm | Casing wall; also sets the sew-flange thickness. |
| Channel | `channel_clear` | 0.4 mm | Slip fit per side between stay and slot. |

The channel is fully derived: slot is `stay_width + 2·channel_clear` by
`stay_t + 2·channel_clear`, so a stay always slides into its own channel with no
second set of dimensions to keep in sync.

## Print notes

Print **flat on the bed**, stay face-down — the blade's flex should come from
layers stacked across the thickness, not along it. PETG or nylon for a springy
stay that returns to straight; TPU-95A for a very soft bodice; PLA only for
short stays that see little bending. The channel prints unsupported (the slot
bridges across its own width) and is sewn down through the flanges on both long
edges, the same way twill casing tape is applied. Two to four perimeters is
plenty; the stay wants near-solid infill.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Channel Slot** (`socket`, internal) — the stay's seat inside the casing,
    defined by `stay_width`, `stay_t`, `channel_clear`.
  - **Sew Flange** (`flange`, internal) — **the sewn/set flange for the
    dimensional handshake**, defined by `stay_length`, `channel_wall`.

## Fashion Cabinet bridge

FC's `boning` notion carries the seam run; this cartridge supplies the solid.
Suggested `hardware_ref` on the FC side:

```json
{
  "notion": "boning",
  "hardware_ref": {
    "platform": "yantra4d",
    "project_slug": "boning-stay",
    "linked": true,
    "params_map": {
      "stay_length": "seam_length_mm - 2 * seam_allowance_mm",
      "stay_width": "boning_width_mm",
      "stay_t": "boning_gauge_mm",
      "channel_clear": "0.4"
    }
  }
}
```

The dimensional handshake happens on `sew_face`: FC's finished seam length,
less the allowance at each end, becomes `stay_length`, and the flange's
`channel_wall` is what the garment's stitch line lands on.
