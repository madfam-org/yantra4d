# Solar Panel Mount

Brackets and tilt legs for framed solar panels on a boat, RV, van, or ground setup. A
corner bracket clamps the panel's aluminium edge frame and bolts down, a tilt leg props
the panel at a chosen angle, and a low-profile Z-bracket fixes it flat to a roof. Sized
by the panel edge (frame) thickness to fit common 25–40 mm frames.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Corner Bracket | `corner_bracket` | An L-corner cap gripping two panel edges, bolted to a surface. |
| Tilt Leg | `tilt_leg` | A foot + angled strut ending in an edge clip that grabs the frame. |
| Z-Bracket | `z_bracket` | A low-profile Z mount that bolts flat and clamps the frame edge. |

## Key Parameters

- **Frame Thickness** — the panel's aluminium edge frame thickness.
- **Grip Depth** — how far the cap wraps over the panel face.
- **Frame Fit** — clearance so the frame slides into the grip.
- **Wall Thickness / Bolt Clearance** — bracket body and mounting hole.
- **Strut Length / Tilt Angle** — tilt-leg lift and prop angle (aim at the sun).

## Printing Notes

Print in ASA or PETG for UV stability outdoors; PLA will creep in the sun. Orient the
tilt strut so its layers run along its length for strength. Bolt the corner brackets and
Z-brackets through the foot with stainless hardware and use a rubber pad against the
panel frame to spread the clamp load.

## Hyperobject Profile

- **Domain:** hybrid (marine / RV / van / ground solar).
- **CDG interfaces:**
  - `panel_edge_grip` (`profile`) — the C-channel that hugs the panel frame edge, standard `internal`, driven by `edge_t`, `grip_depth`, `fit`, `wall`.
  - `surface_bolt_pattern` (`bolt_pattern`) — the bolt-down foot (`internal`), driven by `bolt_dia`, `wall`.
- **Material awareness:** tolerance-by-material (frame fit tuned per filament; ASA/PETG for UV).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** mounts and tilts off-grid solar with printable brackets sized to
  the panel on hand, cutting the cost of proprietary racking for boats, vans, and RVs.
