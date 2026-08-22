# Magnetic Button Cover

A printable **two-part adaptive conversion** that turns an existing buttoned garment into a
magnetic one **without unpicking a single button**. Generated with **CadQuery** (B-Rep).

- The **cap** snaps over the sew-through button already on the shirt. The button stays where
  it is and still looks like a button from the front.
- The **plate** is stitched behind the buttonhole side of the placket, carrying the mating
  magnet.

The placket now closes by bringing two magnets together — something a hand with arthritis,
tremor, hemiparesis or one working side can do, and a fine pinch is not.

**Why a cover rather than a magnetic button.** Replacing buttons means unpicking and
resewing every one, and the garment is then permanently altered — impossible when the
garment is a uniform, a school shirt, or something borrowed or inherited. A cap that snaps
on is reversible in seconds and moves to the next shirt.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Snap-On Cap** | `cap` | The cap that swallows the existing button. |
| **Sew-On Magnet Plate** | `plate` | The carrier plate with its perimeter sew-hole ring. |
| **Conversion Set (cap + plate)** | `set` | One of each, laid out for printing together. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Existing Button | `button_dia` | 11.0 mm | 7–40 | The button already on the garment. Shirt 11 mm, jacket 20 mm, coat 25 mm. |
| Existing Button | `button_t` | 2.2 mm | 1.0–8.0 | Button thickness; sets the socket depth. Measure the button alone. |
| Existing Button | `snap_lip` | 0.7 mm | 0.2–2.0 | How far the mouth steps in past the button rim — the retention interference. |
| Magnet | `magnet_dia` | 6.0 mm | 3–25 | Neodymium disc diameter; clamped to fit inside the button. |
| Magnet | `magnet_t` | 2.0 mm | 1.0–8.0 | Disc thickness. 6×2 and 8×3 N42 are the common adaptive sizes. |
| Magnet | `magnet_fit` | 0.15 mm | 0.0–0.5 | Pocket clearance. 0.15 mm is a press fit needing no glue. |
| Magnet | `wall` | 1.4 mm | 0.8–4.0 | Working wall — the material *between* the magnets when closed. Thinner holds harder. |
| Sewing | `sew_holes` | 6 | 0–16 | Plate stitch holes. Six spreads the magnet's pull on the placket lining. |
| Sewing | `hole_dia` | 1.6 mm | 0.8–3.0 | Stitch hole diameter; clamped to keep wall at the plate rim. |

## Magnet pockets open downward

Both pockets are cut **downward** — from the part's underside, not as a blind hole in the
top. Three things follow, and all three matter:

1. **They drain.** No sealed void anywhere in either part.
2. **They print without a bridge.** With the part on the plate the pocket is an open-topped
   cavity, so nothing spans air.
3. **The disc is captured, not glued.** The magnet drops into the pocket and is held there by
   the button (in the cap) or by the fabric the plate is stitched to. Nothing relies on
   adhesive, which is what fails first on a garment that goes through a wash.

## Print notes

Print **both parts open-face up** — cap mouth up, plate pocket up. Every cavity then opens
toward the nozzle and no supports are needed.

**PETG** at 0.15 mm layers, 4 perimeters, 60 % infill. The high perimeter count matters at
the cap's retaining lip, which is where the part is loaded every time it goes on or comes
off. PLA is acceptable and slightly stiffer but the lip will eventually crack. TPU works for
the plate but the cap will not retain.

Set `magnet_fit` to 0.15 mm and press the disc in cold — do **not** heat-set neodymium.
Above roughly 80 °C an N42 disc loses its field permanently, so a magnet installed with a
soldering iron comes out of the process dead. For the same reason, wash the garment cold.

**Get the polarity right before you commit**: install the cap magnet, offer the plate magnet
up to it, and mark which face attracts *before* pressing the plate magnet home. A pocket
pressed to 0.15 mm does not come apart again without breaking something.

Every mode exports watertight; the `set` mode returns an assembly of two separate parts, not
a fused body.

## Hyperobject Profile

Domain `wearable`. Three CDG interfaces:

- **`plate_sew_ring`** (`flange`, parameters `button_dia`, `wall`, `sew_holes`, `hole_dia`) —
  the genuine sewn edge: the plate is stitched to the placket lining through this ring, so
  the plate diameter and hole pattern are the dimensions the placket's reinforcement must
  match. This is the FC dimensional handshake.
- **`button_snap`** (`snap`, parameters `button_dia`, `button_t`, `snap_lip`) — the
  interference fit onto the garment's existing button. Point-fixed clip-on hardware.
- **`magnet_pocket`** (`pocket`, parameters `magnet_dia`, `magnet_t`, `magnet_fit`) — the
  press-fit seat for a commodity disc magnet, shared by both parts.

## Fashion Cabinet bridge

Expected FC consumers: the **dress shirt**, **blouse**, **cardigan**, **coat** and any FC
garment flagged as adaptive dressing, plus the **button** and **placket** notions.

The handshake runs on the existing button, not on new hardware: FC's button notion carries
the ligne size and thickness of the buttons the garment was made with, and those two numbers
size the cap's socket and lip. The placket notion carries the plate's stitch pattern, so the
sew ring and the placket reinforcement agree.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "magnetic-button-cover",
  "linked": true,
  "params_map": {
    "button_dia": "button_diameter_mm",
    "button_t": "button_thickness_mm",
    "snap_lip": "button_thickness_mm * 0.32",
    "magnet_dia": "min(10, button_diameter_mm * 0.55)",
    "magnet_t": "placket_layers * 1.0",
    "wall": "1.4",
    "sew_holes": "6",
    "hole_dia": "1.6",
    "magnet_fit": "0.15"
  }
}
```

The **`plate_sew_ring`** flange is what FC reads for the dimensional handshake, and
**`button_snap`** is what makes the conversion non-destructive: change the FC garment's
button ligne and the cap resizes, without the garment's own pattern changing at all. The
sibling **`sew-on-snap`** cartridge covers the case where a placket is genuinely being
re-fastened rather than adapted, and **`button-hook-aid`** covers the same accessibility
problem solved with a tool instead of a conversion.

`CERN-OHL-W-2.0`.
