"""
P-Trap / Drain Fitting — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Under-sink tubular drainage parts built to real US slip-joint sizing: tailpiece
extensions, quarter-bend trap arms, and the P-trap U-bend itself. Each part carries
slip-joint sockets so it mates with standard 1-1/4" and 1-1/2" tubular drain tube
using the usual slip nut + beveled washer.

Real dimensions (US tubular drain, expressed in mm):
  - 1-1/4" tube: 1.66" OD = 42.16 mm.
  - 1-1/2" tube: 1.90" OD = 48.26 mm.
  A slip socket here is bored to (tube OD + fit clearance) so the mating tube slides
  in; the slip nut threads onto the outside in the real world (modeled as a plain
  collar so the print stays a clean fitting, not a fragile printed pipe thread).

Watertightness strategy (a real hollow drain path that is still a closed 2-manifold):
  The flow path is swept as a SOLID rod along a genuine centerline wire, then a
  second, thinner rod is swept along the SAME wire and cut away — leaving a hollow
  tube. The path is assembled from explicit edges
  (Edge.makeLine / Edge.makeThreePointArc -> Wire.assembleEdges) so curved runs are
  one continuous multi-edge wire, and the profile disk is placed at the path start
  with its normal along the start tangent (`sweep(..., isFrenet=True,
  transition="round")`). Both open ends are SOCKET CUPS: the bore opens onto the end
  face but is ringed by wall, so every end face is an ANNULUS and the whole surface
  is sealed (an open bare tube would have boundary loops -> not watertight). Sockets
  and the swept core are unioned with real volumetric overlap, never tangent kisses.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math

from cadquery import Edge, Vector, Wire


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Slip-joint tube sizes (mm) ───────────────────────────────────────────────
TUBE_OD = {"1-1/4": 42.16, "1-1/2": 48.26}


def tube_od(name):
    """Slip-joint tube outside diameter (mm), defaulting to 1-1/2\"."""
    return TUBE_OD.get(name, TUBE_OD["1-1/2"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "p_trap"))
tube_size = str(PARAM(lambda: tube_size, "1-1/2"))   # slip tube nominal
wall = float(PARAM(lambda: wall, 3.0))               # pipe wall thickness (mm)
clearance = float(PARAM(lambda: clearance, 0.4))     # slip-fit slop per side (mm)
socket_depth = float(PARAM(lambda: socket_depth, 16.0))  # how deep the mating tube seats (mm)
bend_radius = float(PARAM(lambda: bend_radius, 32.0))    # centerline bend radius (mm)
leg = float(PARAM(lambda: leg, 55.0))                # straight leg / run length (mm)

# Clamp so extreme UI values still build watertight.
wall = max(2.0, min(wall, 6.0))
clearance = max(0.1, min(clearance, 0.8))
socket_depth = max(8.0, min(socket_depth, 30.0))
bend_radius = max(18.0, min(bend_radius, 60.0))
leg = max(25.0, min(leg, 120.0))


# ── Derived radii ────────────────────────────────────────────────────────────
def _radii():
    """Return (bore_r, sbore_r, out_r) in mm, chosen so the whole fitting is one
    body: a UNIFORM outer radius `out_r` with a stepped internal bore.

    bore_r  : flow bore that runs the full length (od/2 - wall, i.e. matched to the
              seated mating tube's inner path so flow is not choked).
    sbore_r : slip-socket counterbore at the ends (od/2 + clearance) — the mating
              tube slides in here and butts a shoulder where sbore_r steps to bore_r.
    out_r   : the single outer radius everywhere = sbore_r + wall. Because the socket
              is only a wider COUNTERBORE (always < out_r), it never severs the wall,
              so cutting it leaves one solid (no floating socket cup, no trapped void).
    """
    od = tube_od(tube_size)
    sbore_r = od / 2.0 + clearance
    bore_r = max(6.0, od / 2.0 - wall)
    out_r = sbore_r + wall
    return bore_r, sbore_r, out_r


# ── Swept solid rod along a centerline wire ──────────────────────────────────
def _sweep_solid(path_wire, start_uv, start_z, radius):
    """Sweep a SOLID disk of `radius` along path_wire. The disk sits in an XY plane
    offset to start_z, centered at start_uv (which must be the path start). The start
    tangent is vertical for every drain part, so an XY-plane disk is perpendicular."""
    return (
        cq.Workplane("XY")
        .workplane(offset=start_z)
        .center(start_uv[0], start_uv[1])
        .circle(radius)
        .sweep(cq.Workplane(obj=path_wire), isFrenet=True, transition="round")
    )


