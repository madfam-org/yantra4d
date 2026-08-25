# Strap Ring

The **strap-ring family** — generated with **CadQuery** (B-Rep). The plain loops a bag
maker sews webbing or a leather tab around to anchor a strap, hang a clip, or turn a
corner. Three shapes cover almost every commercial part. Fashion Cabinet's `strap-ring`
notion owns the fashion semantics (tab placement, tape length, bar tack position) and
bridges to **this** solid for the hardware.

## Sibling cartridge

`d-ring` is the fourth member of this family and stays a cartridge of its own: the flat-bar
**D** shape, whose straight side is the sewn bar and whose curved bow takes the clip.
Reach for `d-ring` when the flat sewn bar is the point of the part. Reach for **this**
cartridge for O, rectangular, or triangle. The two share the same webbing-width and rod
section vocabulary on purpose, so an FC garment can swap between them without redrafting.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **O-Ring** | `o_ring` | Plain round ring — free-swivelling, the classic handbag hardware. |
| **Rectangular Ring** | `rect_ring` | Square loop — keeps the webbing flat and square to the panel. |
| **Triangle Ring** | `triangle_ring` | Delta loop — apex takes the clip, flat base takes the sewn tape. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Opening | `webbing_w` | 25 mm | 10–75 | Webbing/tab width the ring must pass. Nominal webbing is 20 / 25 / 38 / 50 mm. |
| Opening | `opening` | 18 mm | 6–150 | Clear opening perpendicular to the bar; clamped to `webbing_w × 2`. |
| Rod Section | `wire_t` | 4.0 mm | 2–12 | Rod thickness in plan. A printed ring needs roughly twice a cast metal one's section. |
| Rod Section | `wire_h` | 4.5 mm | 2–14 | Rod height out of plan — also the print height. |
| Rod Section | `round_r` | 1.2 mm | 0.2–5.0 | Section rounding; clamped to 45 % of the smaller rod dimension. |

On the **O-ring** the bore is the larger of `webbing_w` and `opening`, so a folded tape
passes through whichever way it is threaded.

## Presets

- **25 mm Webbing Rectangle** — the everyday pack ring.
- **38 mm Pack Triangle** — heavy section for a shoulder-strap anchor.
- **20 mm Handbag O-Ring** — light and round.

## Geometry notes

Every ring is one plan outline extruded, minus one oversized inner outline — a single
boolean pair, then guarded fillets on the resulting rod section. No sweeps, no lofts, no
post-cut chamfers. The triangle's outer outline is offset from the inner one by the rod
thickness measured **perpendicular to each face**, which is why the offset scales with the
apex half-angle rather than being a naïve uniform grow; a uniform grow leaves the apex
paper-thin.

## Print notes

Print **flat in the ring plane** — the whole part is a prism, nothing overhangs, no
supports. Print the ring **tall** (`wire_h` up) if you can, because a printed ring fails at
the layer bond and a taller section puts the strap load along the layer lines rather than
across them. PETG, ASA or nylon at 5–6 perimeters and 60 % infill for anything load
bearing; PLA only for a decorative or display ring.

**Round the bearing edge.** `round_r` is not cosmetic: a sharp printed edge saws through
webbing under repeated load far faster than a cast ring's radius would. Leave it at 1.2 mm
or more on any ring that a strap actually moves through.

All three modes export watertight, single-body, with distinctly different volumes.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Tape Bar** (`flange`, internal) — **the sewn flange for the dimensional handshake**:
    the bar the webbing wraps and is bar-tacked around. Defined by `webbing_w`, `wire_t`,
    `wire_h`.
  - **Clip Opening** (`rail`, internal) — the loop a snap hook or carabiner rides, defined
    by `opening`, `wire_t`, `round_r`.

## Fashion Cabinet bridge

Consumed by FC's **shoulder strap**, **crossbody strap**, **backpack haul loop**, **tote
handle anchor** and **dog-collar tab** garments — every place a tape terminates in a loop
rather than a buckle.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "strap-ring",
  "linked": true,
  "params_map": {
    "webbing_w": "webbing_width_mm",
    "opening": "webbing_width_mm * 0.72",
    "wire_t": "webbing_width_mm * 0.16",
    "wire_h": "webbing_width_mm * 0.18",
    "round_r": "webbing_width_mm * 0.048"
  }
}
```

The **`tape_bar`** interface is the handshake surface: FC drives its own
`webbing_width_mm` into `webbing_w`, and the entire rod section scales from that one
number, so a garment re-drafted from 25 mm to 38 mm tape gets a proportionally heavier ring
without anyone touching a hardware parameter. `wire_t` and `wire_h` are exposed
independently so a maker can override the section upward for a load-bearing anchor while
keeping the tape fit exact.

`CERN-OHL-W-2.0`.
