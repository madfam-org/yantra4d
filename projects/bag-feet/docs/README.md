# Bag Feet

The **dome studs** set into the base of a handbag or briefcase so the bag stands off the
floor and the leather does not scuff — generated with **CadQuery** (B-Rep). A foot is a
shallow dome on a flange with a boss underneath that passes through a punched hole; a
backing washer inside the bag spreads the load so the foot does not pull through the
lining. Fashion Cabinet's `bag-feet` notion owns the fashion semantics (how many feet,
where they sit on the base pattern) and bridges to **this** solid for the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Foot** | `foot` | Dome + flange + boss, in whichever boss style is selected. |
| **Backing Washer** | `washer` | The flat washer for the inside of the base panel, bore matched to the boss. |
| **Foot Set (foot + washer)** | `set` | One of each, as two separate bodies on one plate. |

A bag normally takes four or five feet; print the `set` mode as many times as you need.

## Two boss styles

`prong_style` switches how the foot is fixed, and it changes **both** parts at once:

- **Screw post** — the boss carries a cosmetic sawtooth thread and the washer is bored to
  match, so the washer twists on. Removable, which is the right choice for a bag you expect
  to repair again.
- **Splayable prongs** — the boss end is split into two flat tabs you fold over a plain
  bored washer with pliers. The traditional setting: faster, flatter inside, permanent.

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Dome | `foot_dia` | 14 mm | 8–30 | Dome and flange OD. Commercial feet 10–20 mm; luggage studs to 25 mm. |
| Dome | `foot_h` | 7.0 mm | 2–22 | Standoff above the flange; clamped to `foot_dia × 0.75`. |
| Dome | `flange_t` | 1.6 mm | 0.8–4.0 | Flat flange under the dome — what bears on the outside of the panel. |
| Boss | `boss_dia` | 5.0 mm | 2.5–26 | Through the punched hole; clamped to `foot_dia − 4`. Match your punch. |
| Boss | `panel_t` | 3.0 mm | 0.8–10 | Base panel including lining and stiffener — drives the boss length. |
| Boss | `prong_style` | screw | screw \| prong | See above; changes foot and washer together. |
| Washer | `washer_dia` | 16 mm | 7–40 | Backing washer OD. Make it **larger** than the foot. |
| Washer | `washer_t` | 1.8 mm | 0.8–5.0 | Washer thickness; also feeds the boss-length calculation. |

## Geometry notes

The dome is a **revolved closed profile with a flat crown land** — flange, shoulder, flank,
crown. A cylinder unioned with a sphere cap is banned in this commons because the sphere's
pole reads as a non-watertight crack, and the crown land is flat for the same reason: no
pole, no singularity.

The threads are **cosmetic ring stacks**, one revolved triangle per turn, never a helical
sweep. Two bugs found and fixed during verification are worth naming, because both produced
a silently floating second body:

1. A thread ring straddling the boss's tip taper gets sliced into a sliver — the thread now
   stops 1.2 mm clear of the taper.
2. A taper cut whose cone did not span the **full** height of its ring cutter sheared the
   boss clean through above the cone and severed the whole tip — the cone now overshoots
   the ring at both ends.

The internal thread in the washer is built into the bore cutter and applied as one single
cut, for the same watertightness reason.

## Print notes

Print the foot **dome down** with the boss pointing up — the flange acts as its own brim
and nothing overhangs. Print the washer flat. PETG or ASA at 4 perimeters and 50 % infill;
these carry the bag's whole standing weight on four small contact patches, so PLA will
creep and flatten over a season.

Setting: punch the base panel to `boss_dia`, push the boss through from outside, then either
twist the washer on (screw style) or splay the two prongs outward with pliers over the
washer (prong style). A drop of contact cement under the flange stops the foot spinning.

Every mode exports watertight; `set` exports as two separate bodies with a real print gap,
never a `.union()` of non-touching solids.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Panel Bore** (`socket`, internal) — the punched hole the boss passes through,
    defined by `boss_dia`, `panel_t`, `flange_t`.
  - **Washer Engagement** (`snap`, internal) — the boss-to-washer fixing, defined by
    `boss_dia`, `washer_t`, `prong_style`.

This is **point-fixed** hardware: it goes through a punched hole, it is not sewn along an
edge, so it declares no flange interface (the CDG sense of "flange" is a sewn/threaded
edge, not the mechanical flange under the dome — the two words collide here and only the
CDG meaning drives the FC handshake). Its shelf siblings `strap-end-tip`, `strap-ring` and
`kiss-lock-frame` carry the flange interfaces.

## Fashion Cabinet bridge

Consumed by FC's **structured tote**, **briefcase**, **weekender**, **doctor bag** and
**laptop satchel** garments — anything with a flat base that sits down on a surface.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "bag-feet",
  "linked": true,
  "params_map": {
    "foot_dia": "base_panel_width_mm * 0.05 + 8",
    "foot_h": "base_clearance_mm",
    "flange_t": "1.6",
    "boss_dia": "base_hole_punch_mm",
    "panel_t": "shell_leather_thickness_mm + lining_thickness_mm + stiffener_thickness_mm",
    "prong_style": "\"screw\"",
    "washer_dia": "(base_panel_width_mm * 0.05 + 8) * 1.15",
    "washer_t": "1.8"
  }
}
```

The handshake runs through **`panel_bore`**: FC drives its punched hole size into
`boss_dia` and its full base build-up — shell leather plus lining plus stiffener board —
into `panel_t`, and the boss length follows automatically, which is precisely the number a
maker gets wrong by hand and ends up with a foot that rattles or bottoms out. Add a
stiffener on the FC side and the boss grows to suit with no hardware edit.

`CERN-OHL-W-2.0`.
