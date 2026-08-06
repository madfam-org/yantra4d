"""
Universal Bracket Generator — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The most-requested generator after Gridfinity: one cartridge that produces the
common bracket topologies from a single set of parameters. A `bracket_type`
select chooses the family, and each family is exposed as its own studio mode:

  * "angle_bracket"       — a 90° (or arbitrary `angle`) L-bracket: two flat legs
                            meeting at a bend, each with a row of screw holes.
  * "flat_bracket"        — a flat mounting strap / plate: one slab with a screw
                            hole at each end (a mending / joiner plate).
  * "corner_bracket_3d"   — a three-axis corner gusset: three mutually
                            perpendicular flat legs sharing one corner, for
                            bracing box / frame corners in all three planes.

Shared across the batch: a bolt-pattern helper (`drill_row` / `bolt_grid`) and a
plate helper (`slab`) build every hole and leg, so the CDG screw interface is
identical wherever a plate carries fasteners.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `leg_a`).
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
bracket_type = str(PARAM(lambda: bracket_type, "angle_L"))  # angle_L|flat|T|corner_3d
target_part  = str(PARAM(lambda: target_part, ""))          # studio dispatch (part id)

leg_a        = float(PARAM(lambda: leg_a,        50.0))   # leg A length (mm)
leg_b        = float(PARAM(lambda: leg_b,        50.0))   # leg B length (mm)
width        = float(PARAM(lambda: width,        30.0))   # bracket width (mm)
thickness    = float(PARAM(lambda: thickness,     4.0))   # material thickness (mm)
angle        = float(PARAM(lambda: angle,        90.0))   # bend angle for the L (deg)

holes_per_leg = int(PARAM(lambda: holes_per_leg,   2))    # screw holes on each leg
screw_dia    = float(PARAM(lambda: screw_dia,     4.5))   # screw clearance dia (mm)
counterbore  = bool(PARAM(lambda: counterbore,  False))   # flat counterbore for heads
gusset       = bool(PARAM(lambda: gusset,       False))   # add a triangular brace (L only)


# ── Studio mode → bracket topology ───────────────────────────────────────────
# Each studio mode renders a single part id; the manifest part ids are the
# topology names. `bracket_type` is the user-facing family select and stays in
# sync with the active mode so presets and the select both drive the geometry.
PART_FOR_TYPE = {
    "angle_L":   "angle_bracket",
    "flat":      "flat_bracket",
    "T":         "T_bracket",
    "corner_3d": "corner_bracket_3d",
}
TYPE_FOR_PART = {v: k for k, v in PART_FOR_TYPE.items()}

_part_ids = ("angle_bracket", "flat_bracket", "T_bracket", "corner_bracket_3d")
if target_part in _part_ids:
    active_part = target_part
else:
    active_part = PART_FOR_TYPE.get(bracket_type, "angle_bracket")


# ── Safe clamps ──────────────────────────────────────────────────────────────
leg_a = max(12.0, leg_a)
leg_b = max(12.0, leg_b)
width = max(8.0, width)
thickness = max(2.0, thickness)
angle = max(30.0, min(angle, 160.0))
holes_per_leg = max(0, min(holes_per_leg, 6))
screw_dia = max(1.5, min(screw_dia, width - 3.0))
CB_DEPTH = min(thickness * 0.5, screw_dia * 0.6)   # counterbore depth
CB_DIA = screw_dia * 2.0                            # counterbore diameter


# ── Shared plate + bolt-pattern helpers (reused across the batch) ─────────────
def slab(length_x, length_y, thick_z):
    """A flat slab: X:[0,length_x], centered in Y, Z:[0,thick_z]."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(length_x / 2.0, 0, thick_z / 2.0))
        .box(length_x, length_y, thick_z)
    )


def _bore(solid, x, y, top_z, thru):
    """Cut one vertical screw hole (Z axis) centered at (x,y) whose top sits at
    top_z, plus an optional flat counterbore recessed from that top face."""
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, top_z - thru / 2.0))
        .cylinder(thru + 1.0, screw_dia / 2.0)
    )
    solid = solid.cut(hole)
    if counterbore:
        cb = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, top_z - CB_DEPTH / 2.0 + 0.01))
            .cylinder(CB_DEPTH, CB_DIA / 2.0)
        )
        solid = solid.cut(cb)
    return solid


def drill_row(solid, length, top_z):
    """Row of `holes_per_leg` holes along +X on a leg spanning X:[0,length],
    top face at z=top_z, centered in Y. Kept clear of the bend root and tip."""
    if holes_per_leg <= 0:
        return solid
    x0 = max(thickness + screw_dia, length * 0.20)
    x1 = length - max(screw_dia, length * 0.12)
    if x1 <= x0:
        x0 = x1 = length / 2.0
    for i in range(holes_per_leg):
        x = length / 2.0 if holes_per_leg == 1 else x0 + (x1 - x0) * i / (holes_per_leg - 1)
        solid = _bore(solid, x, 0.0, top_z, thickness + 2.0)
    return solid


