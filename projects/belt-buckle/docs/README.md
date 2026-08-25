# Belt Buckle

The printable **center-bar belt buckle** — generated with **CadQuery** (B-Rep).
A rounded frame, a bar across its middle, and a prong that curls around that bar
and drops into a punched belt hole. Fashion Cabinet's `belt-buckle` notion owns
the fashion semantics (strap placement, hole spacing) and bridges to **this**
solid for the hardware.

This is the buckle kilts, belted coats and waistcoat cinches need. The sibling
`strap-buckle` cartridge covers **webbing** hardware instead (side-release,
ladder-lock, tri-glide) — pick that one for packs and slings, this one for belts.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Frame + Prong** | `set` | Both pieces laid side by side with a print gap — two separate solids on one plate. |
| **Frame Only** | `frame` | The frame ring plus its center bar (and the roller sleeve if enabled). |
| **Prong Only** | `prong` | The prong: curl, shaft, tapered tip. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Strap | `strap_width` | 32 mm | Finished belt width. Frame interior = this + 1.5 mm pass-through allowance. |
| Frame | `frame_t` | 3.5 mm | Frame rod thickness. Heavier reads as chunkier hardware and prints stronger. |
| Frame | `bar_dia` | 3.0 mm | Center bar diameter. The prong curl is sized to this + 0.45 mm running clearance. |
| Frame | `corner_r` | 4.0 mm | Frame opening corner radius. Clamped to `strap_width / 3` so the opening never closes. |
| Frame | `roller` | off | Swap the outer frame side for a fatter smooth sleeve. |
| Prong | `prong_d` | 3.0 mm | Prong shaft diameter — must be smaller than the punched belt hole. |

## Presets

- **Default** — 32 mm belt.
- **Kilt Strap** — 50 mm, heavy section.
- **Waistcoat Cinch** — 18 mm, fine section.
- **Roller Frame** — 40 mm belted coat with the roller sleeve.

## About the roller

`roller` thickens the outer frame side into a smooth cylindrical sleeve, which
reduces strap wear at the bearing edge. **The sleeve is fused to the frame — it
does not spin.** A genuinely free-spinning roller is a separate loose part
captured on the bar; it cannot be expressed as one watertight solid, so it is out
of scope for a single-body print. If you need a true roller, print the frame with
`roller` off and slip a cut tube over the outer bar during assembly.

## Print notes

Print **flat on the bed** — the frame lies in the XY plane and the prong lies on
its side, both self-supporting with no bridging. PETG or PLA-with-higher-infill
suits a light garment cinch; a load-bearing belt wants a tough filament (PETG,
ASA, nylon) at high perimeter count, since the prong root and the center bar are
the stress path. Print the `set` mode to get both pieces in one job — they are
laid out with a real gap and export as two separate bodies.

Every mode exports as a watertight solid. The prong tip is a loft to a small flat
circle (not a point) and the curl is a trimmed torus (not a swept arc), both
deliberate choices that keep the mesh clean.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Strap Slot** (`rail`, internal) — the frame opening the strap passes
    through, defined by `strap_width`, `frame_t`.
  - **Prong Seat** (`snap`, internal) — the curl-on-bar engagement, defined by
    `prong_d`, `bar_dia`.
  - **Strap Anchor Flange** (`flange`, internal) — **the sewn/set flange for the
    dimensional handshake**: the center bar the strap end folds over and is
    stitched or riveted back onto. Defined by `strap_width`, `bar_dia`,
    `frame_t`.

## Fashion Cabinet bridge

FC-side `hardware_ref` block on the `belt-buckle` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "belt-buckle",
      "linked": true,
      "params_map": {
        "strap_width": "belt_width_mm",
        "frame_t": "belt_width_mm * 0.11",
        "bar_dia": "belt_thickness_mm * 1.4",
        "prong_d": "min(belt_hole_dia_mm - 0.6, 5.0)",
        "corner_r": "belt_width_mm * 0.125"
      }
    }
  }
}
```

The garment drives the hardware: a finished belt width sets the frame opening via
`strap_width`, and the punched hole diameter caps `prong_d` so the prong always
drops through. `strap_anchor_flange` is the interface FC uses for the dimensional
handshake when placing the strap end.
