"""
Curtain / Blind Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall bracket that holds a curtain or blind rod at a set projection from the
wall. The cradle can be an open-top C (drop the rod in) or a closed ring (thread
the rod through), sized to `rod_dia`. A wall plate carries two mounting holes.

Three parts (dispatched through `target_part`):
  * "bracket"        — a standard single wall bracket: plate + arm + rod cradle.
  * "end_bracket"    — a bracket with a closing end cap on the outer side of the
                       cradle so the rod cannot slide off the end of the run.
  * "center_support" — a mid-span support for long rods: a taller plate + arm
                       with a saddle that the rod rests in (always open-top so it
                       can be added under an already-hung rod).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rod_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bracket"))  # bracket | end_bracket | center_support
cradle_style = str(PARAM(lambda: cradle_style, "open"))   # open (C) | closed (ring)

rod_dia = float(PARAM(lambda: rod_dia, 19.0))            # rod diameter the cradle holds (mm)
projection = float(PARAM(lambda: projection, 70.0))      # rod centre distance from wall (mm)
cradle_wall = float(PARAM(lambda: cradle_wall, 4.0))     # wall of the cradle ring/C

plate_w = float(PARAM(lambda: plate_w, 32.0))           # wall-plate width
plate_thick = float(PARAM(lambda: plate_thick, 6.0))    # wall-plate thickness
arm_w = float(PARAM(lambda: arm_w, 14.0))               # support-arm width
arm_thick = float(PARAM(lambda: arm_thick, 10.0))       # support-arm thickness (load)

hole_spacing = float(PARAM(lambda: hole_spacing, 40.0))  # vertical screw-hole spacing
screw_dia = float(PARAM(lambda: screw_dia, 4.5))        # screw clearance hole

# Sanitize
rod_dia = max(6.0, rod_dia)
cradle_wall = max(2.0, cradle_wall)
arm_thick = max(4.0, arm_thick)
plate_thick = max(3.0, plate_thick)

r_rod = rod_dia / 2.0
r_out = r_rod + cradle_wall                               # cradle outer radius


# ── Building blocks ───────────────────────────────────────────────────────────
def _wall_plate(width, height):
    """Wall plate: front face at y=0, thickness toward -Y, base at z=0. The arm
    grows from the front face toward +Y (away from the wall)."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -plate_thick, 0))
        .box(width, plate_thick, height, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Y").fillet(min(width / 4.0, height / 6.0, 5.0))
    except Exception:
        pass
    return plate


def _drill_screws(plate, height):
    """Two vertical screw holes through the plate (bored toward -Y)."""
    r = screw_dia / 2.0
    if r <= 0.05:
        return plate
    zc = height / 2.0
    half = min(hole_spacing / 2.0, zc - (r + 3.0))
    zs = [zc - half, zc + half] if half > 1.0 else [zc]
    for z in zs:
        bore = (
            cq.Workplane("XZ")
            .center(0, z)
            .circle(r)
            .extrude(-(plate_thick + 2.0))
            .translate((0, 1.0, 0))
        )
        plate = plate.cut(bore)
    return plate


def _arm(z_center, length):
    """A horizontal support arm from the plate front (y=0) forward to y=-length,
    centred vertically on z_center. Overlaps ~2 mm back into the plate; callers
    size `length` so the far end plunges into the cradle ring wall (a real
    volumetric overlap, not a tangent contact)."""
    overlap = 2.0
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -length / 2.0 + overlap / 2.0, z_center))
        .box(arm_w, length + overlap, arm_thick, centered=(True, True, True))
    )
    try:
        arm = arm.edges("|X").fillet(min(arm_thick / 3.0, 2.0))
    except Exception:
        pass
    return arm


def _cradle(y_center, z_center, closed, end_cap=False):
    """The rod cradle at (y_center, z_center), axis along X so the rod runs
    left-right. `closed` → a full ring (rod threads through); else an open-top C
    (rod drops in). `end_cap` closes the outer (+X) face so the rod cannot slide
    off the run end. Returns the cradle solid."""
    depth = arm_w                                        # cradle length along X (rod axis)
    ring = (
        cq.Workplane("YZ")
        .circle(r_out)
        .circle(r_rod)
        .extrude(depth)
        .translate((-depth / 2.0, y_center, z_center))
    )
    if not closed:
        # Remove the top to make a C so the rod can drop in from above. The gap
        # is a touch narrower than the rod so it is lightly retained.
        gap_w = rod_dia * 0.85
        mouth = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y_center, z_center + r_rod * 0.35))
            .box(depth + 2.0, gap_w, r_out * 2.0, centered=(True, True, False))
        )
        ring = ring.cut(mouth)

    if end_cap:
        cap = (
            cq.Workplane("YZ")
            .circle(r_out)
            .extrude(cradle_wall)
            .translate((depth / 2.0, y_center, z_center))
        )
        ring = ring.union(cap)
    return ring


# ── Part builders ─────────────────────────────────────────────────────────────
def _closed_style():
    return cradle_style == "closed"


def build_bracket(end_cap=False):
    """Plate + arm + rod cradle at the set projection."""
    height = max(2.0 * r_out + 2.0 * 8.0, hole_spacing + 2.0 * (screw_dia + 6.0))
    z_center = height / 2.0

    body = _wall_plate(plate_w, height)
    body = _drill_screws(body, height)

    # Arm plunges into the near wall of the ring (past its inner surface) so the
    # union is a solid overlap, never a tangent contact.
    length = max(r_out + arm_thick, projection - r_rod * 0.4)
    body = body.union(_arm(z_center, length))

    y_cradle = -projection
    body = body.union(_cradle(y_cradle, z_center, _closed_style(), end_cap=end_cap))
    return body


def build_end_bracket():
    """A bracket whose cradle has a closing end cap on the outer face."""
    return build_bracket(end_cap=True)


def build_center_support():
    """A mid-span support: a taller plate + arm with an OPEN saddle the rod rests
    in (open so it can be slid under a rod already hung). Two arms flank the
    saddle for stiffness on long spans."""
    height = max(2.0 * r_out + 2.0 * 12.0, hole_spacing + 2.0 * (screw_dia + 8.0))
    z_center = height / 2.0

    body = _wall_plate(max(plate_w, arm_w * 2.0 + 8.0), height)
    body = _drill_screws(body, height)

    length = max(r_out + arm_thick, projection - r_rod * 0.4)
    # Two arms flanking the cradle for a stiffer mid-span support.
    for sx in (-1, 1):
        arm = _arm(z_center, length).translate((sx * (arm_w * 0.6), 0, 0))
        body = body.union(arm)

    # Open saddle cradle (never closed, so it can be added under a hung rod).
    y_cradle = -projection
    saddle = _cradle(y_cradle, z_center, closed=False)
    # Widen the saddle along X to span both arms.
    saddle2 = _cradle(y_cradle, z_center, closed=False).translate((arm_w * 0.6, 0, 0))
    saddle3 = _cradle(y_cradle, z_center, closed=False).translate((-arm_w * 0.6, 0, 0))
    body = body.union(saddle).union(saddle2).union(saddle3)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "end_bracket":
    result = build_end_bracket()
elif target_part == "center_support":
    result = build_center_support()
else:
    result = build_bracket()
