# Strain Relief

Strain reliefs and bend limiters for cable exits: they clamp the cable and spread the bend
load where it leaves a plug, enclosure, or panel, so the conductors don't fatigue and snap.
Sized by cable diameter and a panel or mount interface.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Snap-In Grommet | `grommet_relief` | A panel bushing with a flange + snap ridge and a strain-rib cable bore. |
| Saddle Clamp | `clamp_relief` | A two-screw saddle that pinches the cable against a foot (cordgrip). |
| Bend Limiter | `bend_limiter` | A flexible ribbed sleeve that enforces a minimum bend radius. |

## Key Parameters

- **Cable Diameter / Grip** — cable size and bore undersize for jacket grip.
- **Wall Thickness** — body wall.
- **Panel Hole / Panel Thickness** — the grommet's snap-in panel interface.
- **Bolt Clearance** — saddle-clamp screw holes.
- **Min Bend Radius / Rib Count** — the bend limiter's enforced radius and flex ribs.

## How It Builds (watertight & fast)

Every part avoids OCC's slow operations. Annular features (grommet barrel, bend-limiter
ribs) use **annular-cross-section extrudes** and short **tube unions**, not cuts between
two lofted solids. The bend limiter is a **stack of annular tubes** (a loft through
sharply-alternating rib/neck radii is far too slow), with the rib count auto-capped for
speed. All variants export watertight in under 15 s.

## Printing Notes

Print the bend limiter and grommet in a flexible filament (TPU) so they actually flex; the
saddle clamp can be rigid PLA/PETG. The grommet snaps into a round panel hole; the saddle
clamp bolts down over the cable; the bend limiter slides onto the cable at the exit and
bonds to the strain point at its collar.

## Hyperobject Profile

- **Domain:** industrial (electrical / cable management).
- **CDG interface:** `cable_strain_relief` (`snap`) — the cable grip bore plus snap-in panel
  interface, standard `internal`, driven by `cable_dia`, `grip`, `panel_hole`, `panel_t`.
- **Material awareness:** tolerance-by-material (grip and snap tuned per filament; TPU flexes).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** stops cables from failing at the exit — a printable strain relief and
  bend limiter sized to the exact cable, keeping tools, chargers, and equipment out of the landfill.
