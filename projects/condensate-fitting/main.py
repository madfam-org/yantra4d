"""
Sump / Condensate Fitting — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Fittings for AC condensate, dehumidifier, and sump discharge lines: a barb-to-barb
coupler (join or step between two tube sizes), a 90-degree barbed elbow, and a
barb-to-socket drain adapter. Barbs are sized to real vinyl / poly tube nominal
sizes so push-on tubing grips and holds without a clamp.

Real dimensions (US small-tube barbs, expressed in mm):
  - 3/8" tube barb OD ~= 9.53 mm; 1/2" ~= 12.70 mm; 5/8" ~= 15.88 mm; 3/4" ~= 19.05 mm.
  Barb ridges flare slightly over the nominal OD and step back so the tube slides on
  one way and resists pulling off. The socket end slips over a larger pipe stub.

Watertightness strategy (barbed hollow fittings as closed manifolds):
  Each fitting is a SOLID core (straight extrusion, swept elbow, or stacked barb
  ridges) unioned into one body, then a single through-bore is cut end to end so both
  ends are ANNULAR rims (an open bare tube would leave boundary loops -> not
  watertight). Barb ridges are built by LOFTING tapered frusta (small -> big -> small)
  and unioning them onto a solid core column with real overlap — never a `.revolve()`
  of a cut groove (which yields a zero-volume seam) and never a tangent kiss. The
  elbow is swept along an edge-assembled centerline wire with the profile seeded at
  the path start. The socket bore opens to its end face (no trapped void).

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


# ── Tube barb nominal ODs (mm) ───────────────────────────────────────────────
TUBE_OD = {
    "3/8": 9.53,
    "1/2": 12.70,
    "5/8": 15.88,
    "3/4": 19.05,
}


def tube_od(name):
    """Barb tube nominal OD (mm), defaulting to 1/2\"."""
    return TUBE_OD.get(name, TUBE_OD["1/2"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "barb_coupler"))
tube_a = str(PARAM(lambda: tube_a, "1/2"))        # end A tube size
tube_b = str(PARAM(lambda: tube_b, "3/8"))        # end B tube size
wall = float(PARAM(lambda: wall, 2.2))            # fitting wall thickness (mm)
barb_count = int(PARAM(lambda: barb_count, 3))    # ridges per barb
bend_radius = float(PARAM(lambda: bend_radius, 22.0))  # elbow centerline radius (mm)
socket_od = str(PARAM(lambda: socket_od, "3/4"))  # drain stub the socket slips over
clearance = float(PARAM(lambda: clearance, 0.4))  # socket slip clearance (mm)

# Clamp so extreme UI values still build watertight.
wall = max(1.6, min(wall, 4.0))
barb_count = max(1, min(barb_count, 6))
bend_radius = max(14.0, min(bend_radius, 45.0))
clearance = max(0.1, min(clearance, 0.8))


# ── Bore radius shared by all ends (min of the two tube inner paths) ──────────
def _bore_r():
    """Flow bore radius: the smaller tube's inner path so flow is continuous."""
    small = min(tube_od(tube_a), tube_od(tube_b))
    return max(3.0, small / 2.0 - wall)


# ── Barb nozzle (stacked lofted ridges on a solid core) ──────────────────────
def barb_nozzle(od, z0, height_dir=1):
    """A barbed nozzle rising from z0 along +Z (height_dir=1) or -Z (-1): a stack of
    tapered ridges that grip a push-on tube. Returns (solid, tip_z). The core column
    is solid so the ridges share one body; the bore is cut later by the caller."""
    ridge_r = od / 2.0
    tip_r = max(_bore_r() + 1.0, ridge_r - 1.0)
    ridge_h = 4.0
    gap = 1.2
    body = None
    z = z0
    for _ in range(barb_count):
        ring = (
            cq.Workplane("XY")
            .circle(tip_r)
            .workplane(offset=ridge_h * 0.7)
            .circle(ridge_r)
            .workplane(offset=ridge_h * 0.3)
            .circle(tip_r)
            .loft(combine=True)
            .translate((0, 0, z if height_dir > 0 else z - (ridge_h)))
        )
        body = ring if body is None else body.union(ring)
        z += height_dir * (ridge_h + gap)
    span = abs(z - z0)
    core = (
        cq.Workplane("XY").circle(tip_r)
        .extrude(span if height_dir > 0 else -span)
        .translate((0, 0, z0))
    )
    body = core if body is None else body.union(core)
    return body, z


