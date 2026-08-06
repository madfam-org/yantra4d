"""Toiletry Holder — Toothbrush / Razor Holder (Yantra4D Hyperobject, CadQuery).

Household bathroom organizer sized to REAL handle diameters: manual toothbrush
handles (~13-16 mm), electric toothbrush bodies (~25-32 mm), and disposable
razor handles (~10-14 mm). Three distinct socket-interface modes:

  * counter_caddy — a solid puck with a row of vertical bores that sit brushes
    and razors upright on the counter; a drain slot keeps water out.
  * wall_rail     — a wall strip with keyhole (obround) bores that grip a handle
    from the side, plus two screw mounts.
  * razor_cradle  — a single wall hook that cradles one handle by the neck.

Watertightness strategy: fillet the blank BEFORE cutting bores; every bore opens
to a face (no trapped voids); the drain is an obround (stadium) slot, not a fan
of arcs; screw counterbores open through to the back face.

Sandbox contract (apps/api/services/engine/cq_runner.py): `cq` and `math` are
pre-injected; manifest params arrive as bare globals; read them via
PARAM(lambda: name, default) (globals()/eval are not in the allowed builtins);
assign the final solid to `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "counter_caddy"))
hole_d      = float(PARAM(lambda: hole_d,      16.0))   # handle bore diameter (mm)
hole_count  = int(PARAM(lambda: hole_count,     4))     # number of handle bores
wall        = float(PARAM(lambda: wall,         4.0))   # material between bores / outer wall
height      = float(PARAM(lambda: height,      45.0))   # body height (caddy) / rail width
depth       = float(PARAM(lambda: depth,       30.0))   # front-to-back depth
screw_d     = float(PARAM(lambda: screw_d,      4.2))   # wall-mount screw clearance (M4 ~4.2)

# Clamp to sane, buildable ranges.
hole_d     = max(6.0, min(hole_d, 40.0))
hole_count = max(1, min(hole_count, 8))
wall       = max(2.0, min(wall, 10.0))
height     = max(20.0, min(height, 90.0))
depth      = max(18.0, min(depth, 60.0))
screw_d    = max(2.5, min(screw_d, 8.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _fillet_safe(wp, selector, radius):
    """Fillet the blank BEFORE cutting features; degrade gracefully."""
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _bore_xs(pitch, n):
    """Symmetric X positions for n bores at a given pitch (centered on 0)."""
    return [(-(n - 1) / 2.0 + i) * pitch for i in range(n)]


def _obround(wp, length, width):
    """A stadium (obround) 2D wire on the current workplane: robust vs arc fans."""
    r = width / 2.0
    straight = max(0.0, length - width)
    return (
        wp.moveTo(-straight / 2.0, r)
        .lineTo(straight / 2.0, r)
        .threePointArc((straight / 2.0 + r, 0), (straight / 2.0, -r))
        .lineTo(-straight / 2.0, -r)
        .threePointArc((-straight / 2.0 - r, 0), (-straight / 2.0, r))
        .close()
    )


# ── counter_caddy ────────────────────────────────────────────────────────────
def build_counter_caddy():
    """A rounded puck with a row of vertical handle bores + a drain slot."""
    pitch = hole_d + wall
    body_len = hole_count * pitch + wall
    body_w = max(depth, hole_d + 2 * wall)

    body = (
        cq.Workplane("XY")
        .box(body_len, body_w, height, centered=(True, True, False))
    )
    # Round all vertical corners + the top rim BEFORE cutting bores.
    body = _fillet_safe(body, "|Z", min(wall * 1.4, body_w / 4.0))
    body = _fillet_safe(body, ">Z", min(2.0, wall * 0.5))

    # Vertical handle bores — each opens to the top face, blind above a solid
    # floor so water drains out the slot, never trapped.
    floor = max(3.0, wall * 0.8)
    bore_depth = height - floor
    for x in _bore_xs(pitch, hole_count):
        cutter = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, floor))
            .circle(hole_d / 2.0)
            .extrude(bore_depth + 1.0)
        )
        body = body.cut(cutter)

    # Drain slot through the floor at the bottom (opens bottom + into bores).
    drain = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .rect(body_len * 0.6, min(6.0, body_w * 0.3))
        .extrude(floor + 2.0)
    )
    body = body.cut(drain)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── wall_rail ────────────────────────────────────────────────────────────────
def build_wall_rail():
    """A wall strip; handles slide DOWN into keyhole (obround) side bores.

    The rail lies flat: X = length, Y = plate thickness, Z = height. Handle
    slots are obround openings cut through the Y thickness, open at the top so a
    brush drops in from above. Two screw mounts anchor it to the wall."""
    pitch = hole_d + wall
    rail_len = hole_count * pitch + wall
    plate_th = max(depth * 0.35, hole_d * 0.6 + wall)
    rail_h = height

    plate = (
        cq.Workplane("XY")
        .box(rail_len, plate_th, rail_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall, plate_th / 3.0))

    # Handle slots: vertical obround through-holes, open at the top rim so a
    # brush drops in from above. Drawn on the XZ plane (centered high enough that
    # the top arc breaks through the rail top), extruded through the Y thickness.
    slot_len = hole_d * 1.9
    slot_cz = rail_h - hole_d  # center height: top of the obround clears rail_h
    for x in _bore_xs(pitch, hole_count):
        cut = cq.Workplane("XZ").center(x, slot_cz)
        cut = _obround(cut, slot_len, hole_d)
        cut = cut.extrude(-(plate_th + 2.0)).translate((0, plate_th / 2.0 + 1.0, 0))
        plate = plate.cut(cut)

    # Two screw mounts through the plate (front to back), countersunk on front.
    mount_x = rail_len / 2.0 - pitch / 2.0
    for sx in (-mount_x, mount_x):
        screw = (
            cq.Workplane("XZ")
            .center(sx, rail_h * 0.5)
            .circle(screw_d / 2.0)
            .extrude(-(plate_th + 2.0))
            .translate((0, plate_th / 2.0 + 1.0, 0))
        )
        head = (
            cq.Workplane("XZ")
            .center(sx, rail_h * 0.5)
            .circle(screw_d)
            .extrude(-3.0)
            .translate((0, plate_th / 2.0 + 1.0, 0))
        )
        plate = plate.cut(screw).cut(head)

    try:
        plate = plate.clean()
    except Exception:
        pass
    return plate


# ── razor_cradle ─────────────────────────────────────────────────────────────
def build_razor_cradle():
    """A single wall hook: a back plate with an arm that cradles one handle by
    the neck. A C-shaped (open-front) collar grips the handle; the opening lets
    the handle press in from the front."""
    plate_w = hole_d + 2 * wall
    plate_h = height
    plate_th = max(4.0, wall)

    # Back plate (against the wall): X = width, Y = thickness, Z = height.
    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall, plate_w / 4.0))

    # Screw hole through the back plate.
    screw = (
        cq.Workplane("XZ")
        .center(0, plate_h * 0.72)
        .circle(screw_d / 2.0)
        .extrude(-(plate_th + 2.0))
        .translate((0, plate_th / 2.0 + 1.0, 0))
    )
    plate = plate.cut(screw)

    # Cradle arm: a stubby cylinder of material projecting forward (+Y), then a
    # C-collar bored through it to hold the handle. Union with overlap into the
    # plate so the boolean is volumetric (watertight).
    arm_y = depth * 0.7
    collar_or = hole_d / 2.0 + wall
    collar_z = plate_h * 0.32
    arm = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, collar_z, -(plate_th / 2.0)))
        .circle(collar_or)
        .extrude(-(arm_y + plate_th))
    )
    body = plate.union(arm)

    # Bore the handle hole through the collar (open front + back → no trapped void).
    hole = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, collar_z, -(plate_th / 2.0) - arm_y - 1.0))
        .circle(hole_d / 2.0)
        .extrude(arm_y + plate_th + 2.0)
    )
    body = body.cut(hole)

    # Open the collar front (C-clip) so the handle presses in.
    mouth_w = hole_d * 0.62
    mouth = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, collar_z, -(plate_th / 2.0) - arm_y - 1.0))
        .rect(mouth_w, mouth_w)
        .extrude(arm_y + 2.0)
        .translate((0, collar_or, 0))
    )
    body = body.cut(mouth)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wall_rail":
    result = build_wall_rail()
elif target_part == "razor_cradle":
    result = build_razor_cradle()
else:
    result = build_counter_caddy()
