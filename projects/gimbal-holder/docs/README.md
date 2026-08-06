# Gimbal Holder

A self-leveling drink or bottle holder for a boat or RV. The vessel sits in a cup that
pivots inside nested rings, so it stays upright as the vehicle rolls. Print-in-place:
rings and cup are separate closed bodies with pivot clearance and pop free off the bed.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| 2-Axis Gimbal Cup | `gimbal_cup` | Base frame + outer ring + inner cup, all print-in-place. |
| Single-Axis Rocker | `single_axis` | Base frame + a cup that swings on one axis (no middle ring). |
| Wall-Mount Gimbal | `wall_gimbal` | A vertical bulkhead plate carrying a 2-axis gimbal cup. |

## Key Parameters

- **Vessel Diameter / Cup Height** — sized to the cup or bottle you hold.
- **Wall Thickness** — cup and ring walls.
- **Pivot Clearance** — gap around each pin; larger frees the print-in-place motion.
- **Ring Gap** — radial gap between nested bodies.
- **Pivot Pin Diameter** — trunnion size.
- **Base Diameter / Thickness** — the mounting base.

## Print-in-Place & Watertight Notes

Each moving body — base frame, outer ring, cup — is a **fully closed solid**; the pins
keep a `pivot_gap` clearance to the ring they turn in, so the bodies never touch. The
export is therefore a set of disjoint closed manifolds, which is **watertight**, and the
gaps let the gimbal move straight off the plate with no assembly. A subtle detail: every
pin and socket roots in a small rectangular boss so the cylinder fuses to a flat face
(cylinder-to-shell fuses tessellate non-manifold). Print at 0.2 mm; keep `pivot_gap` at
0.5–0.7 mm for most printers. The cup has a drain hole so rain runs out.

## Hyperobject Profile

- **Domain:** hybrid (marine / RV mobile living).
- **CDG interfaces:**
  - `gimbal_pivot` (`socket`) — the trunnion pin/socket pivot, standard `internal`, driven by `pin_dia`, `pivot_gap`, `ring_gap`.
  - `vessel_cup_bore` (`socket`) — the cup that receives the vessel (`internal`), driven by `vessel_dia`, `cup_h`, `wall`.
- **Material awareness:** tolerance-by-material (pivot clearance tuned per filament for free motion).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** keeps a drink upright on rough water or road without spills — a
  print-in-place self-leveling holder anyone can make to fit their own cup.
