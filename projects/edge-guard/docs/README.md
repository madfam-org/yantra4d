# Edge Guard

Child-safety corner and edge guards that clip onto the edge of a table, counter, or shelf
to cushion sharp corners and edges. Each guard is a C-clip that grips the edge thickness
with a rounded outer cushion presented to the room. Sized by the edge thickness so it
snaps onto whatever furniture is in the home.

> **Catalog object #200** — the capstone that closes the Open Commons of Hyperobjects.

## Modes / Parts

| Mode | Part id | What it is |
|------|---------|------------|
| Corner Guard | `corner_guard` | An L-shaped cap: two clip channels at 90° with a rounded corner bumper. |
| Edge Strip | `edge_strip` | A straight run of clip channel + rounded cushion for a long edge. |
| Cushion Bumper | `cushion_bumper` | A stick-on domed pad (no clip) for a flat face or a too-thick edge. |

## Key Parameters

- **Edge Thickness** — the furniture edge the clip grips (drives the clip slot).
- **Grip Depth** — how far the clip reaches onto the top/bottom face.
- **Clip Fit** — slot clearance so the guard slips on.
- **Cushion Thickness** — the rounded cushion depth in front of the edge.
- **Wall Thickness** — guard wall.
- **Length / Corner Arm** — edge-strip length and corner-guard arm length.

## How It Builds (watertight & fast)

Each guard is a prismatic C-section: a solid block with a `edge_t + fit` slot cut `grip`
deep, walled on the back and both grip legs, with the front outer edges **filleted into a
soft cushion**. The corner guard unions two runs at 90° plus a rounded corner filler so the
pointed table corner is fully covered. The bumper is a domed pad, flat on its adhesive back.
No expensive booleans — every variant exports watertight in a couple of seconds.

## Printing Notes

Print in a flexible filament (TPU) so the clip grips and the cushion actually softens
impacts; a rigid print still protects but is less forgiving. The clip slips over the edge
dry; add a strip of mounting tape inside the channel for a permanent hold, or use the
cushion bumper with adhesive on faces too thick to clip. Tune Clip Fit to your printer so
the guard snaps on firmly without splitting.

## Hyperobject Profile

- **Domain:** household (child safety).
- **CDG interface:** `edge_guard` (`profile`) — the C-clip cross-section that hugs the
  furniture edge, standard `internal`, driven by `edge_t`, `grip`, `fit`, `cushion`.
- **Material awareness:** tolerance-by-material (clip fit and softness tuned per filament; TPU cushions best).
- **Commons license:** CERN-OHL-W-2.0.
- **Societal benefit:** cushions sharp furniture corners and edges so a home is safer for
  small children and everyone — a printable guard sized to the exact edge, closing the Open
  Commons of Hyperobjects with the most human of objects: one that keeps a child from getting hurt.