# ── Axial socket counterbore (a widened mouth cut into an end) ────────────────
def _counterbore(center, axis_dir, radius, depth):
    """A cylindrical cutter of `radius` starting 1 mm proud of `center` and going
    `depth` inward along +axis_dir. Used to widen a bore end into a slip socket.
    Stays strictly inside the (wider) outer wall, so it never severs the body."""
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(radius)
        .extrude(depth + 1.0)
    )
    z = Vector(0, 0, 1)
    a = Vector(*axis_dir).normalized()
    dot = max(-1.0, min(1.0, z.dot(a)))
    ang = math.degrees(math.acos(dot))
    if ang > 1e-6:
        if ang > 179.999:
            cutter = cutter.rotate((0, 0, 0), (1, 0, 0), 180)
        else:
            ax = z.cross(a)
            cutter = cutter.rotate((0, 0, 0), (ax.x, ax.y, ax.z), ang)
    return cutter.translate(center)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_tailpiece():
    """A straight vertical drain tailpiece: slip socket up top, plain outlet below,
    one stepped bore through. Extends a sink strainer down to the trap."""
    bore_r, sbore_r, out_r = _radii()
    total = leg + socket_depth

    body = cq.Workplane("XY").circle(out_r).extrude(total)          # uniform outer
    body = body.cut(cq.Workplane("XY").workplane(offset=-1.0).circle(bore_r).extrude(total + 2.0))
    # Slip counterbore at the top mouth.
    body = body.cut(_counterbore((0, 0, total), (0, 0, 1), sbore_r, socket_depth))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_trap_arm():
    """A quarter-bend trap arm: a straight run into a 90-degree elbow, slip socket on
    the inlet end and a plain spigot outlet. Connects trap outlet to the wall drain."""
    bore_r, sbore_r, out_r = _radii()
    # Bend radius must clear the tube's own outer radius or the swept walls self-
    # intersect through the axis; floor it with a small margin.
    R = max(bend_radius, out_r + 2.0)

    # Centerline: start pointing -Z from the inlet top, 90-degree bend to +X.
    p0 = Vector(0, 0, leg)   # inlet top (slip socket here)
    p1 = Vector(0, 0, 0)     # start of bend
    pc = Vector(R * (1 - math.cos(math.radians(45))), 0, -R * math.sin(math.radians(45)))
    p2 = Vector(R, 0, -R)    # end of bend, tangent now +X
    p3 = Vector(R + leg, 0, -R)  # straight run toward the wall

    path = Wire.assembleEdges([
        Edge.makeLine(p0, p1),
        Edge.makeThreePointArc(p1, pc, p2),
        Edge.makeLine(p2, p3),
    ])

    body = _sweep_solid(path, (0, 0), leg, out_r)                    # uniform outer rod
    body = body.cut(_sweep_solid(path, (0, 0), leg, bore_r))         # flow bore through
    # Slip counterbore at the inlet (top, +Z) and a shallower one at the +X outlet.
    body = body.cut(_counterbore((0, 0, leg), (0, 0, 1), sbore_r, socket_depth))
    body = body.cut(_counterbore((R + leg, 0, -R), (1, 0, 0), sbore_r, socket_depth))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_p_trap():
    """The P-trap U-bend: two vertical legs joined by a 180-degree bottom bend, with a
    slip socket on top of each leg. This is the water-seal trap under a sink."""
    bore_r, sbore_r, out_r = _radii()
    # The 180-degree belly and the leg spacing (2*R) both need R > the tube outer
    # radius, or the swept walls self-intersect; floor it with a small margin.
    R = max(bend_radius, out_r + 2.0)

    p_ltop = Vector(-R, 0, leg)
    p_lbot = Vector(-R, 0, 0)
    p_mid = Vector(0, 0, -R)
    p_rbot = Vector(R, 0, 0)
    p_rtop = Vector(R, 0, leg)

    path = Wire.assembleEdges([
        Edge.makeLine(p_ltop, p_lbot),
        Edge.makeThreePointArc(p_lbot, p_mid, p_rbot),
        Edge.makeLine(p_rbot, p_rtop),
    ])

    body = _sweep_solid(path, (-R, 0), leg, out_r)                  # uniform outer rod
    body = body.cut(_sweep_solid(path, (-R, 0), leg, bore_r))       # flow bore through
    # Slip counterbores on both leg tops (opening +Z).
    for cx in (-R, R):
        body = body.cut(_counterbore((cx, 0, leg), (0, 0, 1), sbore_r, socket_depth))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tailpiece":
    result = build_tailpiece()
elif target_part == "trap_arm":
    result = build_trap_arm()
else:
    result = build_p_trap()
