"""
Magnetic Tool Strip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall-mounted magnetic strip that holds screwdrivers, pliers, knives, and other
steel tools on a row of embedded disc magnets. The magnets drop into blind
pockets on the FRONT face; wall screws pass through countersunk holes on the
ends (or back). Glue the magnets in, screw the strip up, and tools snap on.

Three modes (rendered per-part via `target_part`):

  * "strip"       — a flat magnetic bar: magnet pockets on the front, wall
                    screw holes near the ends.
  * "shelf_strip" — the flat strip plus a small bottom ledge/lip so heavier
                    tools rest on a shelf as well as stick to the magnets.
  * "corner_strip"— an L-section strip that wraps an inside wall corner, with the
                    magnet row on the main face (holds tools around the corner).

Magnet pockets are all cut in ONE `pushPoints` operation. Magnet size is
parametric — the common ferrite/neodymium disc sizes 6×2 mm and 8×3 mm are
presets.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `length`).
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
target_part = str(PARAM(lambda: target_part, "strip"))  # strip|shelf_strip|corner_strip

length = float(PARAM(lambda: length, 200.0))       # strip length (mm)
height = float(PARAM(lambda: height, 25.0))        # strip face height (mm)
thickness = float(PARAM(lambda: thickness, 8.0))   # strip body thickness (mm)

magnet_dia = float(PARAM(lambda: magnet_dia, 6.0))   # disc magnet diameter (mm)
magnet_th = float(PARAM(lambda: magnet_th, 2.0))     # disc magnet thickness / pocket depth (mm)
magnet_count = int(PARAM(lambda: magnet_count, 6))   # number of magnet pockets
magnet_wall = float(PARAM(lambda: magnet_wall, 1.2)) # material left behind a pocket (mm)

wall_screw = float(PARAM(lambda: wall_screw, 4.5))   # wall screw clearance dia (mm)
countersink = bool(PARAM(lambda: countersink, True)) # countersink the wall screws

ledge_depth = float(PARAM(lambda: ledge_depth, 15.0))  # bottom shelf depth (shelf_strip) (mm)
leg_b = float(PARAM(lambda: leg_b, 25.0))              # second leg height (corner_strip) (mm)


# ── Active part ──────────────────────────────────────────────────────────────
_parts = ("strip", "shelf_strip", "corner_strip")
active = target_part if target_part in _parts else "strip"

# ── Safe clamps ──────────────────────────────────────────────────────────────
length = max(40.0, length)
height = max(12.0, height)
thickness = max(4.0, thickness)
magnet_dia = max(2.0, min(magnet_dia, height - 4.0))
magnet_th = max(1.0, magnet_th)
magnet_count = max(1, min(magnet_count, 40))
magnet_wall = max(0.6, magnet_wall)
# Pocket must not break through the back: cap depth to leave magnet_wall behind.
pocket_depth = max(1.0, min(magnet_th, thickness - magnet_wall))
wall_screw = max(1.5, min(wall_screw, height - 4.0))
countersink = bool(countersink)
ledge_depth = max(5.0, ledge_depth)
leg_b = max(10.0, leg_b)


# ── Shared helpers (reused across the batch) ──────────────────────────────────
def bar(length_x, height_z, thick_y):
    """The strip body: X:[-L/2, L/2], Z:[0, height], thickness in Y:[0, thick].
    The back face (y=0) mounts to the wall; the front face (y=thick) carries the
    magnets and faces the room."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, thick_y / 2.0, height_z / 2.0))
        .box(length_x, thick_y, height_z)
    )


def magnet_points():
    """Evenly spaced magnet-pocket centres along the strip, on the face
    mid-height. Returns (x, z) points in the strip's XZ face plane."""
    z = height / 2.0
    if magnet_count == 1:
        return [(0.0, z)]
    margin = max(magnet_dia, length * 0.06)
    x0 = -length / 2.0 + margin
    x1 = length / 2.0 - margin
    if x1 <= x0:
        return [(0.0, z)]
    step = (x1 - x0) / (magnet_count - 1)
    return [(x0 + i * step, z) for i in range(magnet_count)]


