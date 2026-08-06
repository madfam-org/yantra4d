# Locker Latch

Positive latches for RV and boat cabinet doors that stay shut under motion — a cammed
or sprung catch, not a friction magnet. The body screws to the frame; a hooked catch
engages the door so vibration and heel can't pop it open.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Quarter-Turn Cam | `cam_latch` | A bored square-drive hub with a cam finger that sweeps behind a strike. |
| Snap Spring Latch | `spring_latch` | A hooked catch on a printed cantilever beam that snaps over the door. |
| Push Catch | `push_latch` | A low-profile ramped nib on a short flexure the door drops behind. |

## Key Parameters

- **Door Gap** — space between the door edge and the frame.
- **Catch Engagement** — how deep the hook grabs behind the door / strike.
- **Body Width / Height / Base Thickness** — the mounting body envelope.
- **Spindle Bore / Cam Reach** — cam-latch square drive and finger sweep.
- **Spring Beam** — cantilever/flexure thickness; thinner flexes more easily.

## Printing Notes

Print in PETG or nylon for a fatigue-resistant living hinge on the spring and push
latches; orient the beam so its layers run along its length. The cam latch takes a
square spindle (printed knob or metal rod). All three screw to the cabinet frame.

## Hyperobject Profile

- **Domain:** hybrid (marine / RV cabinetry).
- **CDG interface:** `door_edge_catch` (`snap`) — the sprung/cammed engagement that grabs
  the door edge, standard `internal`, driven by `door_gap`, `catch_hook`, `spring_t`.
- **Material awareness:** tolerance-by-material (beam stiffness and snap force vary by filament).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** keeps cabinets and lockers shut through vibration, heel, and rough
  roads — a printable positive latch that replaces failed magnetic catches on any moving home.
