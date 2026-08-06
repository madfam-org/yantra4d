"""
Mobility Tube Tip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Printable replacement tips and holders for the round tubes of canes, crutches,
and walkers. Sized by the outer tube diameter so the socket press-fits the tube;
the ground-contact face carries a concentric tread for grip.

  * "cane_tip"    — a closed tip cup: a socket that caps the tube end with a
                    treaded, chamfered ground face (target_part == "cane_tip").
  * "quad_foot"   — a wide four-lobe base for extra stability, same tube socket
                    on top (target_part == "quad_foot").
  * "clip_holder" — a C-clip that snaps onto the tube to hold it against a wall
                    or table edge (target_part == "clip_holder").

Watertight strategy: every body is one solid; the tube socket is a single blind
bore that always leaves a floor beneath it, the tread is shallow ring grooves
cut into that floor, and the clip is a solid C-ring with one slot removed.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

These are printable mobility AIDS for personal use, not certified medical
devices; verify fit and load before relying on them.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cane_tip"))  # cane_tip | quad_foot | clip_holder

tube_dia   = float(PARAM(lambda: tube_dia,   19.0))   # outer tube diameter (mm)
clearance  = float(PARAM(lambda: clearance,   0.3))   # radial press-fit slop (per side)
wall       = float(PARAM(lambda: wall,        3.0))   # socket wall thickness
socket_h   = float(PARAM(lambda: socket_h,   28.0))   # how deep the tube seats
floor      = float(PARAM(lambda: floor,       5.0))   # ground-contact base thickness
tread      = float(PARAM(lambda: tread,       1.2))   # tread groove depth
foot_dia   = float(PARAM(lambda: foot_dia,   55.0))   # quad-foot base outer diameter

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_dia  = max(8.0,  min(tube_dia, 40.0))
clearance = max(0.0,  min(clearance, 1.5))
wall      = max(2.0,  min(wall, 8.0))
socket_h  = max(10.0, min(socket_h, 60.0))
floor     = max(3.0,  min(floor, 15.0))
tread     = max(0.0,  min(tread, 3.0))

bore_dia  = tube_dia + 2.0 * clearance     # socket inner diameter (press fit)
BORE_R    = bore_dia / 2.0
OUTER_R   = BORE_R + wall                   # socket outer radius
foot_dia  = max(foot_dia, 2.0 * OUTER_R + 6.0)


# ── Helpers ──────────────────────────────────────────────────────────────────
def tube_socket(base_th):
    """A closed cup: solid outer cylinder, blind bore from the top leaving
    `base_th` of floor. Height = base_th + socket_h."""
    total_h = base_th + socket_h
    body = cq.Workplane("XY").circle(OUTER_R).extrude(total_h)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_th))
        .circle(BORE_R)
        .extrude(socket_h + 1.0)
    )
    body = body.cut(bore)
    return body, total_h


def cut_tread(body, face_r):
    """Concentric ring grooves in the bottom ground face for slip resistance.
    Cut as thin annular rings (one boolean each) so the base stays watertight."""
    if tread < 0.05:
        return body
    n = max(1, int(face_r / 4.0))
    for i in range(1, n + 1):
        rr = face_r * i / (n + 0.5)
        ring = (
            cq.Workplane("XY")
            .circle(rr)
            .circle(max(0.4, rr - 1.1))
            .extrude(tread)
            .translate((0, 0, -0.01))
        )
        try:
            body = body.cut(ring)
        except Exception:
            pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_cane_tip():
    """Closed tip cup with a treaded, gently chamfered ground face."""
    body, total_h = tube_socket(floor)
    # Chamfer the bottom outer edge so the tip meets the ground cleanly.
    try:
        body = body.faces("<Z").edges().chamfer(min(1.5, floor * 0.4, wall * 0.5))
    except Exception:
        pass
    body = cut_tread(body, OUTER_R - 1.0)
    return body


def build_quad_foot():
    """A wide four-lobe base disc for stability with the tube socket rising from
    its centre. The base is a central disc unioned with four corner lobes."""
    base_h = floor + 2.0
    fr = foot_dia / 2.0
    base = cq.Workplane("XY").circle(fr * 0.62).extrude(base_h)
    lobe_orbit = fr - fr * 0.34
    for k in range(4):
        ang = math.radians(45.0 + k * 90.0)
        x = lobe_orbit * math.cos(ang)
        y = lobe_orbit * math.sin(ang)
        lobe = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, 0))
            .circle(fr * 0.42)
            .extrude(base_h)
        )
        base = base.union(lobe)
    # Socket on top of the base.
    socket, _sh = tube_socket(floor)
    socket = socket.translate((0, 0, base_h))
    body = base.union(socket)
    # Tread on the underside disc.
    body = cut_tread(body, fr * 0.95)
    try:
        body = body.faces("<Z").edges().chamfer(min(1.5, base_h * 0.3))
    except Exception:
        pass
    return body


def build_clip_holder():
    """An open C-clip that snaps around the tube to hang/park it. A solid ring
    (bore = tube + clearance) with a mouth slot slightly narrower than the tube
    so it grips, plus a small mounting tab."""
    ring_h = max(14.0, socket_h * 0.5)
    clip_or = BORE_R + wall
    ring = cq.Workplane("XY").circle(clip_or).extrude(ring_h)
    bore = cq.Workplane("XY").circle(BORE_R).extrude(ring_h + 2.0).translate((0, 0, -1.0))
    ring = ring.cut(bore)
    # Mouth opening ~85% of diameter so it snaps on and retains.
    mouth = max(2.0, bore_dia * 0.85)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, clip_or, 0))
        .box(mouth, clip_or * 2.2, ring_h + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    ring = ring.cut(slot)
    # Mounting tab on the back with a screw hole.
    tab_w = clip_or * 1.4
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -clip_or - wall * 0.5, 0))
        .box(tab_w, wall * 2.2, ring_h, centered=(True, True, False))
    )
    screw = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -clip_or - wall, ring_h / 2.0))
        .transformed(rotate=cq.Vector(90, 0, 0))
        .circle(2.1)
        .extrude(wall * 4.0)
    )
    body = ring.union(tab).cut(screw)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "quad_foot":
    result = build_quad_foot()
elif target_part == "clip_holder":
    result = build_clip_holder()
else:  # "cane_tip"
    result = build_cane_tip()
