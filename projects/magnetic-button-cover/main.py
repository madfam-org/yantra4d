"""Magnetic Button Cover — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part adaptive conversion that turns an existing buttoned garment into a magnetic
one without unpicking a single button: a CAP that snaps over the sew-through button already
on the shirt, and a magnet carrier PLATE sewn behind the buttonhole side. The button stays
where it is and still looks like a button; the placket now closes by bringing two magnets
together, which a hand with arthritis, tremor, hemiparesis or one working side can do.

Why this shape and not a magnetic button: replacing the buttons means unpicking and
resewing every one, and the garment is then permanently altered — a problem when the
garment is a uniform, a school shirt, or something borrowed or inherited. A cap that snaps
on is reversible in seconds and can move to the next shirt.

Magnet sizing: adaptive closures use N42-N52 neodymium discs. 6x2 mm holds a shirt placket,
8x3 mm a jacket, 10x3 mm a coat. `magnet_dia` and `magnet_t` are the disc's real
dimensions; the pockets are cut with a press-fit allowance and open DOWNWARD so they drain
and print without a bridge, and so the magnet is dropped in from the open side and captured
by the mating part rather than glued into a blind hole.

Modes (dispatched via `target_part`):
  * "cap"   — the snap-on cap that covers the existing button.
  * "plate" — the sew-on magnet carrier plate with its perimeter sew-hole ring.
  * "set"   — one of each, laid out for printing together.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `button_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
button_dia  = float(PARAM(lambda: button_dia,  11.0))  # existing button diameter (mm)
button_t    = float(PARAM(lambda: button_t,     2.2))  # existing button thickness (mm)
magnet_dia  = float(PARAM(lambda: magnet_dia,   6.0))  # disc magnet diameter (mm)
magnet_t    = float(PARAM(lambda: magnet_t,     2.0))  # disc magnet thickness (mm)
wall        = float(PARAM(lambda: wall,         1.4))  # working wall thickness (mm)
snap_lip    = float(PARAM(lambda: snap_lip,     0.7))  # cap retaining lip depth (mm)
sew_holes   = int(  PARAM(lambda: sew_holes,      6))  # sew holes around the plate
hole_dia    = float(PARAM(lambda: hole_dia,     1.6))  # sew hole diameter (mm)
magnet_fit  = float(PARAM(lambda: magnet_fit,   0.15))  # magnet pocket clearance (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # cap|plate|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
button_dia = max(7.0, min(button_dia, 40.0))
button_t   = max(1.0, min(button_t, 8.0))
magnet_dia = max(3.0, min(magnet_dia, 25.0))
magnet_t   = max(1.0, min(magnet_t, 8.0))
wall       = max(0.8, min(wall, 4.0))
snap_lip   = max(0.2, min(snap_lip, 2.0))
sew_holes  = max(0, min(sew_holes, 16))
hole_dia   = max(0.8, min(hole_dia, 3.0))
magnet_fit = max(0.0, min(magnet_fit, 0.5))

# The magnet must fit inside the button it hides behind, with wall around it.
magnet_dia = min(magnet_dia, max(2.0, button_dia - 2.0 * wall - 1.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
pocket_dia = magnet_dia + magnet_fit
# CAP: an outer shell whose bore takes the button, with the magnet pocket in its crown.
cap_bore = button_dia + 0.4                      # running clearance over the button
cap_od = cap_bore + 2.0 * wall
cap_socket_h = button_t + 0.3                    # depth of the button socket
cap_h = cap_socket_h + magnet_t + wall           # total cap height
# The retaining lip is a shoulder that steps the bore in at the open mouth.
lip_bore = max(2.0, cap_bore - 2.0 * snap_lip)
lip_h = min(max(0.5, button_t * 0.35), cap_socket_h * 0.5)
# PLATE: a flat disc carrying the mating magnet and a perimeter sew ring.
plate_od = cap_od
plate_h = magnet_t + wall
sew_r = max(pocket_dia / 2.0 + hole_dia / 2.0 + 0.8,
            plate_od / 2.0 - max(hole_dia * 0.6 + 1.0, 2.0))
hole_dia = min(hole_dia, max(0.6, (plate_od / 2.0 - sew_r) * 1.6))


def _pt(r, a):
    """Polar to cartesian on XY."""
    return (r * math.cos(a), r * math.sin(a))


def _magnet_pocket(depth_from_z0, extra=0.0):
    """A magnet pocket opening DOWNWARD from z = 0, so it drains and needs no bridge.

    The cutter overshoots below z = 0 so the opening is never a coincident face.
    """
    return (
        cq.Workplane("XY")
        .circle(pocket_dia / 2.0)
        .extrude(depth_from_z0 + 3.0 + extra)
        .translate((0, 0, -3.0))
    )


def build_cap():
    """The snap-on cap: a shell whose bore swallows the button, magnet pocket in the crown.

    Built face-up: the visible crown is the top, the open mouth faces -Z. The button socket,
    the retaining lip step and the magnet pocket are all cut from that same open side, so
    every cavity in the finished part opens downward and drains.
    """
    shell = cq.Workplane("XY").circle(cap_od / 2.0).extrude(cap_h)
    # Soften the crown rim on the clean blank, before any cavity is cut.
    try:
        shell = shell.edges(">Z").fillet(min(wall * 0.7, cap_h * 0.25, 1.2))
    except Exception:
        pass
    # Button socket, cut in two steps so the mouth is narrower than the chamber behind it.
    # Above the lip: the full bore the button body sits in.
    lip_relief = (
        cq.Workplane("XY")
        .circle(cap_bore / 2.0)
        .extrude(cap_socket_h - lip_h + 0.01)
        .translate((0, 0, lip_h))
    )
    # At the mouth: a narrower bore. What is left between them IS the retaining lip, so the
    # cap has to spring over the button's rim and stays put once it is on.
    mouth = (
        cq.Workplane("XY")
        .circle(lip_bore / 2.0)
        .extrude(lip_h + 3.0)
        .translate((0, 0, -3.0))
    )
    body = shell.cut(lip_relief).cut(mouth)
    # Lead-in chamfer at the mouth so the cap starts onto the button without a fight.
    lead = min(snap_lip * 0.9, lip_h * 0.8)
    if lead > 0.05:
        entry = (
            cq.Workplane("XY")
            .circle(lip_bore / 2.0 + lead)
            .workplane(offset=lead + 0.2)
            .circle(lip_bore / 2.0)
            .loft(ruled=True)
            .translate((0, 0, -0.1))
        )
        body = body.cut(entry)
    # Magnet pocket in the crown, opening downward into the button socket.
    body = body.cut(_magnet_pocket(cap_socket_h + magnet_t))
    return body


def build_plate():
    """The sew-on carrier plate: a flat disc, magnet pocket down, sew-hole ring around it.

    The pocket opens downward — toward the placket's inside face — so the sewn plate traps
    the magnet against the fabric and nothing has to be glued into a blind hole.
    """
    disc = cq.Workplane("XY").circle(plate_od / 2.0).extrude(plate_h)
    try:
        disc = disc.edges(">Z").chamfer(min(wall * 0.4, plate_h * 0.25, 0.6))
    except Exception:
        pass
    body = disc.cut(_magnet_pocket(magnet_t))
    if sew_holes > 0:
        pts = [_pt(sew_r, 2.0 * math.pi * i / sew_holes + math.pi / 6.0)
               for i in range(sew_holes)]
        holes = (
            cq.Workplane("XY")
            .pushPoints(pts)
            .circle(hole_dia / 2.0)
            .extrude(plate_h + 6.0)
            .translate((0, 0, -3.0))
        )
        body = body.cut(holes)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cap":
    result = build_cap()
elif target_part == "plate":
    result = build_plate()
else:
    gap = max(4.0, cap_od * 0.25)
    off = (cap_od + plate_od) / 4.0 + gap / 2.0
    asm = cq.Assembly()
    asm.add(build_cap().translate((-off, 0, 0)), name="cap", color=cq.Color("#8f8f9f"))
    asm.add(build_plate().translate((off, 0, 0)), name="plate", color=cq.Color("#7f7f8f"))
    result = asm
