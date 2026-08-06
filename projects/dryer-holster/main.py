"""Dryer Holster — Hair Dryer / Styling-Tool Wall Holster (Yantra4D Hyperobject).

Wall holsters for hair dryers and curling / flat-iron tools, sized to REAL
handle and barrel diameters: dryer handles (~40-55 mm), dryer barrels / nozzles
(~50-75 mm), curling-iron handles (~28-35 mm). Three distinct socket modes:

  * barrel_cradle — a U-shaped cradle the dryer barrel drops into sideways,
    open at the front so it lifts straight out.
  * handle_holster — a deep tube socket the handle drops into so the tool hangs
    handle-down; a cord slot lets the cable exit the back.
  * cord_hook     — a compact hook to loop the cord + hang the tool by its handle.

Watertightness: fillet before cutting; the cradle U is a boolean cut opening to
the top face; the holster bore opens to the top face over a solid floor with a
side cord slot (no trapped void); the hook is a swept-solid, not a shell.

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params bare globals
via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "barrel_cradle"))
barrel_d    = float(PARAM(lambda: barrel_d,    62.0))   # dryer barrel diameter (mm)
handle_d    = float(PARAM(lambda: handle_d,    45.0))   # handle diameter (mm)
wall        = float(PARAM(lambda: wall,         5.0))   # wall thickness (mm)
plate_h     = float(PARAM(lambda: plate_h,     70.0))   # wall-plate height (mm)
depth       = float(PARAM(lambda: depth,       60.0))   # cradle / socket reach (mm)
screw_d     = float(PARAM(lambda: screw_d,      4.2))   # mount screw clearance (mm)

barrel_d = max(35.0, min(barrel_d, 95.0))
handle_d = max(25.0, min(handle_d, 65.0))
wall     = max(3.0, min(wall, 10.0))
plate_h  = max(40.0, min(plate_h, 120.0))
depth    = max(35.0, min(depth, 90.0))
screw_d  = max(2.5, min(screw_d, 8.0))


def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _back_screws(plate_th, span_x, at_z_list):
    # Two columns only when clearly separated (>= 3*screw_d apart); else a single
    # centred hole. Tangent twin holes pinch to zero wall and break
    # watertightness. Plain through-holes (both=True) — no countersink.
    cutter = None
    if span_x >= 3.0 * screw_d:
        xs = (-span_x / 2.0, span_x / 2.0)
    else:
        xs = (0.0,)
    for x in xs:
        for z in at_z_list:
            hole = (
                cq.Workplane("XZ").center(x, z).circle(screw_d / 2.0)
                .extrude(plate_th, both=True)
            )
            cutter = hole if cutter is None else cutter.union(hole)
    return cutter


# ── barrel_cradle ────────────────────────────────────────────────────────────
def build_barrel_cradle():
    """A U-cradle the barrel drops into; open front to lift straight out."""
    block_w = barrel_d + 2 * wall
    plate_th = max(5.0, wall)
    arm_y = min(depth, barrel_d + wall)

    # Back plate.
    plate = (
        cq.Workplane("XY")
        .box(block_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall * 1.4, block_w / 5.0))

    # Forward cradle block (solid) unioned to the plate mid-height.
    cradle_z = plate_h * 0.5
    cradle_h = min(plate_h * 0.5, barrel_d)
    block = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0, cradle_z - cradle_h / 2.0))
        .box(block_w, arm_y, cradle_h, centered=(True, True, False))
        .translate((0, arm_y / 2.0, 0))
    )
    body = plate.union(block)
    body = _fillet_safe(body, ">Y and |Z", min(wall, block_w / 6.0))

    # Cut the barrel channel: a horizontal cylinder along Y, opening to the top
    # via a slot the barrel width. Cylinder cut leaves the U walls; the top slot
    # opens it so the barrel lifts out (both open to faces → watertight).
    chan_cy = cradle_z + barrel_d * 0.10
    channel = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, chan_cy, -(plate_th / 2.0) - arm_y - 1.0))
        .circle(barrel_d / 2.0)
        .extrude(arm_y + plate_th + 2.0)
    )
    body = body.cut(channel)
    top_slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0 - 1.0, chan_cy))
        .box(barrel_d * 0.9, arm_y + 2.0, cradle_h, centered=(True, True, False))
        .translate((0, (arm_y + 2.0) / 2.0, 0))
    )
    body = body.cut(top_slot)

    screws = _back_screws(plate_th, block_w - wall * 2.0, [plate_h * 0.9, plate_h * 0.1])
    if screws is not None:
        body = body.cut(screws)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── handle_holster ───────────────────────────────────────────────────────────
def build_handle_holster():
    """A deep tube socket the handle drops into; tool hangs handle-down."""
    tube_or = handle_d / 2.0 + wall
    plate_th = max(5.0, wall)
    plate_w = tube_or * 2.0

    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall, plate_w / 5.0))

    # Vertical tube projecting forward, unioned to the plate.
    tube_z0 = plate_h * 0.18
    tube_len = plate_h * 0.6
    stand_off = min(depth, tube_or + wall)
    tube = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0 + stand_off - tube_or, tube_z0))
        .circle(tube_or)
        .extrude(tube_len)
    )
    # Connector web tying tube to plate (solid) so the union is volumetric.
    web = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0, tube_z0))
        .box(wall * 2.2, stand_off, tube_len, centered=(True, True, False))
        .translate((0, stand_off / 2.0, 0))
    )
    body = plate.union(web).union(tube)

    # Bore the handle socket from the TOP down to a solid floor (no trapped void
    # because a cord slot opens the floor to the side).
    floor = max(3.0, wall)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0 + stand_off - tube_or, tube_z0 + floor))
        .circle(handle_d / 2.0)
        .extrude(tube_len)
    )
    body = body.cut(bore)
    # Cord slot: opens the tube floor + wall out the back so the cable exits.
    cord = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, tube_z0 + floor * 0.3))
        .box(min(handle_d * 0.5, 18.0), plate_th + stand_off + 4.0, floor * 1.4, centered=(True, True, False))
        .translate((0, (plate_th + stand_off) / 2.0 - 1.0, 0))
    )
    body = body.cut(cord)

    screws = _back_screws(plate_th, 0, [plate_h * 0.9, plate_h * 0.1])
    if screws is not None:
        body = body.cut(screws)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── cord_hook ────────────────────────────────────────────────────────────────
def build_cord_hook():
    """A compact wall hook: back plate + an up-curved horn to loop the cord and
    hang the tool by its handle. Built as a swept solid (never a shell)."""
    plate_w = max(handle_d, 40.0)
    plate_th = max(5.0, wall)

    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall, plate_w / 5.0))

    # Horn: built from solid primitives placed with EXPLICIT points + direction
    # vectors (cq.Solid.makeCylinder / makeSphere) so there is no plane-normal
    # sign ambiguity. A forward arm along +Y + an elbow sphere + an up lip along
    # +Z, each overlapping the previous solid → every boolean is volumetric.
    horn_r = max(4.0, wall * 1.2)
    reach = min(depth, plate_h * 0.6)
    up = plate_h * 0.28
    hook_z = plate_h * 0.38
    front = plate_th / 2.0

    # Forward arm: root a little INSIDE the plate (y = -horn_r) and run to the
    # tip (y = front + reach), so it always overlaps the plate volume.
    arm_y0 = -horn_r
    arm_len = (front + reach) - arm_y0
    arm = cq.Solid.makeCylinder(
        horn_r, arm_len, cq.Vector(0, arm_y0, hook_z), cq.Vector(0, 1, 0)
    )
    # Up lip: a vertical cylinder placed so it OVERLAPS the arm generously (no
    # tangent seams, no separate sphere). Start it a full horn_r below the arm
    # centre and pull it back into the arm by horn_r on Y so the two cylinders
    # interpenetrate → a single volumetric union.
    lip_y = front + reach - horn_r
    lip = cq.Solid.makeCylinder(
        horn_r, up + 2.0 * horn_r,
        cq.Vector(0, lip_y, hook_z - horn_r), cq.Vector(0, 0, 1)
    )
    body = plate.union(cq.Workplane(obj=arm)).union(cq.Workplane(obj=lip))

    screws = _back_screws(plate_th, 0, [plate_h * 0.88, plate_h * 0.12])
    if screws is not None:
        body = body.cut(screws)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "handle_holster":
    result = build_handle_holster()
elif target_part == "cord_hook":
    result = build_cord_hook()
else:
    result = build_barrel_cradle()
