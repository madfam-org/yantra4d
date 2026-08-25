# MOLLE Utility Pouch & Clip

**Attachment hardware for the PALS webbing grid** — generated with **CadQuery** (B-Rep).
PALS is the open webbing standard behind MOLLE (MIL-W-17337 / A-A-55301): 1 in
(25.4 mm) webbing in horizontal rows on a 1 in vertical pitch, bartacked at 1.5 in
column intervals. Because the grid is a published dimension rather than a proprietary
rail, anything cut to it attaches to anything else cut to it — packs, plate carriers,
vehicle panels, range bags.

The shared interface is the **PALS grid** itself: row height, row pitch and the strap
thickness that has to pass between webbing and backing.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Utility Pouch Body** | `pouch_body` | An open-top pouch with an integrated PALS-weave back. |
| **PALS Attachment Clip** | `pouch_clip` | A stiff clip that threads two rows and locks with a hooked foot. |
| **Belt Loop with PALS Field** | `belt_loop` | A plain-belt loop carrying a short PALS field, so a MOLLE pouch rides on a belt. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `row_h` | 25.4 mm | 18 – 32 | Webbing row height — 25.4 mm is the 1 in PALS standard. |
| `row_pitch` | 25.4 mm | 18 – 40 | Vertical pitch between rows. |
| `strap_t` | 2.6 mm | 1.6 – 4.0 | Strap thickness passing under the webbing. |
| `weave_rows` | 2 | 1 – 5 | PALS rows the clip or field spans. |
| `pouch_w` | 80 mm | 30 – 160 | Pouch width. |
| `pouch_d` | 35 mm | 18 – 90 | Pouch depth. |
| `pouch_h` | 60 mm | 25 – 140 | Pouch height. |
| `wall` | 2.4 mm | 1.6 – 6.0 | Wall thickness. |
| `belt_w` | 38 mm | 20 – 55 | Belt width for the loop mode. |

## Hyperobject Profile

- **Domain:** consumer
- **CDG interfaces:** PALS Grid (`grid` — MIL-W-17337 / A-A-55301), Weave Strap
  (`profile` — 1 in webbing cross-section), Belt Channel (`rail` — 20–55 mm webbing).
- **Commons license:** CERN-OHL-W-2.0

## Fabrication notes

This cartridge rendered watertight at defaults and at every parameter extreme on the
first verification pass — all three modes, 37 cases, no kernel intervention required.
That is worth stating rather than passing over: the geometry is built from prismatic
extrusions and straightforward cuts, with no swept helices, no lofts between dissimilar
wires, and no tangent unions. The traps that dominate the geared cartridges in this
commons simply do not arise here.

Two habits carried from elsewhere in the commons are what keep it that way. Pockets are
cut so they **vent** — an open-top pouch has no trapped void to begin with, and the
weave slots pass clean through the backing rather than stopping inside it. And every
part is one connected solid by construction: the clip's hooked foot grows out of the
strap body, and the belt loop's PALS field is unioned onto the loop wall with real
overlap rather than set against its face.

Print orientation matters more than geometry here. A PALS clip loaded in peel wants its
layers running **across** the hook, not along it; printing the clip flat on its back is
the difference between a fastener and a set of laminations.