def cut_magnet_pockets(body, front_y):
    """Cut ALL magnet pockets in one pushPoints operation, as blind bores into
    the FRONT face at y=front_y, sunk `pocket_depth` toward the wall. Because
    the pockets never reach the back (a `magnet_wall` web remains), the strip
    stays watertight."""
    pts = magnet_points()
    if not pts or magnet_dia <= 0.05:
        return body
    r = magnet_dia / 2.0
    # Work on the front XZ face plane (normal -Y into the body). Push all points,
    # bore one cylinder per point, sunk pocket_depth (+0.02 over-travel out).
    pockets = (
        cq.Workplane("XZ")
        .pushPoints(pts)
        .circle(r)
        .extrude(pocket_depth + 0.02)
        .translate((0, front_y + 0.02, 0))
    )
    return body.cut(pockets)


def wall_screw_points():
    """Two wall-screw centres near the strip ends, on the vertical mid-line."""
    x = length / 2.0 - max(wall_screw, length * 0.05)
    z = height / 2.0
    if x <= 0:
        return [(0.0, z)]
    return [(-x, z), (x, z)]


def cut_wall_screws(body, thick_y):
    """Drill the wall screws THROUGH the strip thickness (in Y), from the front
    face, with an optional countersink cone on the front so heads sit flush."""
    r = wall_screw / 2.0
    for (x, z) in wall_screw_points():
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, z, 0))
            .cylinder(thick_y + 2.0, r)
            .translate((0, thick_y / 2.0, 0))
        )
        body = body.cut(hole)
        if countersink:
            # Cone widening toward the front face (y=thick_y).
            cone = (
                cq.Workplane("XZ")
                .transformed(offset=cq.Vector(x, z, 0))
                .circle(r)
                .workplane(offset=r * 1.2)
                .circle(r * 2.0)
                .loft()
                .translate((0, thick_y - r * 1.2, 0))
            )
            body = body.cut(cone)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_strip():
    """Flat magnetic bar."""
    body = bar(length, height, thickness)
    body = cut_magnet_pockets(body, thickness)
    body = cut_wall_screws(body, thickness)
    return body


def build_shelf_strip():
    """Flat strip plus a bottom ledge sticking out in +Y so tools can rest on a
    small shelf as well as stick to the magnets."""
    body = bar(length, height, thickness)

    ledge = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, thickness + ledge_depth / 2.0, thickness / 2.0)
        )
        .box(length, ledge_depth, thickness)
    )
    # Small upstand lip at the ledge's outer edge to stop tools rolling off.
    lip = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(
                0, thickness + ledge_depth - thickness / 2.0, thickness + thickness / 2.0
            )
        )
        .box(length, thickness, thickness)
    )
    body = body.union(ledge).union(lip)

    body = cut_magnet_pockets(body, thickness)
    body = cut_wall_screws(body, thickness)
    return body.clean()


def build_corner_strip():
    """L-section strip wrapping an inside wall corner: the main face (leg A)
    carries the magnet row; a second leg (leg B) wraps around the corner so the
    strip screws to both wall faces. Built as two bars fused at the corner."""
    body = bar(length, height, thickness)

    # Second leg: a bar standing in the YZ plane, along +Y at the back edge,
    # sharing the corner at y in [0, thickness].
    legb = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, thickness / 2.0, height / 2.0)
        )
        .box(length, thickness, height)
    )
    # Move leg B so it juts along +Y as a wall-hugging return; rotate it up so it
    # forms an L in the XZ→XY sense: place it as a horizontal return along +Y at
    # the strip's back, thickness deep.
    legb = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, leg_b / 2.0, thickness / 2.0))
        .box(length, leg_b, thickness)
    )
    body = body.union(legb)

    body = cut_magnet_pockets(body, thickness)
    body = cut_wall_screws(body, thickness)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "shelf_strip":
    result = build_shelf_strip()
elif active == "corner_strip":
    result = build_corner_strip()
else:
    result = build_strip()
