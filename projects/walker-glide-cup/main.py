"""
Walker Glide Cup — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The front feet of a walker do NOT grip — they slide. A glide cup presses onto
the front leg tube and presents a broad, smooth, low-friction dome that skates
over vinyl, tile, and low-pile carpet instead of catching on it. It is a
different part from `mobility-tip`, which is deliberately a GRIP tip for the
rear legs; the two share the leg-tube socket series and nothing else.

The WEAR FACE is the point: it is the surface that abrades away, so its
thickness is a published parameter, not a hidden constant. Print a thicker
wear face for a heavy user or a rough floor and reprint when it thins.

Modes:
  - glide_cup  : the domed sliding cup — the front-leg standard.
  - tennis_cup : the same socket carrying a hemispherical seat that takes a
                 tennis ball, the classic improvised glide.
  - glide_disc : a flat, wide disc for deep carpet where a dome digs in.

Watertight strategy: every body is ONE solid. The leg socket is a single blind
bore that ALWAYS leaves a floor beneath it (floor thickness is enforced by a
clamp, not by hope); the dome is a revolved profile unioned coaxially; the ball
seat is a single sphere cut that is clamped so it can never reach the socket
floor. No shelling, no lofted surfaces.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

A printable mobility AID for personal use, not a certified medical device.
A glide that slips is a fall risk: test on YOUR floor, under YOUR weight,
before relying on it, and replace it when the wear face is thin.
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
target_part = str(PARAM(lambda: target_part, "glide_cup"))
# "glide_cup" | "tennis_cup" | "glide_disc"

tube_dia   = float(PARAM(lambda: tube_dia,  25.0))  # walker leg tube OUTER diameter
clearance  = float(PARAM(lambda: clearance,  0.35)) # per-side press-fit gap
wall       = float(PARAM(lambda: wall,       3.2))  # socket wall thickness
socket_h   = float(PARAM(lambda: socket_h,  30.0))  # leg seating depth
wear_th    = float(PARAM(lambda: wear_th,    6.0))  # WEAR FACE thickness — the consumable
glide_dia  = float(PARAM(lambda: glide_dia, 58.0))  # sliding face diameter
dome_rise  = float(PARAM(lambda: dome_rise,  7.0))  # how far the dome bulges
ball_dia   = float(PARAM(lambda: ball_dia,  67.0))  # tennis ball diameter (tennis_cup)
rim_th     = float(PARAM(lambda: rim_th,     3.0))  # rim wall around the ball seat

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_dia  = max(10.0, min(tube_dia, 50.0))
clearance = max(0.0,  min(clearance, 2.0))
wall      = max(2.0,  min(wall, 10.0))
socket_h  = max(10.0, min(socket_h, 70.0))
wear_th   = max(2.0,  min(wear_th, 25.0))
glide_dia = max(20.0, min(glide_dia, 140.0))
dome_rise = max(0.0,  min(dome_rise, 40.0))
ball_dia  = max(30.0, min(ball_dia, 120.0))
rim_th    = max(1.5,  min(rim_th, 12.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
R_BORE = tube_dia / 2.0 + clearance
R_SOCK = R_BORE + wall                     # socket outer radius
# The glide face must always be wider than the socket it carries.
R_GLIDE = max(glide_dia / 2.0, R_SOCK + 3.0)
# Dome rise capped so the revolved arc is always a valid, non-degenerate cap.
RISE = min(dome_rise, R_GLIDE * 0.85)
RISE = max(0.0, RISE)


# ── Helpers ──────────────────────────────────────────────────────────────────
def leg_socket(z0):
    """Socket cylinder rising from z0 with a blind bore. `wear_th` of material
    always remains beneath the bore — that IS the wear face."""
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(R_SOCK)
        .extrude(socket_h)
    )
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(R_BORE)
        .extrude(socket_h + 1.0)
    )
    return body.cut(bore)


def dome_solid():
    """The sliding dome: a revolved profile from the glide radius at Z=0 up to
    the apex at Z=RISE. Built as a closed polyline with a straight base so the
    revolve is always a valid solid even when RISE == 0."""
    if RISE < 0.05:
        return cq.Workplane("XY").circle(R_GLIDE).extrude(wear_th)
    # Profile in the XZ half-plane, already positioned with its ground face at
    # Z = 0 (no post-revolve translate — that is where the off-by-wear_th bugs
    # live). The contact land sits at Z = 0, the shoulder at Z = RISE, and the
    # flat top land at Z = RISE + wear_th.
    #   r = FLAT_R   → z = 0            (contact land, touches the floor)
    #   r = R_GLIDE  → z = RISE         (shoulder)
    #   then straight up by wear_th and back to the axis.
    #
    # FLAT_R is why this profile does not start on the axis. A revolved profile
    # whose first point sits exactly at r = 0 sweeps a POLE SINGULARITY: OCCT
    # keeps it as one valid solid, but the tessellator emits a torn cap, so the
    # exported mesh is a non-watertight TWO-body soup while `.solids()` still
    # reports 1. Giving the apex a small flat land instead of a point removes
    # the degenerate vertex; the land is far too small to change how the cup
    # slides, and the floor contact is a land in real use anyway.
    FLAT_R = max(0.4, min(R_GLIDE * 0.04, 1.5))
    pts = [(FLAT_R, 0.0)]
    n = 18
    for i in range(1, n + 1):
        t = i / float(n)
        r = FLAT_R + (R_GLIDE - FLAT_R) * math.sin(t * math.pi / 2.0)
        z = RISE * (1.0 - math.cos(t * math.pi / 2.0))
        pts.append((r, z))
    pts.append((R_GLIDE, RISE + wear_th))
    pts.append((0.0, RISE + wear_th))
    pts.append((0.0, 0.0))
    prof = cq.Workplane("XZ").polyline(pts).close()
    return prof.revolve(360.0, (0, 0, 0), (0, 1, 0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_glide_cup():
    """Domed sliding face carrying the leg socket on top."""
    dome = dome_solid()
    # dome_solid()'s top land sits at Z = RISE + wear_th (or wear_th when flat).
    z_top = wear_th + RISE
    body = dome.union(leg_socket(z_top - 0.4))   # 0.4 mm overlap = one body
    if RISE < 0.05:
        # Flat variant: soften the ground edge so it does not catch a threshold.
        try:
            body = body.faces("<Z").edges().chamfer(min(1.2, wear_th * 0.35))
        except Exception:
            pass
    return body


def build_glide_disc():
    """Flat wide disc for deep carpet — no dome, a rounded rim instead."""
    body = cq.Workplane("XY").circle(R_GLIDE).extrude(wear_th)
    body = body.union(leg_socket(wear_th - 0.4))
    fr = min(wear_th * 0.4, R_GLIDE * 0.1, 3.0)
    if fr > 0.15:
        try:
            body = body.faces("<Z").edges().fillet(fr)
        except Exception:
            pass
    return body


def seat_cutter(R, depth, exit_h):
    """A spherical ball seat of `depth`, as a SOLID OF REVOLUTION whose bottom is
    a small flat land and whose top continues as a cylinder for `exit_h`.

    Two degeneracies are deliberately designed out here, and both were observed
    as real failures before this shape was adopted:

      1. A `cq.Workplane.sphere()` cut grazes the body instead of clearing it,
         leaving a ZERO-VOLUME sliver at the tangency. OCCT keeps the result as
         one solid, but the exported mesh is two bodies and non-watertight.
      2. A revolved profile that touches the axis (r = 0) sweeps a POLE
         SINGULARITY, which tessellates into a torn cap for the same reason.

    So the profile starts at a small flat radius, never at the axis, and the
    cutter is extended straight up past the top face so it EXITS cleanly rather
    than ending tangent to it.

    Returned with the seat rim at z = 0; the caller translates it to the face."""
    n = 20
    flat = max(0.4, R * 0.03)
    pts = [(0.0, -depth), (flat, -depth)]
    for i in range(1, n + 1):
        z = -depth + depth * (i / float(n))
        dz = z - (R - depth)          # height above the sphere centre
        r = math.sqrt(max(0.0, R * R - dz * dz))
        pts.append((max(r, flat), z))
    r_rim = pts[-1][0]
    pts.append((r_rim, exit_h))
    pts.append((0.0, exit_h))
    prof = cq.Workplane("XZ").polyline(pts).close()
    return prof.revolve(360.0, (0, 0, 0), (0, 1, 0))


def build_tennis_cup():
    """Socket over a hemispherical seat that grips a tennis ball.

    The seat is one revolved cut. Its depth is clamped so the cut can never
    reach the socket floor, and the body radius is clamped to always contain the
    seat rim plus `rim_th`, so the cut can never sever the sides."""
    R_BALL = ball_dia / 2.0
    # Seat depth: how far the ball sinks in. Past the equator so it is retained,
    # but never so deep that the seat eats the wear face beneath it.
    seat_h = min(R_BALL * 0.55, R_BALL * 0.95)
    # The seat rim radius at the cut plane, from the sphere equation.
    dz_rim = R_BALL - seat_h
    r_rim = math.sqrt(max(0.0, R_BALL * R_BALL - dz_rim * dz_rim))
    # Body radius MUST contain the rim plus a real wall, or the seat cuts out
    # through the sides and the part falls into pieces.
    r_body = max(R_GLIDE, r_rim + rim_th, R_SOCK + 2.0)
    body_h = seat_h + wear_th
    body = cq.Workplane("XY").circle(r_body).extrude(body_h)
    body = body.union(leg_socket(body_h - 0.4))
    # Cut the seat from the top face, exiting past the top of the socket.
    cutter = seat_cutter(R_BALL, seat_h, socket_h + wear_th + 10.0)
    body = body.cut(cutter.translate((0.0, 0.0, body_h)))
    try:
        body = body.faces("<Z").edges().chamfer(min(1.2, wear_th * 0.35))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tennis_cup":
    result = build_tennis_cup()
elif target_part == "glide_disc":
    result = build_glide_disc()
else:  # "glide_cup"
    result = build_glide_cup()
