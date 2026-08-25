# Captive Nut Channel

Holds a standard **hex nut** captive so a machine screw can be tightened
one-handed from the far side of a joint. Generated with **CadQuery** (B-Rep).

Captive (or "trapped") nuts are the trick behind flat-pack furniture, printer
frames and any panel you cannot reach behind: a steel nut is held in a pocket so
it cannot spin, and a bolt threads into it from the other side. Plastic threads
strip — a trapped steel nut does not.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Slide-In Channel** | `slide_channel` | An edge bracket with a horizontal hex slot open on one end — the nut slides in from the side and seats against a solid back-stop; a screw bore crosses the seated nut and vents top and bottom. |
| **T-Slot Block** | `tnut_block` | The nut drops into a pocket from the top and is retained by a narrower screw slot above it, so it cannot fall out once the block is placed. |
| **Trap Plate** | `trap_plate` | A flat mounting plate with a recessed hex trap on its underside and a counterbored screw hole through the top — a drop-in threaded anchor for panels. |

All three modes render a single watertight body (`body_count == 1`).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Nut | `nut_size` | M5 | M4 (7 mm A/F) or M5 (8 mm A/F). |
| Fit & Walls | `nut_clear` | 0.35 mm | Across-flats clearance so the nut slides/drops in. |
| Fit & Walls | `wall` | 3.0 mm | Material around the pocket. |
| Fit & Walls | `depth_clear` | 0.4 mm | Extra pocket depth over nominal nut thickness. |
| Sizing | `body_len` | 30.0 mm | Overall bracket / block / plate length. |

### Nut stock (nominal across-flats × thickness, mm)

| Size | A/F | Thickness | Screw |
| :--- | :--- | :--- | :--- |
| M4 | 7.0 | 3.2 | M4 |
| M5 | 8.0 | 4.0 | M5 |

Values follow the ISO 4032-style hex nut; verify against your hardware.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - `hex_nut_pocket` — a `pocket`, standard **M4/M5 hex nut**.
  - `screw_clearance_bore` — a `socket` for the machine screw.
- **Compatible with:** `drum-hardware`. The M5 pocket + screw bore takes the same
  M5 fastener as the **iso-m5** drum tension-rod family, so a printed captive-nut
  bracket and a drum-hardware M5 rod share hardware.
- **License:** CERN-OHL-W-2.0.

## Printing notes

- Print with the nut face **down** (slide channel, T-slot) or the trap face
  **down** (trap plate) so the hex pocket needs no support.
- If the nut drops out too easily, reduce `nut_clear`; if it will not seat, raise
  it. 0.35 mm/AF is a good starting point for a 0.4 mm nozzle.
- The **T-slot block** retains the nut against gravity once assembled; the
  **slide channel** relies on the screw to keep the nut seated.
