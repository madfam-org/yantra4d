"""
Yarn / Cone Guide — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Guides and tensioners that feed yarn smoothly off a cone or ball for knitting,
crochet and weaving. The functional interface is a cone-base SOCKET (a shallow
tapered seat the cone sits in) plus an EYELET (the smooth-lipped hole the yarn
passes through so it can't snag).

Modes:
  - cone_stand   : a cone base seat on a foot with a tall arm carrying a top
    eyelet, so yarn draws off the cone tip and up through the eyelet.
  - tension_gate : a flat wall/table plate with a row of eyelets and a pinch
    slot — thread the yarn through the eyelets for even feed tension.
  - table_eyelet : a single low bracket with one large flared eyelet, clamped
    at a table edge, that redirects yarn without friction.

Watertight strategy:
  The cone seat is a shallow blind pocket bored from the OPEN top face (vented).
  Eyelets are through-holes with a chamfered lip (open both ends). The arm is a
  solid post unioned into the foot with a small embed. No hollow-on-solid
  cavities. Blanks are fillet-cleaned BEFORE feature cuts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cone_stand"))
# "cone_stand" | "tension_gate" | "table_eyelet"

base_dia   = float(PARAM(lambda: base_dia, 50.0))    # yarn-cone base diameter (mm)
taper      = float(PARAM(lambda: taper, 6.0))        # cone wall taper (deg from vertical)
eyelet_d   = float(PARAM(lambda: eyelet_d, 8.0))     # yarn eyelet bore (mm)
arm_h      = float(PARAM(lambda: arm_h, 90.0))       # cone-stand arm height (mm)
wall       = float(PARAM(lambda: wall, 4.0))         # plate / seat wall thickness
eyelets    = int(PARAM(lambda: eyelets, 4))          # eyelets on the tension gate

# Clamp to sane ranges so extreme UI values still build watertight.
base_dia = max(25.0, min(base_dia, 120.0))
taper    = max(0.0, min(taper, 20.0))
eyelet_d = max(3.0, min(eyelet_d, 20.0))
arm_h    = max(40.0, min(arm_h, 160.0))
wall     = max(2.5, min(wall, 10.0))
eyelets  = max(1, min(eyelets, 8))


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _disc(radius, th, fillet_r=2.0):
    """A round base disc, fillet-cleaned before feature cuts."""
    d = cq.Workplane("XY").circle(radius).extrude(th)
    try:
        d = d.edges("|Z or >Z").fillet(fillet_r)
    except Exception:
        try:
            d = d.edges(">Z").fillet(fillet_r)
        except Exception:
            pass
    return d


def _eyelet_cut(bore_r, z_center, depth):
    """A through-eyelet bore centred at z_center, running along Y (through the
    plate thickness). Returns a horizontal cylinder cutter."""
    return (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, z_center, 0))
        .circle(bore_r)
        .extrude(depth, both=True)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_cone_stand():
    """A cone base seat on a disc foot, with a tall arm rising beside it carrying
    a top eyelet. Yarn draws off the cone tip, up and through the eyelet."""
    seat_r = base_dia / 2.0 + wall
    foot = _disc(seat_r + 3.0, wall + 2.0, 3.0)

    # Shallow tapered cone seat bored from the top (vented, blind pocket).
    seat_depth = min(base_dia * 0.25, wall + 6.0)
    top_r = base_dia / 2.0 + 0.6
    bot_r = max(2.0, top_r - seat_depth * math.tan(math.radians(taper)))
    seat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, (wall + 2.0) - seat_depth))
        .circle(top_r)
        .workplane(offset=seat_depth + 0.5)
        .circle(bot_r)
        .loft(combine=True)
    )
    body = foot.cut(seat)

    # Arm: a solid post at the +X edge, embedded into the foot, curving to centre
    # over the cone via a short cantilever head that carries the eyelet.
    arm_w = wall + 2.0
    arm_x = seat_r + 1.0
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(arm_x, 0, 0))
        .rect(arm_w, arm_w)
        .extrude(arm_h)
    )
    # Cantilever head reaching back over the cone centre.
    head_len = arm_x + 2.0
    head = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(arm_x / 2.0, 0, arm_h - arm_w))
        .box(head_len, arm_w, arm_w, centered=(True, True, False))
    )
    body = body.union(post).union(head)

    # Eyelet through the head, over the cone centre, bored down through the head.
    er = max(1.0, eyelet_d / 2.0)
    eye = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, arm_h - arm_w - 1.0))
        .circle(er)
        .extrude(arm_w + 2.0)
    )
    body = body.cut(eye)
    # Chamfer the eyelet lip so yarn doesn't abrade (top face of head).
    try:
        body = body.faces(">Z").edges(cq.NearestToPointSelector((0, 0, arm_h))).chamfer(min(er * 0.5, 1.0))
    except Exception:
        pass
    return body


def build_tension_gate():
    """A flat plate (mounts on a wall or table edge) with a row of eyelets and a
    pinch slot; threading the yarn through the eyelets evens the feed tension."""
    er = max(1.0, eyelet_d / 2.0)
    pitch = eyelet_d + 8.0
    plate_w = pitch * eyelets + 10.0
    plate_h = eyelet_d + 18.0
    plate = cq.Workplane("XY").box(plate_w, wall, plate_h, centered=(True, True, True))
    try:
        plate = plate.edges("|Y").fillet(3.0)
    except Exception:
        pass

    # Row of through-eyelets across the plate (along Y), plus lip chamfers.
    x0 = -(pitch * (eyelets - 1)) / 2.0
    z_eye = plate_h * 0.15
    pts = [(x0 + i * pitch, z_eye) for i in range(eyelets)]
    cutter = (
        cq.Workplane("XZ")
        .pushPoints(pts)
        .circle(er)
        .extrude(wall + 2.0, both=True)
    )
    body = plate.cut(cutter)

    # A pinch/tension slot along the top edge (obround, vented to top).
    slot_len = plate_w * 0.5
    slot = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, plate_h / 2.0 + 0.5, 0))
        .slot2D(slot_len, max(1.6, eyelet_d * 0.35), angle=0)
        .extrude(wall + 2.0, both=True)
    )
    body = body.cut(slot)

    # Two mounting holes near the bottom corners (through the plate).
    mnt_r = 2.2
    mpts = [(-plate_w / 2.0 + 6.0, -plate_h * 0.32), (plate_w / 2.0 - 6.0, -plate_h * 0.32)]
    mcut = (
        cq.Workplane("XZ")
        .pushPoints(mpts)
        .circle(mnt_r)
        .extrude(wall + 2.0, both=True)
    )
    body = body.cut(mcut)
    return body


def build_table_eyelet():
    """A low bracket with one large flared eyelet that redirects yarn off a cone
    at a table edge without friction. The eyelet is a through-hole with a wide
    countersink flare on the entry face."""
    er = max(1.0, eyelet_d / 2.0)
    body_w = eyelet_d + 2.0 * wall + 6.0
    body_h = eyelet_d + 2.0 * wall + 6.0
    depth = wall + 4.0
    body = cq.Workplane("XY").box(body_w, depth, body_h, centered=(True, True, True))
    try:
        body = body.edges("|Y").fillet(4.0)
    except Exception:
        pass

    # Central through-eyelet along Y.
    eye = _eyelet_cut(er, 0.0, depth)
    body = body.cut(eye)
    # Flared entry (a shallow cone countersink) on the +Y face so yarn glides in.
    flare = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, depth / 2.0 + 0.01, 0))
        .circle(er)
        .workplane(offset=-min(depth * 0.5, er * 1.2))
        .circle(er + min(depth * 0.5, er * 1.2))
        .loft(combine=True)
    )
    body = body.cut(flare)

    # A foot lip at the bottom with a mount hole to clamp at the table edge.
    lip = cq.Workplane("XY").box(body_w, depth + 10.0, wall, centered=(True, True, False)).translate((0, 0, -body_h / 2.0))
    body = body.union(lip)
    mnt = cq.Workplane("XY").circle(2.4).extrude(wall + 2.0).translate((0, depth / 2.0 + 4.0, -body_h / 2.0 - 1.0))
    body = body.cut(mnt)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tension_gate":
    result = build_tension_gate()
elif target_part == "table_eyelet":
    result = build_table_eyelet()
else:
    result = build_cone_stand()
