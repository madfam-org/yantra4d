"""
Fan Grill / Duct Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

PC / printer fan accessories built on the standard PC-fan screw square. A fan
table gives the correct corner-hole spacing for 40 / 60 / 80 / 120 / 140 mm
fans. Three modes are dispatched via `target_part`:

  * "grill"        — a finger guard: an outer frame with concentric rings and
                     radial spokes over the fan bore, plus the four corner
                     mounting holes. Built entirely from solids so it exports
                     watertight.
  * "duct"         — a tapered duct adapting the fan face to a smaller/larger
                     round outlet (or a second fan size).
  * "filter_frame" — a shallow frame that clamps a filter media disc over the
                     fan, retained by a thin inner lip.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `fan_size`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── PC fan table ─────────────────────────────────────────────────────────────
# body   : nominal fan body size (square edge, mm)
# spacing: corner mounting-hole centre-to-centre distance (mm)
# bore   : the largest airflow circle for that fan (mm)
# screw  : corner-hole clearance diameter (mm)
FAN_TABLE = {
    "40mm":  {"body": 40.0,  "spacing": 32.0,  "bore": 37.0,  "screw": 3.2},
    "60mm":  {"body": 60.0,  "spacing": 50.0,  "bore": 57.0,  "screw": 4.3},
    "80mm":  {"body": 80.0,  "spacing": 71.5,  "bore": 77.0,  "screw": 4.3},
    "120mm": {"body": 120.0, "spacing": 105.0, "bore": 117.0, "screw": 4.5},
    "140mm": {"body": 140.0, "spacing": 124.5, "bore": 137.0, "screw": 4.5},
}


def fan_spec(key):
    k = str(key).strip().lower().replace(" ", "")
    if not k.endswith("mm"):
        k = k + "mm"
    return FAN_TABLE.get(k, FAN_TABLE["120mm"])


# ── Parameters ───────────────────────────────────────────────────────────────
fan_size    = str(PARAM(lambda: fan_size, "120mm"))   # 40|60|80|120|140 mm
thickness   = float(PARAM(lambda: thickness,  3.0))   # grill / frame plate thickness
ring_count  = int(PARAM(lambda: ring_count,     4))   # concentric rings (grill)
spoke_count = int(PARAM(lambda: spoke_count,    6))   # radial spokes (grill)
bar_w       = float(PARAM(lambda: bar_w,      2.4))   # ring / spoke bar width

duct_len    = float(PARAM(lambda: duct_len,  40.0))   # duct length (Z)
outlet_dia  = float(PARAM(lambda: outlet_dia, 80.0))  # duct outlet diameter
duct_wall   = float(PARAM(lambda: duct_wall,  2.4))   # duct wall thickness

filter_depth = float(PARAM(lambda: filter_depth, 6.0))  # filter frame depth

target_part = str(PARAM(lambda: target_part, "grill"))  # grill|duct|filter_frame

# ── Derived ──────────────────────────────────────────────────────────────────
spec = fan_spec(fan_size)
body = spec["body"]
spacing = spec["spacing"]
bore = spec["bore"]
screw = spec["screw"]

thickness = max(1.5, thickness)
bar_w = max(1.2, bar_w)
ring_count = max(1, min(ring_count, 10))
spoke_count = max(2, min(spoke_count, 16))
duct_wall = max(1.2, duct_wall)
duct_len = max(5.0, duct_len)
outlet_dia = max(6.0, min(outlet_dia, 300.0))
filter_depth = max(2.0, filter_depth)

frame_r = body / 2.0             # outer frame outer radius
bore_r = bore / 2.0             # open airflow radius
inset = max(screw / 2.0 + 2.0, 4.0)


# ── Helpers ──────────────────────────────────────────────────────────────────
def corner_points():
    """Four fan mounting-hole centres, centred on the origin."""
    h = spacing / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


def solid_ring(radius, width, height):
    """A flat annular ring solid: outer circle minus inner circle, extruded."""
    ro = radius + width / 2.0
    ri = max(0.1, radius - width / 2.0)
    outer = cq.Workplane("XY").circle(ro).extrude(height)
    inner = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -0.5)
    ).circle(ri).extrude(height + 1.0)
    return outer.cut(inner)


def drill_corners(solid, height):
    r = screw / 2.0
    cutter = (
        cq.Workplane("XY")
        .pushPoints(corner_points())
        .circle(r)
        .extrude(height + 2.0)
        .translate((0, 0, -1.0))
    )
    return solid.cut(cutter)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_grill():
    """Finger guard: square frame + hub + concentric rings + spokes, all solid.

    Everything is a positive solid unioned together, so the mesh is watertight.
    The airflow gaps are simply the empty space the rings/spokes do not fill."""
    # Square outer frame with a rounded-square inner window down to the bore.
    outer_sq = cq.Workplane("XY").box(body, body, thickness, centered=(True, True, False))
    try:
        outer_sq = outer_sq.edges("|Z").fillet(min(inset, body / 2.0 - 0.1))
    except Exception:
        pass
    window = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -0.5)
    ).circle(bore_r).extrude(thickness + 1.0)
    frame = outer_sq.cut(window)

    parts = [frame]

    # Outer rim ring right at the bore edge so the guard closes the window.
    parts.append(solid_ring(bore_r - bar_w / 2.0, bar_w, thickness))

    # Concentric rings from near the centre out to the bore.
    hub_r = max(bar_w, bore_r * 0.14)
    if ring_count > 0:
        span = bore_r - bar_w - hub_r
        for i in range(1, ring_count + 1):
            rr = hub_r + span * i / (ring_count + 1)
            if rr - bar_w / 2.0 > 0.2:
                parts.append(solid_ring(rr, bar_w, thickness))

    # Central hub (solid disc).
    parts.append(cq.Workplane("XY").circle(hub_r).extrude(thickness))

    # Radial spokes tying hub → rim.
    length = bore_r
    for i in range(spoke_count):
        ang = 360.0 * i / spoke_count
        spoke = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, ang))
            .transformed(offset=cq.Vector(length / 2.0, 0, 0))
            .box(length, bar_w, thickness, centered=(True, True, False))
        )
        parts.append(spoke)

    guard = parts[0]
    for p in parts[1:]:
        guard = guard.union(p)

    guard = drill_corners(guard, thickness)
    return guard


def build_duct():
    """A hollow tapered duct: square fan flange → round outlet."""
    flange_t = thickness
    # Square mounting flange with the four corner holes.
    flange = cq.Workplane("XY").box(body, body, flange_t, centered=(True, True, False))
    try:
        flange = flange.edges("|Z").fillet(min(inset, body / 2.0 - 0.1))
    except Exception:
        pass

    inlet_r = bore_r
    out_r = outlet_dia / 2.0

    # Outer taper (loft between the two circles), then hollow it.
    outer = (
        cq.Workplane("XY").circle(inlet_r + duct_wall)
        .workplane(offset=duct_len)
        .circle(out_r + duct_wall)
        .loft(combine=True)
    )
    inner = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(inlet_r)
        .workplane(offset=duct_len + 1.0)
        .circle(out_r)
        .loft(combine=True)
    )
    tube = outer.cut(inner)

    # Bore the flange open to the inlet and join.
    flange_bore = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -0.5)
    ).circle(inlet_r).extrude(flange_t + 1.0)
    flange = flange.cut(flange_bore)

    duct = flange.union(tube)
    duct = drill_corners(duct, flange_t)
    return duct


def build_filter_frame():
    """A shallow frame clamping a filter disc over the fan: outer wall + floor
    grid opening + a thin inner retaining lip."""
    depth = filter_depth
    outer = cq.Workplane("XY").box(body, body, depth, centered=(True, True, False))
    try:
        outer = outer.edges("|Z").fillet(min(inset, body / 2.0 - 0.1))
    except Exception:
        pass

    # Pocket that holds the filter media (open at the top).
    pocket = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, 1.5)
    ).circle(bore_r).extrude(depth)
    frame = outer.cut(pocket)

    # Airflow opening through the floor (a ring of the bore).
    airflow = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -0.5)
    ).circle(bore_r - 3.0).extrude(2.0 + 1.0)
    frame = frame.cut(airflow)

    # Cross ribs on the floor so the filter cannot fall through.
    for ang in (0.0, 90.0):
        rib = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(bore * 1.0, bar_w, 1.5, centered=(True, True, False))
        )
        frame = frame.union(rib)

    frame = drill_corners(frame, depth)
    return frame


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "duct":
    result = build_duct()
elif target_part == "filter_frame":
    result = build_filter_frame()
else:
    result = build_grill()
