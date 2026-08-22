# Chicago Screw

The two-part **binding post** leatherworkers call a Chicago screw or sex bolt — generated
with **CadQuery** (B-Rep). A barrel with a flat head and an internal bore, and a cap screw
that threads into it from the other side. Together they clamp a leather strap sandwich
without a rivet setter and, unlike a rivet, they come apart again — which is why every
adjustable strap, watch band and knife sheath uses them. Fashion Cabinet's `chicago-screw`
notion owns the fashion semantics (hole spacing, strap adjustment range) and bridges to
**this** solid for the hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Barrel Post** | `post` | Flat head + barrel + threaded blind bore + driver slot. |
| **Cap Screw** | `cap` | Flat head + threaded shank sized to the post bore + driver slot. |
| **Screw Set (post + cap)** | `set` | Both, as two separate bodies on one plate. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Head | `head_dia` | 10 mm | 6–20 | Flat head diameter, identical on both parts. Commercial screws run 8–12 mm. |
| Head | `head_t` | 2.0 mm | 1.2–5.0 | Head thickness; also sets driver-slot depth (55 % of it). |
| Head | `slot_w` | 1.2 mm | 0.6–3.5 | Flat-blade slot width; 1.2 mm suits a 4 mm cabinet blade. |
| Barrel | `post_dia` | 5.0 mm | 3–18 | Barrel OD through the punched strap hole; clamped to `head_dia − 2`. |
| Barrel | `stack_t` | 6.0 mm | 1.5–25 | Leather sandwich thickness. Two plies of 8–9 oz veg-tan ≈ 7 mm. |
| Thread | `thread_dia` | 3.0 mm | 1.6–10 | Nominal thread diameter; clamped to `post_dia − 1.8`. |
| Thread | `thread_len` | 5.0 mm | 1.5–20 | Engaged length; clamped so the bore never breaks through the post head. |

## Presets

- **Watch Strap** — 8 mm head over a 3 mm stack.
- **Belt Keeper** — 10 mm head over a 6 mm stack.
- **Knife Sheath** — 14 mm head over a 12 mm stack.

## About the threads

**The threads are cosmetic.** Each is a stack of revolved triangular rings — one ring per
turn — not a helical sweep. Long helical sweeps at this scale are the reliable way to
provoke an uncatchable OCCT segfault, and a printed 3 mm thread would not hold torque
anyway. What the sawtooth actually gives you is a light interference press that ratchets
and resists backing out.

The internal thread is built **into the bore cutter** — cylinder unioned with the ring
stack, then one single cut. The obvious alternative (cut a plain bore, then union sawtooth
crests back in) produced negative-volume slivers when verified, so it is not used here.

For a strap under real load, chase the assembled joint with a drop of thread-locker, or
print the pair oversize and tap the bore with a real M3 tap.

## Print notes

Print both parts **head down on the bed**, barrel/shank up — self-supporting, no bridging,
no supports. 0.12 mm layers give the sawtooth enough resolution to read; below 3 mm
`thread_dia` drop to 0.08 mm or accept a smooth press fit. PETG or ASA; PLA is fine for a
display piece but the shank creeps under sustained clamp load.

If the cap will not start, ream the bore mouth — the lead-in flare is only 0.9 mm deep by
design so the engaged length is not wasted. Every mode exports watertight; `set` exports as
two separate bodies with a real print gap, never a `.union()` of non-touching solids.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Binding Thread** (`thread`, internal) — the post/cap engagement, defined by
    `thread_dia`, `thread_len`, `stack_t`.
  - **Strap Bore** (`socket`, internal) — the punched hole the barrel passes through,
    defined by `post_dia`, `stack_t`, `head_dia`.

This is **point-fixed** hardware: it passes through a punched hole, it is not sewn along an
edge, so it declares no flange interface. Its shelf siblings `strap-end-tip` and
`kiss-lock-frame` carry the flange interfaces instead.

## Fashion Cabinet bridge

Consumed by FC's **adjustable shoulder strap**, **watch band**, **belt keeper**, **knife
sheath** and **collar-and-lead** garments — anything where a strap must be taken in or let
out after the fact rather than riveted once.

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "chicago-screw",
  "linked": true,
  "params_map": {
    "head_dia": "strap_hole_dia_mm * 2.0",
    "head_t": "2.0",
    "post_dia": "strap_hole_dia_mm - 0.3",
    "stack_t": "strap_thickness_mm * strap_ply_count",
    "thread_dia": "max(strap_hole_dia_mm - 2.0, 2.0)",
    "thread_len": "strap_thickness_mm * strap_ply_count - 0.8",
    "slot_w": "1.2"
  }
}
```

The handshake runs through **`strap_bore`**: FC drives its punched hole diameter into
`post_dia` and its ply stack into `stack_t`, and the barrel and shank lengths fall out of
that automatically — so a strap re-drafted from 2 plies to 3 gets a longer screw without
anyone touching the hardware parameters by hand.

`CERN-OHL-W-2.0`.
