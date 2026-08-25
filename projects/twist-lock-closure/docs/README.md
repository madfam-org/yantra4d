# Twist-Lock Closure

The classic handbag **twist lock** in three printable parts — generated with **CadQuery**
(B-Rep). An oval turn-piece rotates a quarter turn to trap the flap, a backplate with a
matching oval keeper slot is riveted through the flap, and a spreader washer takes the load
on the reverse of the leather. Fashion Cabinet's `twist-lock-closure` notion owns the
fashion semantics (flap overlap, closure placement) and bridges to **this** solid for the
hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Turn Lock** | `turn_lock` | Body plate + pivot post + the oval turn-piece riding on it. |
| **Backplate** | `backplate` | Flap-side plate with the oval keeper slot cut clean through, plus rivet bores. |
| **Spreader Washer** | `washer` | Flat washer with a pivot bore and matching rivet bores, for the leather's reverse. |
| **Full Set (all three)** | `set` | All three as separate bodies on one plate. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Plate | `plate_l` | 34 mm | 20–60 | Plate length across the bag. Commercial locks run 25–45 mm. |
| Plate | `plate_w` | 22 mm | 14–45 | Plate width up the bag face; must clear under the flap overlap. |
| Plate | `plate_t` | 3.0 mm | 1.8–6.0 | Plate thickness. A printed plate needs more section than stamped brass. |
| Turn Piece | `turn_l` | 24 mm | 10–56 | Oval long axis; clamped to `plate_l − 4`. |
| Turn Piece | `turn_w` | 8.0 mm | 4–20 | Oval short axis — what passes through the keeper slot. |
| Turn Piece | `turn_t` | 3.2 mm | 1.8–6.0 | Turn-piece slab thickness; the pivot root is the first thing to fail. |
| Setting | `pivot_dia` | 5.0 mm | 2.5–10 | Pivot post and washer bore; clamped to `turn_w − 1.5`. |
| Setting | `leather_t` | 3.0 mm | 0.8–8.0 | Panel thickness the lock is set through — sets the post height. 3 mm ≈ 7–8 oz veg-tan. |
| Setting | `rivet_dia` | 3.0 mm | 1.5–5.0 | Rivet bore. 3 mm takes a standard double-cap rapid rivet post. |

The keeper slot is always cut **0.5 mm larger** than the turn-piece on both axes, so
`turn_l`/`turn_w` size both parts at once and the pair always mates.

## Presets

- **Messenger Flap** — 34 mm, 3 mm leather.
- **Small Satchel** — 26 mm, fine section over 2 mm leather.
- **Portfolio Case** — 48 mm, heavy section over 4.5 mm leather.

## Geometry notes

The pivot post is a **shouldered revolve with a flat top land**, not a cylinder plus a
sphere cap — the sphere pole reads as a crack and that union is banned in this commons.
The keeper slot and both rivet bores are cut with cutters that overshoot both faces, and no
fillet or chamfer follows any of those cuts; the only fillets run on clean blanks.

**The turn-piece prints fused to the post.** A free-spinning turn-piece is two loose parts
captured on a peened post — that cannot be one watertight solid, so it is out of scope for
a single-body print. Two ways to get the real thing:

1. Print `turn_lock` and snap the turn-piece free at the collar with side cutters, then
   re-pin it through the plate bore with a 2 mm brass rod peened over both ends; or
2. Print `backplate` and `washer` here and reuse a salvaged metal turn-piece — which is the
   usual repair case, since the plate is what gets lost.

## Print notes

Print every part **flat on the bed**, plate face down — nothing overhangs and no supports
are needed. PETG or ASA at 4–5 perimeters and 50 % infill; PLA works for a display piece
but creeps under a carried load. The stress path is the pivot root and the rivet-bore
walls, so do not thin `plate_t` below 3 mm for a bag that actually gets used.

Set the lock through pre-punched leather with double-cap rapid rivets in both bores, washer
on the reverse. Every mode exports watertight; `set` exports as three separate bodies with
a real print gap — never a `.union()` of non-touching solids.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Keeper Slot** (`pocket`, internal) — the oval the turn-piece rotates through,
    defined by `turn_l`, `turn_w`, `plate_t`.
  - **Rivet Pattern** (`bolt_pattern`, internal) — the two-bore setting pattern shared by
    all three parts, defined by `plate_l`, `rivet_dia`, `leather_t`.
  - **Pivot Seat** (`socket`, internal) — the post/bore stack through the panel, defined by
    `pivot_dia`, `leather_t`, `turn_t`.

This is **point-fixed** hardware: it is riveted, not sewn along an edge, so it declares no
flange interface. The sibling `kiss-lock-frame` and `strap-end-tip` cartridges are the
flange-carrying members of this shelf.

## Fashion Cabinet bridge

Consumed by FC's **messenger bag**, **satchel**, **flap crossbody** and **portfolio case**
garments — anything closed by a flap rather than a zipper.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "twist-lock-closure",
  "linked": true,
  "params_map": {
    "plate_l": "min(flap_width_mm * 0.30, 48)",
    "plate_w": "min(flap_overlap_mm * 0.65, 32)",
    "plate_t": "3.0",
    "turn_l": "min(flap_width_mm * 0.30, 48) - 10",
    "turn_w": "min(flap_overlap_mm * 0.65, 32) * 0.36",
    "turn_t": "3.2",
    "pivot_dia": "5.0",
    "leather_t": "shell_leather_thickness_mm",
    "rivet_dia": "3.0"
  }
}
```

The handshake here runs through **`rivet_pattern`** and **`pivot_seat`** rather than a sewn
edge: FC drives its shell leather thickness into `leather_t`, which sets the pivot post
height so the turn-piece lands proud of the panel instead of buried in it, and drives its
flap overlap into `plate_w` so the plate never peeks past the flap edge.

`CERN-OHL-W-2.0`.
