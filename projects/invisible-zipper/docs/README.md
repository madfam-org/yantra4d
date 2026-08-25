# Invisible Zipper

The printable **concealed zipper** of skirts and dresses — generated with
**CadQuery** (B-Rep). The coil rolls to the garment's inside, so only a seam line
shows on the face. Fashion Cabinet's `invisible-zipper` notion owns the fashion
semantics (seam placement, allowance math) and bridges to **this** solid for the
hardware.

Complements [`zipper`](../../zipper/), which covers closed-end and separating
chains with the coil on the tape face. Parameter naming is shared deliberately:
`zip_length`, `tape_width`, `tape_thick`, `gap` mean the same thing in both, so a
garment can drive either cartridge from one finished-opening number.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Full Set** | `tape_left`, `tape_right`, `slider` | Both tapes mirrored across the seam with their coil beads closed and adjacent, slider parked at the bottom. |
| **Single Tape + Coil** | `tape_left` | One tape strip with its bead — a repair length, or one side of a seam. |
| **Slider Only** | `slider` | The slider body, pull bar, and torus pull ring. The piece that actually wears out. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Chain | `zip_length` | 200 mm | 60–600 | Working coil length. **Same id as `zipper`** — the FC handshake key. |
| Chain | `coil_dia` | 2.5 mm | 1.5–4.0 | Bead diameter (the concealed-zip gauge). Clamped above `tape_thick` and below 60% of `tape_width`. |
| Tape | `tape_width` | 7.0 mm | 5.0–15.0 | One tape strip — the sewn seam allowance beside the coil. |
| Tape | `tape_thick` | 1.2 mm | 0.8–2.5 | Tape thickness; also sets the slider's tape channel. |
| Pull | `pull_length` | 25 mm | 10–40 | Bar + ring, measured from the top of the slider body. |
| Fit | `gap` | 0.35 mm | 0.1–1.0 | Clearance between closed beads and inside the slider channel. Clamped to ≤ `coil_dia / 3`. |

All safety limits live as clamps in `main.py`, so `constraints` is empty and no
parameter combination can produce invalid geometry.

## Presets

- **Skirt Back (22 cm)** — the classic invisible-zip application.
- **Dress Back (55 cm)** — full-length back seam.
- **Replacement Slider** — slider only, for a repair.

## Print notes

Print in a tough material (PETG, PA, or recycled PETG — the profile sets
`recycled_material_toggle`). Lay the **tapes flat on the bed with the bead facing
up**, so the sewn edge is a clean bottom face and the bead needs no support. Print
the **slider upright** (pull ring at the top) so the tape channel bridges cleanly
and the ring prints as a full torus. Tune `gap` first on a short 60 mm test set —
too tight and the slider binds, too loose and the beads pop apart under load.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewn Tape Edge** (`tape_edge`, `flange`, internal) — `tape_width`,
    `tape_thick`, `zip_length`. **This is the sewn/set flange for the dimensional
    handshake**, mirrored exactly from the `zipper` cartridge (FC rule 5), so a
    garment can swap between a standard and a concealed zip without remapping.
  - **Coil Channel** (`coil_channel`, `socket`, internal) — `coil_dia`, `gap`.
    The bore the closed bead pair rides through in the slider.
- **Commons license:** CERN-OHL-W-2.0

## Fashion Cabinet bridge

FC-side `notion.hardware_ref` block for an `invisible-zipper` notion:

```json
{
  "platform": "yantra4d",
  "project_slug": "invisible-zipper",
  "linked": true,
  "params_map": {
    "zip_length": "opening_length_mm",
    "tape_width": "seam_allowance_mm",
    "tape_thick": "fabric_thickness_mm * 1.2",
    "coil_dia": "zip_gauge_mm",
    "gap": "print_clearance_mm"
  }
}
```

`zip_length` is the handshake key: it carries the identical meaning and id in
both `zipper` and `invisible-zipper`, so a garment's finished opening length
drives whichever closure the pattern calls for.
