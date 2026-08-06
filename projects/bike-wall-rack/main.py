"""
Bike Wall Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Wall-mounted bicycle storage. A load-rated wall plate screws to the studs; an arm
projects from it to carry the bike either horizontally (by the top tube),
vertically (by a wheel), or as a pedal shelf. The tube/wheel contact is a
half-round cradle pocket so the frame or rim rests without point loads.

Three modes (rendered per-part via `target_part`):

  * "horizontal_hook" — a J cradle on a horizontal arm: the bike's top tube
                        drops into a half-round pocket with an up-turned lip, so
                        the bike hangs level along the wall.
  * "vertical_hook"   — a hook sized to a wheel rim/tire: a taller J whose pocket
                        radius fits the tire, so the bike hangs nose-up by a
                        wheel.
  * "pedal_shelf"     — a flat shelf with a slot the pedal/crank rests in, so the
                        bike stands with a pedal supported on the shelf.

The wall plate always carries a stud-spaced screw pattern (16 in / 406 mm US
stud spacing is a preset option), so the load goes into framing, not drywall.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tube_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

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


# ── Stud-spacing table ───────────────────────────────────────────────────────
# Common wall-framing stud spacings; the plate holes land on one bay so the two
# screws hit adjacent studs (or one stud, for the narrow option).
STUD_TABLE = {
    "single": 0.0,      # both screws into ONE stud, stacked vertically
    "406":    406.4,    # 16 in US stud spacing
    "610":    609.6,    # 24 in US stud spacing
}


def stud_spacing(key):
    k = str(key).strip().lower().replace("in", "").replace('"', "").replace(" ", "")
    if k in ("16",):
        k = "406"
    elif k in ("24",):
        k = "610"
    elif k in ("0", "one", "1"):
        k = "single"
    return STUD_TABLE.get(k, STUD_TABLE["406"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "horizontal_hook"))  # horizontal_hook|vertical_hook|pedal_shelf

tube_w = float(PARAM(lambda: tube_w, 35.0))        # top-tube width / diameter to cradle (mm)
tire_w = float(PARAM(lambda: tire_w, 40.0))        # tire/rim width for the vertical hook (mm)
arm_len = float(PARAM(lambda: arm_len, 90.0))      # how far the arm projects from the wall (mm)
arm_w = float(PARAM(lambda: arm_w, 45.0))          # arm / cradle width across the bike (mm)
thickness = float(PARAM(lambda: thickness, 10.0))  # structural material thickness (mm)

plate_w = float(PARAM(lambda: plate_w, 60.0))      # wall-plate width (mm)
plate_h = float(PARAM(lambda: plate_h, 120.0))     # wall-plate height (mm)
stud = str(PARAM(lambda: stud, "single"))          # stud spacing key
screw_dia = float(PARAM(lambda: screw_dia, 6.5))   # lag/wood screw clearance dia (mm)
lip_h = float(PARAM(lambda: lip_h, 20.0))          # up-turned retaining lip height (mm)


# ── Active part ──────────────────────────────────────────────────────────────
_parts = ("horizontal_hook", "vertical_hook", "pedal_shelf")
active = target_part if target_part in _parts else "horizontal_hook"

# ── Safe clamps (load-bearing: keep thickness generous) ──────────────────────
thickness = max(6.0, thickness)
tube_w = max(15.0, tube_w)
tire_w = max(20.0, tire_w)
arm_len = max(40.0, arm_len)
arm_w = max(20.0, arm_w)
plate_w = max(30.0, plate_w)
plate_h = max(50.0, plate_h)
screw_dia = max(3.0, min(screw_dia, plate_w - 6.0))
lip_h = max(5.0, lip_h)


# ── Shared plate + bolt-pattern helpers (reused across the batch) ─────────────
def wall_plate():
    """The load plate standing in the XZ plane (facing -Y): width plate_w in X,
    height plate_h in Z from z=0, thickness in Y:[0, thickness]; back face at
    y=0 mounts to the wall."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, thickness / 2.0, plate_h / 2.0))
        .box(plate_w, thickness, plate_h)
    )


def stud_screw_points():
    """Wall-screw centres. For a real stud spacing the plate would span two
    studs, but a bike rack plate is narrow, so the two screws stack VERTICALLY
    into one stud (the safe default); wider spacings splay them toward the plate
    edges if the plate is wide enough to reach two studs."""
    span = stud_spacing(stud)
    z_hi = plate_h - max(screw_dia, plate_h * 0.12)
    z_lo = max(screw_dia * 1.5, plate_h * 0.12)
    if span <= 1.0 or span > (plate_w - screw_dia):
        # Stack two screws vertically on the centre line (into one stud).
        return [(0.0, z_lo), (0.0, z_hi)]
    # Splay horizontally to two studs, mid-height, plus one centre top for pull.
    hx = span / 2.0
    zc = plate_h / 2.0
    return [(-hx, zc), (hx, zc), (0.0, z_hi)]


