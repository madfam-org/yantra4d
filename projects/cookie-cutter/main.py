"""
Parametric Cookie / Fondant Cutter & Stamp — Yantra4D Hyperobject Cartridge
(CadQuery / B-Rep).

A press-and-cut cookie / fondant cutter: a thin vertical CUTTING WALL that
follows a chosen outline (circle, star, heart, square, hexagon), topped by a
wider FLANGE you press with your thumb. Optionally an interior relief STAMP that
embosses a detail into the dough, and a linked DOUBLE cutter (a ring-shaped
outline between two concentric walls).

Watertight strategy (this is a thin-wall part, so care is taken):
  The cutting wall is NOT a swept skin — it is a genuine hollow prism:
  outer filled-outline extrusion  MINUS  inner filled-outline extrusion. Both
  outlines come from the SAME shape family scaled about the centre, so their
  difference is a single closed loop with a real ~`wall` thickness — a solid
  with volume, watertight by construction (no zero-thickness faces, no
  sphere-tangent unions). The pressing flange is a second, shorter, WIDER hollow
  prism fused at the top with a small vertical overlap so the boolean union is
  volumetric (a clean fuse, not a coincident-face kiss).

FOOD-CONTACT NOTE: geometry only. Food-safe filament, a food-safe sealing/finish
and hygienic handling are the maker's responsibility (see README).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shape`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
shape       = str(  PARAM(lambda: shape,      "star"))   # circle|star|heart|square|hex
size        = float(PARAM(lambda: size,        60.0))    # outline nominal size (mm, widest span)
cutter_h    = float(PARAM(lambda: cutter_h,    18.0))    # cutting-wall height (mm)
wall        = float(PARAM(lambda: wall,         0.8))    # cutting edge / wall thickness (mm)
flange_w    = float(PARAM(lambda: flange_w,     3.0))    # extra width of the top press flange (mm)
flange_h    = float(PARAM(lambda: flange_h,     2.4))    # flange height (mm)
stamp_depth = float(PARAM(lambda: stamp_depth,  2.0))    # relief height of the interior stamp (mm)
gap         = float(PARAM(lambda: gap,          8.0))    # ring gap for the double cutter (mm)

target_part = str(  PARAM(lambda: target_part, "cutter"))  # cutter|cutter_stamp|double_cutter

# ── Clamps (keep extreme UI values watertight) ───────────────────────────────
size        = max(20.0, min(size, 160.0))
cutter_h    = max(8.0,  min(cutter_h, 40.0))
wall        = max(0.6,  min(wall, 2.0))
flange_w    = max(1.5,  min(flange_w, 8.0))
flange_h    = max(1.5,  min(flange_h, 6.0))
stamp_depth = max(0.8,  min(stamp_depth, 5.0))
gap         = max(4.0,  min(gap, min(size * 0.4, 30.0)))


# ── 2D outline profiles (filled faces, centred on origin) ────────────────────
def _outline_wire(name, span):
    """A closed 2D wire for `name` whose widest extent is ~`span` mm.
    Returned as a Workplane holding a single closed wire (ready to extrude)."""
    r = span / 2.0
    if name == "circle":
        return cq.Workplane("XY").circle(r)
    if name == "square":
        return cq.Workplane("XY").rect(span, span)
    if name == "hex":
        # Flat-to-flat = span; polygon() takes circumdiameter, so scale up.
        return cq.Workplane("XY").polygon(6, span)
    if name == "star":
        # 5-point star: alternate outer/inner radii around 10 vertices.
        pts = []
        inner = r * 0.42
        for i in range(10):
            ang = math.pi / 2.0 + i * math.pi / 5.0  # start pointing +Y
            rad = r if i % 2 == 0 else inner
            pts.append((rad * math.cos(ang), rad * math.sin(ang)))
        return cq.Workplane("XY").polyline(pts).close()
    if name == "heart":
        # Parametric heart curve, normalised so its width ~= span.
        raw = []
        n = 80
        for i in range(n):
            t = 2.0 * math.pi * i / n
            x = 16.0 * math.sin(t) ** 3
            y = (13.0 * math.cos(t) - 5.0 * math.cos(2 * t)
                 - 2.0 * math.cos(3 * t) - math.cos(4 * t))
            raw.append((x, y))
        xs = [p[0] for p in raw]
        s = span / (max(xs) - min(xs))
        pts = [(x * s, y * s) for (x, y) in raw]
        return cq.Workplane("XY").polyline(pts).close()
    # default fallback
    return cq.Workplane("XY").circle(r)


def _hollow_prism(name, outer_span, inner_span, height, z0=0.0):
    """A closed-loop wall of the given shape family: filled `outer_span` outline
    extruded, MINUS the filled `inner_span` outline extruded. Watertight solid
    with a real wall thickness. z0 places the base."""
    outer = _outline_wire(name, outer_span).extrude(height)
    inner = _outline_wire(name, inner_span).extrude(height + 2.0).translate((0, 0, -1.0))
    prism = outer.cut(inner)
    if z0:
        prism = prism.translate((0, 0, z0))
    return prism


# ── Part builders ────────────────────────────────────────────────────────────
def _base_cutter(name, span):
    """A cutting wall + a wider top pressing flange for outline `name`/`span`."""
    # Cutting wall: thin hollow prism, full height.
    wall_solid = _hollow_prism(name, span, span - 2.0 * wall, cutter_h)

    # Pressing flange: a short WIDER hollow prism at the top. Overlap down into
    # the wall by `ov` so the union is volumetric (clean fuse, watertight).
    ov = min(1.0, cutter_h * 0.25)
    flange_outer = span + 2.0 * flange_w
    flange_inner = span - 2.0 * wall
    flange = _hollow_prism(
        name, flange_outer, flange_inner, flange_h + ov, z0=cutter_h - flange_h - ov
    )
    body = wall_solid.union(flange)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cutter():
    return _base_cutter(shape, size)


def build_cutter_stamp():
    """Cutter plus an interior relief STAMP: a raised ridge following a smaller
    copy of the outline, carried on a thin web across the flange plane, so a
    single press cuts AND embosses a detail into the dough."""
    body = _base_cutter(shape, size)

    # Stamp web: a thin closed disk/plate spanning the interior at the top, from
    # which the relief ridge rises. Built as a full filled outline of the inner
    # bore, a thin plate, unioned at flange top with overlap.
    inner_span = size - 2.0 * wall
    web_span = inner_span - 0.2
    web_th = 1.2
    web_z = cutter_h - web_th
    ov = 0.6
    web = _outline_wire(shape, web_span).extrude(web_th + ov).translate((0, 0, web_z - ov))
    body = body.union(web)

    # Relief ridge: a smaller-scale hollow prism of the SAME shape rising from
    # the web (the detail that presses into the dough). Volumetric union.
    ridge_outer = size * 0.55
    ridge_inner = ridge_outer - 2.0 * max(1.0, wall + 0.4)
    ridge = _hollow_prism(
        shape, ridge_outer, ridge_inner, stamp_depth + ov,
        z0=web_z + web_th - ov,
    )
    body = body.union(ridge)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_double_cutter():
    """A linked DOUBLE cutter: an outer outline and a concentric inner outline
    joined by the pressing flange, cutting a ring / donut of dough in one press.
    Both walls are hollow prisms sharing the flange at the top."""
    outer_span = size
    inner_span = max(12.0, size - 2.0 * gap)

    outer_wall = _hollow_prism(shape, outer_span, outer_span - 2.0 * wall, cutter_h)
    inner_wall = _hollow_prism(shape, inner_span, inner_span - 2.0 * wall, cutter_h)

    # Shared flange bridging outer→inner at the top: a wide hollow prism whose
    # OUTER edge is beyond the outer wall and whose INNER edge is inside the
    # inner wall, so it ties both walls together (one press cuts a ring).
    ov = min(1.0, cutter_h * 0.25)
    bridge = _hollow_prism(
        shape, outer_span + 2.0 * flange_w, inner_span - 2.0 * wall,
        flange_h + ov, z0=cutter_h - flange_h - ov,
    )
    body = outer_wall.union(inner_wall).union(bridge)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cutter_stamp":
    result = build_cutter_stamp()
elif target_part == "double_cutter":
    result = build_double_cutter()
else:
    result = build_cutter()
