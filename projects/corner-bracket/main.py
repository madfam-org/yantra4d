"""
Corner Bracket / Angle Gusset — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A simple angle bracket that joins two panels or boards at an angle. Two legs
meet at a configurable angle (default 90°); each leg carries a row of screw
holes with an optional countersink. Modes: a plain L-bracket, a T-bracket
(flat plate with a perpendicular leg), and a gusset bracket with a triangular
brace for extra stiffness.

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
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
angle         = float(PARAM(lambda: angle,         90.0))   # angle between legs (deg)
leg_a         = float(PARAM(lambda: leg_a,         40.0))   # length of leg A (mm)
leg_b         = float(PARAM(lambda: leg_b,         40.0))   # length of leg B (mm)
width         = float(PARAM(lambda: width,         30.0))   # bracket width (mm)
thickness     = float(PARAM(lambda: thickness,      4.0))   # material thickness (mm)
holes_per_leg = int(  PARAM(lambda: holes_per_leg,    2))   # screw holes per leg
screw_dia     = float(PARAM(lambda: screw_dia,      4.5))   # screw clearance hole dia (mm)
gusset        = bool( PARAM(lambda: gusset,        False))  # add triangular brace
countersink   = bool( PARAM(lambda: countersink,   False))  # flat counterbore for screw heads

target_part   = str(  PARAM(lambda: target_part, "L_bracket"))  # L_bracket|T_bracket|gusset_bracket

# ── Safe clamps ──────────────────────────────────────────────────────────────
angle = max(30.0, min(angle, 160.0))
leg_a = max(10.0, leg_a)
leg_b = max(10.0, leg_b)
width = max(8.0, width)
thickness = max(2.0, thickness)
holes_per_leg = max(0, min(holes_per_leg, 6))
screw_dia = max(1.5, min(screw_dia, width - 4.0))
CB_DEPTH = min(thickness * 0.5, screw_dia * 0.5)   # countersink (flat counterbore) depth
CB_DIA = screw_dia * 2.0                            # counterbore diameter


# ── Helpers ──────────────────────────────────────────────────────────────────
def leg_slab(length):
    """A flat slab lying on XY: X:[0, length], centered in Y (width), thickness
    in Z:[0, thickness]. This is one leg before it is rotated into place."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(length / 2.0, 0, thickness / 2.0))
        .box(length, width, thickness)
    )


def drill_row(solid, length, top_z):
    """Cut `holes_per_leg` screw holes down through a horizontal leg slab that
    spans X:[0, length] with its top face at z=top_z. Holes run along X, spaced
    evenly, centered in Y. Optional flat counterbore at the top face."""
    if holes_per_leg <= 0:
        return solid
    # Keep holes off the root (near the bend) and the tip.
    x0 = max(thickness + screw_dia, length * 0.18)
    x1 = length - max(screw_dia, length * 0.12)
    if x1 <= x0:
        x1 = x0 = length / 2.0
    for i in range(holes_per_leg):
        if holes_per_leg == 1:
            x = length / 2.0
        else:
            x = x0 + (x1 - x0) * i / (holes_per_leg - 1)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, top_z - thickness / 2.0))
            .cylinder(thickness + 2.0, screw_dia / 2.0)
        )
        solid = solid.cut(hole)
        if countersink:
            cb = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0, top_z - CB_DEPTH / 2.0 + 0.01))
                .cylinder(CB_DEPTH, CB_DIA / 2.0)
            )
            solid = solid.cut(cb)
    return solid


def build_bend_bracket(brace):
    """Two legs meeting at the bend. Leg A lies flat on XY along +X. Leg B is
    built flat then rotated about the Y axis at the origin by `angle` so it
    stands up. A shared corner block fuses the bend into one watertight solid.
    If `brace`, add a triangular gusset in the XZ plane spanning both legs."""
    a = leg_slab(leg_a)
    a = drill_row(a, leg_a, thickness)

    # Leg B: build flat, drill, then rotate up about the bend line (Y axis at x=0).
    b = leg_slab(leg_b)
    b = drill_row(b, leg_b, thickness)
    b = b.rotate((0, 0, 0), (0, 1, 0), angle)

    body = a.union(b)

    if brace:
        body = body.union(_gusset()).clean()
    return body


def _gusset():
    """A full-width triangular brace bridging the two legs in the XZ plane,
    extruded across the whole bracket width. Its base runs `reach` along leg A
    and its hypotenuse rises to `reach` along leg B; the triangle's contact
    vertices are pushed slightly into the leg material (overlap `ov`) so the
    boolean fuse produces no coincident faces. Full width means the brace's Y
    end-faces coincide with the legs' — they merge cleanly and the result stays
    a watertight, manifold solid at every angle. Sized to a fraction of the
    shorter leg so the brace never overhangs a leg tip."""
    reach = min(leg_a, leg_b) * 0.7
    reach = max(reach, thickness * 2.0)
    a_rad = math.radians(angle)
    ux, uz = math.cos(a_rad), math.sin(a_rad)
    ov = thickness * 0.8
    tri = (
        cq.Workplane("XZ")
        .polyline([
            (-ov, -ov),                          # buried past the bend outer corner
            (reach, -ov),                        # along leg A, dipped below its base
            (reach * ux - ov * ux, reach * uz - ov * uz),  # up leg B, dipped into it
        ])
        .close()
        .extrude(width)
    )
    # `extrude` on XZ pushes along -Y from y=0; recenter across the full width.
    return tri.translate((0, width / 2.0, 0))


def build_L():
    """Plain L-bracket at the set angle (90° by default)."""
    return build_bend_bracket(brace=False)


def build_gusset_bracket():
    """L-bracket with a triangular brace."""
    return build_bend_bracket(brace=True)


def build_T():
    """T-bracket: a flat base plate with a perpendicular leg rising from its
    center, for T-joints. The upright fuses to the plate as one solid."""
    # Base plate spans X:[-leg_a/2, +leg_a/2] on z=0.
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, thickness / 2.0))
        .box(leg_a, width, thickness)
    )
    # Drill the plate: two holes near each end along X.
    if holes_per_leg > 0:
        n = holes_per_leg
        xend = leg_a / 2.0 - max(screw_dia, leg_a * 0.1)
        for i in range(n):
            x = -xend + (2.0 * xend) * (i / (n - 1)) if n > 1 else 0.0
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0, thickness / 2.0))
                .cylinder(thickness + 2.0, screw_dia / 2.0)
            )
            plate = plate.cut(hole)
            if countersink:
                cb = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(x, 0, thickness - CB_DEPTH / 2.0 + 0.01))
                    .cylinder(CB_DEPTH, CB_DIA / 2.0)
                )
                plate = plate.cut(cb)

    # Upright leg B rising from the plate center, standing in Z.
    upright = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, thickness + leg_b / 2.0))
        .box(thickness, width, leg_b)
    )
    # Drill the upright: holes through its thickness (along X), spaced up Z.
    if holes_per_leg > 0:
        n = holes_per_leg
        z0 = thickness + max(screw_dia, leg_b * 0.18)
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


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "T_bracket":
    result = build_T()
elif target_part == "gusset_bracket" or gusset:
    result = build_gusset_bracket()
else:
    result = build_L()