def drill_wall_screws(body):
    """Drill the wall screws through the plate thickness (Y), countersunk on the
    front so lag-screw heads/washers seat."""
    r = screw_dia / 2.0
    for (x, z) in stud_screw_points():
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, z, 0))
            .cylinder(thickness + 2.0, r)
            .translate((0, thickness / 2.0, 0))
        )
        body = body.cut(hole)
        # Counterbore from the front for a washer/head.
        cb = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, z, 0))
            .cylinder(min(thickness * 0.5, 4.0), r * 1.8)
            .translate((0, thickness - min(thickness * 0.5, 4.0) / 2.0, 0))
        )
        body = body.cut(cb)
    return body


def cradle_pocket(body, cradle_r, cx, cz):
    """Cut a half-round cradle: a horizontal cylinder (axis along X, the bike's
    width) of radius `cradle_r`, centred at (y=cx, z=cz), removed from the arm so
    the tube/tire nests in a smooth trough. The cylinder is longer than the arm
    width so it cuts clean through both sides."""
    cyl = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(cx, cz, 0))
        .cylinder(arm_w + 4.0, cradle_r)
    )
    body = body.cut(cyl)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_horizontal_hook():
    """J cradle on a horizontal arm. The arm projects in +Y at a height on the
    plate; a half-round pocket cradles the top tube, and the arm tip turns UP
    into a retaining lip so the bike cannot roll off."""
    plate = wall_plate()

    arm_z = plate_h * 0.5           # arm mid-height on the plate
    arm_h = tube_w + 2.0 * thickness  # arm tall enough to hold the cradle

    # Horizontal arm projecting from the plate front (+Y).
    arm = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, thickness + arm_len / 2.0, arm_z)
        )
        .box(arm_w, arm_len, arm_h)
    )

    # Up-turned lip at the arm tip.
    lip = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(
                0, thickness + arm_len - thickness / 2.0, arm_z + arm_h / 2.0 + lip_h / 2.0
            )
        )
        .box(arm_w, thickness, lip_h)
    )

    body = plate.union(arm).union(lip)

    # Cradle: half-round trough for the top tube, sitting in the arm's top,
    # a little back from the lip so the tube seats against the lip.
    cradle_r = tube_w / 2.0
    cx = thickness + arm_len - thickness - cradle_r - 2.0
    cz = arm_z + arm_h / 2.0 - cradle_r * 0.4   # cut into the top of the arm
    body = cradle_pocket(body, cradle_r, cx, cz)

    body = drill_wall_screws(body)
    return body.clean()


def build_vertical_hook():
    """Wheel hook: a taller J whose cradle radius fits the tire, so the bike
    hangs nose-up by a wheel. The arm rises at a slight upward reach and the
    pocket is sized to tire_w; a generous lip keeps the wheel captured."""
    plate = wall_plate()

    arm_z = plate_h * 0.62
    arm_h = tire_w + 2.0 * thickness
    reach = arm_len

    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, thickness + reach / 2.0, arm_z))
        .box(arm_w, reach, arm_h)
    )
    # Tall up-turned lip (a hook) at the tip to capture the wheel.
    hook_lip = tire_w * 0.9 + lip_h
    lip = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(
                0, thickness + reach - thickness / 2.0, arm_z + arm_h / 2.0 + hook_lip / 2.0
            )
        )
        .box(arm_w, thickness, hook_lip)
    )
    body = plate.union(arm).union(lip)

    # Cradle sized to the tire.
    cradle_r = tire_w / 2.0 + 2.0
    cx = thickness + reach - thickness - cradle_r - 2.0
    cz = arm_z + arm_h / 2.0 - cradle_r * 0.3
    body = cradle_pocket(body, cradle_r, cx, cz)

    body = drill_wall_screws(body)
    return body.clean()


def build_pedal_shelf():
    """A flat shelf with a pedal/crank slot. The bike leans so a pedal rests on
    the shelf, the crank arm dropping into a central slot; the shelf edge has a
    lip so the pedal cannot slide off."""
    plate = wall_plate()

    shelf_z = plate_h * 0.4
    shelf = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, thickness + arm_len / 2.0, shelf_z + thickness / 2.0)
        )
        .box(arm_w, arm_len, thickness)
    )
    # Front lip so the pedal cannot slide off the outer edge.
    lip = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(
                0, thickness + arm_len - thickness / 2.0, shelf_z + thickness + lip_h / 2.0
            )
        )
        .box(arm_w, thickness, lip_h)
    )
    # Under-brace triangle so the shelf carries load.
    reach = min(arm_len * 0.7, shelf_z * 0.8)
    reach = max(reach, thickness * 2.0)
    brace = (
        cq.Workplane("YZ")
        .polyline([
            (thickness, shelf_z),
            (thickness + reach, shelf_z),
            (thickness, shelf_z - reach),
        ])
        .close()
        .extrude(arm_w)
        .translate((-arm_w / 2.0, 0, 0))
    )
    body = plate.union(shelf).union(lip).union(brace)

    # Pedal/crank slot: a rectangular through-slot along Y in the shelf centre.
    slot_w = min(tube_w * 0.7, arm_w * 0.4)
    slot = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, thickness + arm_len * 0.55, shelf_z + thickness / 2.0)
        )
        .box(slot_w, arm_len * 0.6, thickness + 2.0)
    )
    body = body.cut(slot)

    body = drill_wall_screws(body)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "vertical_hook":
    result = build_vertical_hook()
elif active == "pedal_shelf":
    result = build_pedal_shelf()
else:
    result = build_horizontal_hook()
