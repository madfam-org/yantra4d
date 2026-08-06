"""
Fan-to-Duct Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Ducts a standard PC / printer fan into round tubing, a hose, or around a corner.
A square fan flange (on the real 40 / 60 / 80 / 120 / 140 mm corner-hole square)
transitions to a round outlet so a fan can feed a duct, a vacuum hose, a resin-
printer exhaust, or a soldering-fume line. The flange bolts to the same fan a
fan-adapter, dust-shroud or fan-filter mounts on.

Three modes, each its own studio part (a single manifold hollow solid):
  * fan_to_round — a straight tapered transition: square fan flange → round duct
                   spigot. The classic "put the fan on a duct" adapter.
  * fan_to_hose  — the same transition ending in a barbed nozzle that a push-on
                   vacuum / garden hose grips, so a fan drives a hose directly.
  * elbow_duct   — a 90-degree elbow: the fan flange turns the airflow through a
                   quarter-torus into a round outlet facing sideways, for tight
                   enclosures where a straight duct will not fit.

Watertight strategy:
  The duct wall is a hollow tube made by lofting the OUTER wall between two
  circles and cutting a slightly longer lofted INNER bore — a genuine closed
  shell, never a tangent kiss. The flange is a solid slab bored open to the inlet
  and UNIONED to the tube (overlapping). The elbow is a swept quarter-torus wall
  (revolve of an annulus, capped by the flange and an outlet ring) so it stays a
  single closed body. Corner holes are bored last through the flange (they vent to
  both faces). Fillets clean the flange blank BEFORE the corner holes.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math

from cadquery import Edge, Vector, Wire


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── PC-fan table (real corner-hole squares) ──────────────────────────────────
FAN_TABLE = {
    "40mm":  {"body": 40.0,  "spacing": 32.0,  "bore": 37.0,  "screw": 3.2},
    "60mm":  {"body": 60.0,  "spacing": 50.0,  "bore": 57.0,  "screw": 4.3},
    "80mm":  {"body": 80.0,  "spacing": 71.5,  "bore": 77.0,  "screw": 4.3},
    "120mm": {"body": 120.0, "spacing": 105.0, "bore": 117.0, "screw": 4.5},
    "140mm": {"body": 140.0, "spacing": 124.5, "bore": 137.0, "screw": 4.5},
}


def fan_spec(name):
    return FAN_TABLE.get(str(name).strip(), FAN_TABLE["120mm"])


# ── Parameters ────────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "fan_to_round"))
# "fan_to_round" | "fan_to_hose" | "elbow_duct"

fan_size = str(PARAM(lambda: fan_size, "120mm"))   # 40|60|80|120|140 mm
duct_len = float(PARAM(lambda: duct_len, 45.0))    # straight duct length (Z, mm)
outlet_dia = float(PARAM(lambda: outlet_dia, 70.0))  # round outlet inner diameter (mm)
duct_wall = float(PARAM(lambda: duct_wall, 2.4))   # duct wall thickness (mm)
flange_t = float(PARAM(lambda: flange_t, 4.0))     # fan flange thickness (mm)
barb_dia = float(PARAM(lambda: barb_dia, 32.0))    # hose-barb nominal OD (fan_to_hose)
barb_count = int(PARAM(lambda: barb_count, 3))     # number of barb ridges

# Clamp to sane ranges so extreme UI values never crash the kernel.
duct_len = max(15.0, min(duct_len, 140.0))
duct_wall = max(1.6, min(duct_wall, 6.0))
flange_t = max(2.5, min(flange_t, 10.0))
barb_count = max(1, min(barb_count, 6))

spec = fan_spec(fan_size)
body = spec["body"]
spacing = spec["spacing"]
bore = spec["bore"]
screw = spec["screw"]

bore_r = bore / 2.0
inset = max(screw / 2.0 + 2.0, 4.0)
# Outlet clamped so it never exceeds the inlet bore (a duct only narrows/holds).
outlet_dia = max(10.0, min(outlet_dia, bore))
out_r = outlet_dia / 2.0
barb_dia = max(8.0, min(barb_dia, bore))


# ── Shared flange helper ─────────────────────────────────────────────────────
def fan_flange(inlet_r=None):
    """The square fan mounting flange, filleted, bored open to `inlet_r` (defaults
    to the full fan bore). Occupies Z:[0, flange_t]. Returns the solid (still needs
    corner holes). A smaller inlet_r leaves a solid web the elbow core fuses into."""
    ir = bore_r if inlet_r is None else inlet_r
    flange = (
        cq.Workplane("XY")
        .box(body, body, flange_t, centered=(True, True, False))
    )
    try:
        flange = flange.edges("|Z").fillet(min(inset, body / 2.0 - 0.1))
    except Exception:
        pass
    inlet = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(ir).extrude(flange_t + 1.0)
    )
    return flange.cut(inlet)


def drill_corners(solid):
    """Bore the four fan corner holes through the flange."""
    h = spacing / 2.0
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .pushPoints([(h, h), (-h, h), (h, -h), (-h, -h)])
        .circle(screw / 2.0)
        .extrude(flange_t + 1.0)
    )
    return solid.cut(tool)


def tapered_tube(z0, length, r_in_bot, r_in_top):
    """A hollow tapered tube from z0 up `length`: outer wall lofted between the
    two inner radii + wall, inner bore lofted (longer) and cut. Closed shell."""
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(r_in_bot + duct_wall)
        .workplane(offset=length)
        .circle(r_in_top + duct_wall)
        .loft(combine=True)
    )
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 - 0.5))
        .circle(r_in_bot)
        .workplane(offset=length + 1.0)
        .circle(r_in_top)
        .loft(combine=True)
    )
    return outer.cut(inner)


def barb_nozzle(z0):
    """A barbed hose nozzle rising from z0: a stack of tapered ridges over a solid
    core column (bored through afterward). Returns (solid, top_z)."""
    tip_r = max(out_r, barb_dia / 2.0 - 1.2)
    ridge_r = barb_dia / 2.0
    ridge_h = 4.0
    gap = 1.4
    solid = None
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
            .translate((0, 0, z))
        )
        solid = ring if solid is None else solid.union(ring)
        z += ridge_h + gap
    core = (
        cq.Workplane("XY")
        .circle(tip_r).extrude(z - z0)
        .translate((0, 0, z0))
    )
    solid = core if solid is None else solid.union(core)
    return solid, z


# ── Part builders ─────────────────────────────────────────────────────────────
def build_fan_to_round():
    """Straight tapered transition: square fan flange → round duct spigot."""
    flange = fan_flange()
    # Transition tube tapering from the fan bore down to the outlet.
    tube = tapered_tube(flange_t - 0.5, duct_len + 0.5, bore_r, out_r)
    duct = flange.union(tube)
    duct = drill_corners(duct)
    return duct


def build_fan_to_hose():
    """Fan flange → short taper → barbed hose nozzle. A fan that drives a hose."""
    flange = fan_flange()
    taper_len = max(10.0, duct_len * 0.45)
    barb_r = barb_dia / 2.0
    tube = tapered_tube(flange_t - 0.5, taper_len + 0.5, bore_r, barb_r)
    body_solid = flange.union(tube)
    # Barbed nozzle on top of the taper, then bore the whole airway through.
    nozzle, ntop = barb_nozzle(flange_t + taper_len)
    body_solid = body_solid.union(nozzle)
    channel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(max(2.0, barb_r - duct_wall))
        .extrude(ntop + 2.0)
    )
    body_solid = body_solid.cut(channel)
    body_solid = drill_corners(body_solid)
    try:
        body_solid = body_solid.clean()
    except Exception:
        pass
    return body_solid


def _sweep_along(path, r, seed_z):
    """Sweep a circle of radius r along `path`, seeding the profile on an XY
    workplane at height seed_z (the path start) so the frame is well-conditioned."""
    return (
        cq.Workplane("XY").workplane(offset=seed_z).circle(r)
        .sweep(cq.Workplane(obj=path), isFrenet=True, transition="round")
    )


def build_elbow_duct():
    """A 90-degree elbow: the fan flange feeds a swept round duct that turns the
    airflow to a round outlet facing +X. The airway is a SOLID core swept along an
    L-centerline (straight up from the flange, a quarter arc, then a short +X
    stub); the bore is the SAME path swept at the airway radius and cut through —
    a single closed pipe. The flange is unioned on and bored to the inlet."""
    r_air = min(bore_r, out_r + duct_wall)   # airway radius through the elbow
    core_r = r_air + duct_wall               # outer duct radius
    R = max(core_r + 2.0, r_air + duct_wall + 6.0)   # centerline bend radius
    # Flange inlet sized to the airway (not the full fan bore) so a solid web
    # remains around the axis for the swept core to fuse into (single body).
    flange = fan_flange(inlet_r=r_air)

    # L-centerline (all in the XZ plane, y=0):
    #   riser: from the flange top straight up +Z to the bend start S,
    #   arc:   quarter turn (center O=S+(R,0,0)) so the tangent rotates +Z -> +X,
    #   stub:  a short +X run to the outlet face.
    riser = 3.0
    z_s = flange_t + riser                 # bend start height
    # Start the riser at z=0 (flange bottom) so the swept core passes THROUGH the
    # whole flange slab — a volumetric overlap, so union() yields one body.
    p_bot = Vector(0, 0, 0.0)
    p_s = Vector(0, 0, z_s)                 # arc start, tangent +Z
    a45 = math.radians(45.0)
    p_mid = Vector(R - R * math.cos(a45), 0, z_s + R * math.sin(a45))
    p_e = Vector(R, 0, z_s + R)             # arc end, tangent +X
    p_out = Vector(R + max(8.0, duct_len * 0.35), 0, z_s + R)   # outlet stub end
    path = Wire.assembleEdges([
        Edge.makeLine(p_bot, p_s),
        Edge.makeThreePointArc(p_s, p_mid, p_e),
        Edge.makeLine(p_e, p_out),
    ])

    core = _sweep_along(path, core_r, 0.0)
    body_solid = core.union(flange)
    # Bore the whole airway along the same path, then open the flange inlet.
    bore = _sweep_along(path, r_air, 0.0)
    body_solid = body_solid.cut(bore)
    inlet = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(r_air).extrude(flange_t + 2.0)
    )
    body_solid = body_solid.cut(inlet)
    try:
        body_solid = body_solid.clean()
    except Exception:
        pass
    body_solid = drill_corners(body_solid)
    return body_solid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "fan_to_hose":
    result = build_fan_to_hose()
elif target_part == "elbow_duct":
    result = build_elbow_duct()
else:
    result = build_fan_to_round()