def bolt_grid(solid, points, top_z):
    """Cut a screw hole (+ optional counterbore) at each (x,y) point."""
    for (x, y) in points:
        solid = _bore(solid, x, y, top_z, thickness + 2.0)
    return solid


# ── Builders ─────────────────────────────────────────────────────────────────
def _gusset_solid():
    """Full-width triangular brace bridging the two legs of the L in the XZ
    plane. Contact vertices are pushed into the leg material so the fuse leaves
    no coincident faces and the result stays watertight at any bend angle."""
    reach = max(min(leg_a, leg_b) * 0.6, thickness * 2.0)
    a_rad = math.radians(angle)
    ux, uz = math.cos(a_rad), math.sin(a_rad)
    ov = thickness * 0.8
    tri = (
        cq.Workplane("XZ")
        .polyline([
            (-ov, -ov),
            (reach, -ov),
            (reach * ux - ov * ux, reach * uz - ov * uz),
        ])
        .close()
        .extrude(width)
    )
    return tri.translate((0, width / 2.0, 0))


def build_angle():
    """L-bracket: leg A flat on XY along +X; leg B built flat then rotated up
    about the bend line (Y axis at x=0) by `angle`. A shared corner fuses them."""
    a = drill_row(slab(leg_a, width, thickness), leg_a, thickness)
    b = drill_row(slab(leg_b, width, thickness), leg_b, thickness)
    b = b.rotate((0, 0, 0), (0, 1, 0), angle)
    body = a.union(b)
    if gusset:
        body = body.union(_gusset_solid()).clean()
    return body


def build_flat():
    """Flat strap / mending plate: one slab spanning X:[0, leg_a], centered in
    Y, with a screw hole near each end (a row along X)."""
    body = slab(leg_a, width, thickness)
    return drill_row(body, leg_a, thickness)


def build_T():
    """T-bracket: a flat base plate (span leg_a) with a perpendicular upright
    (height leg_b) rising from its center. Both carry a hole row."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, thickness / 2.0))
        .box(leg_a, width, thickness)
    )
    if holes_per_leg > 0:
        n = holes_per_leg
        xend = leg_a / 2.0 - max(screw_dia, leg_a * 0.12)
        for i in range(n):
            x = -xend + (2.0 * xend) * (i / (n - 1)) if n > 1 else 0.0
            plate = _bore(plate, x, 0.0, thickness, thickness + 2.0)
    upright = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, thickness + leg_b / 2.0))
        .box(thickness, width, leg_b)
    )
    if holes_per_leg > 0:
        n = holes_per_leg
        z0 = thickness + max(screw_dia, leg_b * 0.20)
        z1 = thickness + leg_b - max(screw_dia, leg_b * 0.12)
        for i in range(n):
            z = z0 + (z1 - z0) * (i / (n - 1)) if n > 1 else thickness + leg_b / 2.0
            hole = (
                cq.Workplane("YZ")
                .transformed(offset=cq.Vector(0, z, 0))
                .cylinder(thickness + 2.0, screw_dia / 2.0)
            )
            upright = upright.cut(hole)
    return plate.union(upright)


def build_corner_3d():
    """Three-axis corner gusset: three mutually perpendicular flat legs sharing
    the origin corner. Leg X lies in the XY plane along +X, leg Y in the XY
    plane along +Y (a floor quarter), and leg Z stands up the +Z wall. Each
    carries one central mounting hole through its thickness."""
    t = thickness
    lx = leg_a
    ly = leg_b
    lz = min(leg_a, leg_b)

    # Floor leg along +X (thickness in Z), width band along +Y.
    floor_x = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(lx / 2.0, width / 2.0, t / 2.0))
        .box(lx, width, t)
    )
    floor_x = _bore(floor_x, lx * 0.6, width / 2.0, t, t + 2.0)

    # Floor leg along +Y (thickness in Z), width band along +X.
    floor_y = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(width / 2.0, ly / 2.0, t / 2.0))
        .box(width, ly, t)
    )
    floor_y = _bore(floor_y, width / 2.0, ly * 0.6, t, t + 2.0)

    # Wall leg standing up +Z (thickness in Y), footprint along +X and +Z.
    wall_z = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(lx / 2.0, t / 2.0, lz / 2.0))
        .box(lx, t, lz)
    )
    hole = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(lx * 0.6, lz * 0.6, 0))
        .cylinder(t + 2.0, screw_dia / 2.0)
    )
    wall_z = wall_z.cut(hole)

    body = floor_x.union(floor_y).union(wall_z)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active_part == "flat_bracket":
    result = build_flat()
elif active_part == "T_bracket":
    result = build_T()
elif active_part == "corner_bracket_3d":
    result = build_corner_3d()
else:
    result = build_angle()