# ── Part builders ─────────────────────────────────────────────────────────────
def build_barb_coupler():
    """A straight barb-to-barb coupler with a central grip hub. Joins or steps
    between two condensate tubes; one flow bore runs through everything."""
    bore_r = _bore_r()
    hub_r = max(tube_od(tube_a), tube_od(tube_b)) / 2.0 + wall + 1.0
    hub_h = 6.0

    # Central hub occupies [0, hub_h].
    hub = cq.Workplane("XY").circle(hub_r).extrude(hub_h)
    # Barb A rises above the hub; barb B drops below 0.
    barb_a, top_a = barb_nozzle(tube_od(tube_a), hub_h, height_dir=1)
    barb_b, bot_b = barb_nozzle(tube_od(tube_b), 0.0, height_dir=-1)

    body = hub.union(barb_a).union(barb_b)
    # One through bore from below barb B to above barb A.
    chan = (
        cq.Workplane("XY").workplane(offset=bot_b - 1.0)
        .circle(bore_r).extrude((top_a - bot_b) + 2.0)
    )
    body = body.cut(chan)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_barb_elbow():
    """A 90-degree barbed elbow. The core is swept along an L centerline; a barb
    nozzle is fused at each open end and one bore runs through the whole path."""
    bore_r = _bore_r()
    core_r = max(tube_od(tube_a), tube_od(tube_b)) / 2.0 + wall * 0.0 + 1.0
    core_r = max(core_r, bore_r + wall)
    R = max(bend_radius, core_r + 2.0)

    # Centerline: start at inlet top going -Z, quarter arc around center (R,0,0) to
    # (R,0,-R) so the tangent turns to +X, then a short +X stub for the outlet barb.
    p0 = Vector(0, 0, R)          # inlet (barb rises above here)
    p1 = Vector(0, 0, 0)
    pc = Vector(R - R * math.cos(math.radians(45)), 0, -R * math.sin(math.radians(45)))
    p2 = Vector(R, 0, -R)
    p3 = Vector(R + 4.0, 0, -R)   # short stub so the outlet barb attaches on +X

    path = Wire.assembleEdges([
        Edge.makeLine(p0, p1),
        Edge.makeThreePointArc(p1, pc, p2),
        Edge.makeLine(p2, p3),
    ])

    def sweep(r):
        return (
            cq.Workplane("XY").workplane(offset=R).center(0, 0).circle(r)
            .sweep(cq.Workplane(obj=path), isFrenet=True, transition="round")
        )

    core = sweep(core_r)
    # Barb at the inlet (top, +Z) and outlet (+X).
    barb_in, top_in = barb_nozzle(tube_od(tube_a), R, height_dir=1)
    core = core.union(barb_in)
    # Outlet barb along +X: build along +Z then rotate to +X and translate to p3.
    barb_out, _ = barb_nozzle(tube_od(tube_b), 0.0, height_dir=1)
    barb_out = barb_out.rotate((0, 0, 0), (0, 1, 0), 90).translate((p3.x, p3.y, p3.z))
    core = core.union(barb_out)

    # One bore through the whole path + a matching bore down each barb axis.
    bore_core = sweep(bore_r)
    body = core.cut(bore_core)
    # Bore up the inlet barb (it sits above R, beyond the swept core).
    body = body.cut(
        cq.Workplane("XY").workplane(offset=R - 1.0).circle(bore_r).extrude((top_in - R) + 2.0)
    )
    # Bore along the outlet barb axis (+X): a cylinder from p3 outward.
    obarb_len = barb_count * (4.0 + 1.2) + 2.0
    bore_out = (
        cq.Workplane("YZ").workplane(offset=R - 3.0)
        .center(0, -R).circle(bore_r).extrude(obarb_len + 6.0)
    )
    body = body.cut(bore_out)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_drain_adapter():
    """A barb-to-socket adapter: a barb on one end for push-on tube, a slip socket on
    the other that fits over a larger drain stub, with a shoulder flange between."""
    bore_r = _bore_r()
    sock_bore_r = tube_od(socket_od) / 2.0 + clearance
    sock_out_r = sock_bore_r + wall
    flange_r = sock_out_r + 3.0
    sock_h = 16.0
    flange_h = 4.0

    # Socket cup at the bottom [0, sock_h], opening downward (bore to the bottom face).
    body = cq.Workplane("XY").circle(sock_out_r).extrude(sock_h)
    # Flange ring just above the socket.
    body = body.union(
        cq.Workplane("XY").workplane(offset=sock_h).circle(flange_r).extrude(flange_h)
    )
    # Barb rising above the flange.
    barb, top_b = barb_nozzle(tube_od(tube_a), sock_h + flange_h, height_dir=1)
    body = body.union(barb)

    # Bores: flow bore through everything; wider socket counterbore at the bottom.
    body = body.cut(
        cq.Workplane("XY").workplane(offset=-1.0).circle(bore_r).extrude((top_b) + 2.0)
    )
    body = body.cut(
        cq.Workplane("XY").workplane(offset=-1.0).circle(sock_bore_r).extrude(sock_h + 1.0)
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "barb_elbow":
    result = build_barb_elbow()
elif target_part == "drain_adapter":
    result = build_drain_adapter()
else:
    result = build_barb_coupler()
