"""
VESA Thin-Client Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Mounts a mini-PC / thin-client / SBC enclosure behind a monitor on the VESA
FDMI / MIS-D 100 x 100 mm bolt pattern (M4). The device is captured by a strap
cage, rests on an L-shelf tray, or is pinched between a pair of brackets — pick
the style, set the device box size, done. Grows the `vesa` family.

VESA MIS-D geometry (nominal, dimensionally real):
  - MIS-D 100 bolt square = 100.0 mm, M4 (4.5 mm clearance holes)
  - (MIS-D 75 = 75 mm also selectable via the bolt-square parameter)

Watertight strategy:
  Every part is built by UNIONING overlapping solids (backing plate + walls /
  shelf / brackets), never tangent ones. The VESA holes are through-holes that
  vent to both faces. Device windows and cable slots are through-cuts. Fillets
  are applied to clean blanks BEFORE feature cuts, wrapped in try/except. No
  hollow posts on solid bases (no trapped voids).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>).
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


# ── Parameters (VESA MIS-D + device box) ─────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "strap_cage"))
# "strap_cage" | "tray_shelf" | "bracket_pair"

vesa_sq = float(PARAM(lambda: vesa_sq, 100.0))      # VESA bolt square (100 or 75)
plate_t = float(PARAM(lambda: plate_t, 5.0))        # backing plate thickness
bolt_d = float(PARAM(lambda: bolt_d, 4.5))          # M4 clearance hole dia
dev_w = float(PARAM(lambda: dev_w, 120.0))          # device box width (X)
dev_h = float(PARAM(lambda: dev_h, 120.0))          # device box height (Y)
dev_t = float(PARAM(lambda: dev_t, 30.0))           # device box depth/thickness
wall = float(PARAM(lambda: wall, 4.0))              # cage / bracket wall thickness
lip = float(PARAM(lambda: lip, 10.0))               # capture lip / shelf depth
corner_r = float(PARAM(lambda: corner_r, 5.0))      # plate corner radius

# Clamp to sane ranges so extreme UI values never crash the kernel.
vesa_sq = max(75.0, min(vesa_sq, 100.0))
plate_t = max(3.0, min(plate_t, 10.0))
bolt_d = max(3.5, min(bolt_d, 7.0))
dev_w = max(50.0, min(dev_w, 220.0))
dev_h = max(50.0, min(dev_h, 220.0))
dev_t = max(10.0, min(dev_t, 90.0))
wall = max(2.5, min(wall, 8.0))
lip = max(5.0, min(lip, 30.0))
corner_r = max(2.0, min(corner_r, 12.0))


# ── Primitives ───────────────────────────────────────────────────────────────
def _rounded_slab(sx, sy, thick, rad):
    """A slab centred on XY, base at z=0, filleted vertical edges. Fillet the
    clean blank BEFORE any feature cut."""
    blank = cq.Workplane("XY").box(sx, sy, thick, centered=(True, True, False))
    try:
        blank = blank.edges("|Z").fillet(min(rad, min(sx, sy) / 2.0 - 1.0))
    except Exception:
        pass
    return blank


def _backing_plate():
    """The VESA backing plate: a rounded slab covering the bolt square plus
    margin, drilled with the 4 VESA through-holes and a cable slot."""
    size = vesa_sq + 24.0
    body = _rounded_slab(size, size, plate_t, corner_r)
    # VESA square through-holes (vent both faces).
    h = vesa_sq / 2.0
    pts = [(-h, -h), (h, -h), (h, h), (-h, h)]
    body = (
        body.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts)
        .hole(bolt_d)
    )
    # Central cable slot (through, vents).
    body = (
        body.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .slot2D(min(size - 12.0, 40.0), 12.0, angle=0)
        .cutThruAll()
    )
    return body, size


# ── Part builders ────────────────────────────────────────────────────────────
def build_strap_cage():
    """VESA backing plate with a raised rectangular CAGE (four walls) that cradles
    the device box, each wall carrying a capture lip that folds inward over the
    device. The device slides in from the front and is trapped by the lips."""
    body, size = _backing_plate()

    # Cage inner cavity = device footprint + a hair of clearance.
    cav_w = dev_w + 1.0
    cav_h = dev_h + 1.0
    outer_w = cav_w + 2.0 * wall
    outer_h = cav_h + 2.0 * wall
    cage_z = dev_t + wall  # wall height = box depth + a lip shelf

    # Outer cage block, unioned onto the plate with overlap (solid weld).
    cage = _rounded_slab(outer_w, outer_h, cage_z, corner_r)
    cage = cage.translate((0, 0, plate_t - 0.01))
    body = body.union(cage)

    # Hollow out the cavity from the top down to just above the plate, leaving a
    # solid floor (the plate) — the cavity opens UP to the outside (vented), so
    # no trapped void.
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_t + 1.0))
        .box(cav_w, cav_h, cage_z, centered=(True, True, False))
    )
    body = body.cut(cavity)

    # Capture lips: shave the top inner edge of the walls inward so the mouth is
    # narrower than the cavity (device is trapped). Cut a wider window from the
    # very top so the lips are a thin overhang.
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_t + cage_z - lip))
        .box(cav_w - 2.0 * (wall * 0.5), cav_h - 2.0 * (wall * 0.5),
             lip + 1.0, centered=(True, True, False))
    )
    body = body.cut(mouth)

    # A front access/airflow window through the -Y wall (vents).
    win = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, plate_t + cage_z * 0.5, -outer_h / 2.0 - 1.0))
        .rect(cav_w * 0.6, cage_z * 0.6)
        .extrude(outer_h + 2.0)
    )
    body = body.cut(win)
    return body


def build_tray_shelf():
    """VESA backing plate with a horizontal L-SHELF at the bottom edge that the
    device box rests on, projecting forward (+Z, the device side) with a front
    curb so the box can't slide off. The whole L is one welded body.

    Frame: the plate is a flat panel in z in [0, plate_t]; the monitor is the
    z<0 side and the device stands off in +Z. The shelf is a ledge at the plate's
    bottom Y edge, overlapping UP into the plate (never tangent)."""
    body, size = _backing_plate()
    ov = max(2.0, wall)
    y_bot = -size / 2.0                        # bottom Y edge of the plate
    shelf_w = min(dev_w + 2.0 * wall, size)    # never exceed the plate width
    shelf_depth = dev_t + lip                  # forward projection in +Z

    # Ledge slab: lies in the XZ sense — width along X, thickness `wall` along Y
    # at the bottom edge, projecting up +Z from the plate front. Overlap it up
    # into the plate by ov in +Y.
    shelf = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_bot + (wall + ov) / 2.0 - ov,
                                      plate_t - 0.01))
        .box(shelf_w, wall + ov, shelf_depth, centered=(True, True, False))
    )
    body = body.union(shelf)

    # Front curb at the far +Z end of the ledge so the device can't slide off.
    curb = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_bot + wall / 2.0,
                                      plate_t + shelf_depth - lip))
        .box(shelf_w, wall, lip, centered=(True, True, False))
    )
    body = body.union(curb)

    # Two strap holes through the ledge (vent along +Y through wall thickness),
    # kept inside the ledge footprint so they never sever it.
    for sx in (-1, 1):
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(sx * shelf_w * 0.30,
                                          plate_t + shelf_depth * 0.5,
                                          y_bot - 1.0))
            .circle(2.6)
            .extrude(wall + 2.0)
        )
        body = body.cut(hole)
    return body


def build_bracket_pair():
    """VESA backing plate with TWO L-brackets standing off the plate (+Z, the
    device side) that pinch the device between them from left and right. Each
    bracket is a wall rising in +Z with an inward foot that hooks over the device
    face. One watertight body.

    Frame: plate is a flat panel in z in [0, plate_t]; brackets rise in +Z and
    overlap DOWN into the plate (never tangent) so the assembly fuses."""
    body, size = _backing_plate()
    ov = max(2.0, wall)
    br_rise = min(dev_t + wall, size * 0.7)    # how far the wall stands off in +Z
    arm_len = min(dev_h, size - 4.0)           # how far the wall runs along Y
    arm_w = wall
    # Keep each arm fully over the plate so it always welds (never floats off a
    # too-wide device): clamp its centre so |x| + arm_w/2 <= size/2 - 1.
    x_max = size / 2.0 - arm_w / 2.0 - 1.0
    x_dev = min(dev_w / 2.0 + wall / 2.0, x_max)

    for sx in (-1, 1):
        x = sx * x_dev
        # Side wall rising in +Z, overlapping down into the plate by ov.
        arm = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, plate_t - ov))
            .box(arm_w, arm_len, br_rise + ov, centered=(True, True, False))
        )
        body = body.union(arm)
        # Inward foot at the top of the wall hooking over the device face (+Z).
        foot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x - sx * (lip - arm_w) / 2.0, 0,
                                          plate_t + br_rise - arm_w))
            .box(lip, arm_len, arm_w, centered=(True, True, False))
        )
        body = body.union(foot)

        # A vertical slot up the wall for cable ties / bolts (through X, vents).
        slot = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, plate_t + br_rise * 0.5, x - sx * (arm_w + 2.0)))
            .slot2D(min(arm_len * 0.5, 30.0), 5.0, angle=0)
            .extrude(sx * (arm_w + 4.0))
        )
        body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tray_shelf":
    result = build_tray_shelf()
elif target_part == "bracket_pair":
    result = build_bracket_pair()
else:
    result = build_strap_cage()
