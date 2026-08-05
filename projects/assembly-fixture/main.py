"""
Assembly / Welding Fixture — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A positioning aid that holds parts in a repeatable location during assembly,
welding, gluing, or drilling. One base plate carries locating pins (in a
selectable pattern), optional raised stops/fences, or a V-groove, plus mounting
holes to bolt the fixture to a bench.

Three build targets are dispatched by `target_part`:
  - "pin_plate"    : base plate + array of locating pins (corners / grid / linear)
  - "stop_fixture" : base plate + edge stops forming an L / corner reference
  - "v_block"      : a V-groove block that cradles round stock

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `base_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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
base_w       = float(PARAM(lambda: base_w,       120.0))  # plate width  (X, mm)
base_d       = float(PARAM(lambda: base_d,        90.0))  # plate depth  (Y, mm)
base_t       = float(PARAM(lambda: base_t,        10.0))  # plate thickness (Z, mm)

pin_pattern  = str(  PARAM(lambda: pin_pattern, "corners"))  # corners|grid|linear
pin_dia      = float(PARAM(lambda: pin_dia,        8.0))   # locating pin diameter
pin_height   = float(PARAM(lambda: pin_height,    18.0))   # pin height above plate
pin_inset    = float(PARAM(lambda: pin_inset,     15.0))   # pin distance from edge
grid_cols    = int(  PARAM(lambda: grid_cols,        3))   # pins across X (grid)
grid_rows    = int(  PARAM(lambda: grid_rows,        2))   # pins across Y (grid)
pin_count    = int(  PARAM(lambda: pin_count,        4))   # pins in a line (linear)

stops        = bool( PARAM(lambda: stops,         True))   # raised edge stops/fences
stop_h       = float(PARAM(lambda: stop_h,        15.0))   # stop wall height
stop_t       = float(PARAM(lambda: stop_t,         8.0))   # stop wall thickness

v_angle      = float(PARAM(lambda: v_angle,       90.0))   # included V-groove angle
v_stock_dia  = float(PARAM(lambda: v_stock_dia,   25.0))   # nominal round stock dia

mount_holes  = bool( PARAM(lambda: mount_holes,   True))   # corner bolt-down holes
mount_dia    = float(PARAM(lambda: mount_dia,      6.5))   # mounting hole diameter
mount_inset  = float(PARAM(lambda: mount_inset,   10.0))   # hole distance from edge

target_part  = str(  PARAM(lambda: target_part, "pin_plate"))

# ── Derived / clamped ────────────────────────────────────────────────────────
base_t      = max(3.0, base_t)
pin_dia     = max(2.0, min(pin_dia, min(base_w, base_d) / 3.0))
grid_cols   = max(1, min(grid_cols, 12))
grid_rows   = max(1, min(grid_rows, 12))
pin_count   = max(1, min(pin_count, 20))
mount_inset = max(mount_dia, min(mount_inset, min(base_w, base_d) / 2.0 - 1.0))
pin_inset   = max(pin_dia, min(pin_inset, min(base_w, base_d) / 2.0 - 1.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def base_plate():
    """Flat base plate centred on XY, base at z=0. Corners lightly filleted."""
    wp = cq.Workplane("XY").box(base_w, base_d, base_t, centered=(True, True, False))
    r = min(3.0, min(base_w, base_d) / 6.0)
    if r > 0.2:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _mount_hole_points():
    hx = base_w / 2.0 - mount_inset
    hy = base_d / 2.0 - mount_inset
    return [(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]


def drill_mount_holes(solid):
    if not mount_holes:
        return solid
    r = min(mount_dia / 2.0, min(base_w, base_d) / 4.0)
    cutter = (
        cq.Workplane("XY")
        .pushPoints(_mount_hole_points())
        .circle(r)
        .extrude(base_t + 2.0)
    )
    return solid.cut(cutter)


def _min_spacing(points):
    """Smallest centre-to-centre distance among the pin points (or a large number
    if there is only one)."""
    best = 1.0e9
    for i in range(len(points)):
        xi, yi = points[i]
        for j in range(i + 1, len(points)):
            xj, yj = points[j]
            dx, dy = xi - xj, yi - yj
            best = min(best, (dx * dx + dy * dy) ** 0.5)
    return best


def _all_pins(points):
    """All locating pins as ONE solid (batched extrude — avoids per-pin unions
    that get very slow for large grids). The effective pin diameter is clamped so
    adjacent pins never interpenetrate (which would be non-manifold), then a
    single chamfer softens every lead-in."""
    d = pin_dia
    if len(points) > 1:
        d = min(d, _min_spacing(points) - 0.6)  # leave a >=0.6 mm gap
    d = max(d, 1.5)
    pins = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, base_t))
        .pushPoints(points)
        .circle(d / 2.0)
        .extrude(pin_height)
    )
    try:
        pins = pins.faces(">Z").chamfer(min(d / 4.0, 1.5))
    except Exception:
        pass
    return pins


def _pin_points():
    """Return the (x, y) centres for the active pin pattern."""
    ax = base_w / 2.0 - pin_inset
    ay = base_d / 2.0 - pin_inset
    if pin_pattern == "grid":
        pts = []
        span_x = base_w - 2.0 * pin_inset
        span_y = base_d - 2.0 * pin_inset
        for c in range(grid_cols):
            fx = 0.0 if grid_cols == 1 else c / (grid_cols - 1)
            px = -span_x / 2.0 + fx * span_x
            for rrow in range(grid_rows):
                fy = 0.0 if grid_rows == 1 else rrow / (grid_rows - 1)
                py = -span_y / 2.0 + fy * span_y
                pts.append((px, py))
        return pts
    if pin_pattern == "linear":
        pts = []
        span_x = base_w - 2.0 * pin_inset
        for i in range(pin_count):
            fx = 0.0 if pin_count == 1 else i / (pin_count - 1)
            px = -span_x / 2.0 + fx * span_x
            pts.append((px, 0.0))
        return pts
    # default "corners"
    return [(ax, ay), (-ax, ay), (ax, -ay), (-ax, -ay)]


# ── pin_plate ────────────────────────────────────────────────────────────────
def build_pin_plate():
    body = base_plate()
    body = drill_mount_holes(body)
    pts = _pin_points()
    if pts:
        body = body.union(_all_pins(pts))
    return body


# ── stop_fixture ─────────────────────────────────────────────────────────────
def build_stop_fixture():
    """Base plate with two perpendicular fences forming an L / corner reference,
    so a part pushed into the corner locates in both X and Y."""
    body = base_plate()
    body = drill_mount_holes(body)
    if not stops:
        return body

    inner_x = -base_w / 2.0 + stop_t / 2.0
    inner_y = -base_d / 2.0 + stop_t / 2.0

    # Fence along the -X edge (runs in Y)
    fence_x = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(inner_x, 0.0, base_t))
        .box(stop_t, base_d, stop_h, centered=(True, True, False))
    )
    # Fence along the -Y edge (runs in X)
    fence_y = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, inner_y, base_t))
        .box(base_w, stop_t, stop_h, centered=(True, True, False))
    )
    body = body.union(fence_x).union(fence_y)
    try:
        body = body.edges("|Z").fillet(min(1.5, stop_t / 3.0))
    except Exception:
        pass
    return body


# ── v_block ──────────────────────────────────────────────────────────────────
def build_v_block():
    """A block with a V-groove running along X that cradles round stock. The
    groove is a triangular prism sized so `v_stock_dia` seats on both flanks."""
    half = math.radians(v_angle / 2.0)
    # groove half-width at the top surface so the notch is deep enough to seat
    # the nominal stock without bottoming out.
    depth = max(v_stock_dia * 0.6, 8.0)
    half_w = depth * math.tan(half)

    block_h = base_t + depth + 4.0
    body = cq.Workplane("XY").box(base_w, base_d, block_h, centered=(True, True, False))

    # Triangular cutter: apex down, opening up, extruded along X.
    top_z = block_h
    cutter = (
        cq.Workplane("XZ")
        .moveTo(-half_w, top_z)
        .lineTo(half_w, top_z)
        .lineTo(0.0, top_z - depth)
        .close()
        .extrude(base_w + 2.0, both=True)
    )
    body = body.cut(cutter)
    body = drill_mount_holes(body)
    try:
        body = body.edges("|Y and >Z").chamfer(min(1.0, stop_t / 4.0))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "pin_plate":    build_pin_plate,
    "stop_fixture": build_stop_fixture,
    "v_block":      build_v_block,
}

result = _dispatch.get(target_part, build_pin_plate)()
