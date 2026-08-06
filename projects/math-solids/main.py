"""
Math Manipulatives / Solids — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Geometric manipulatives for the maths classroom: the five Platonic solids, a
regular N-gon prism for surface-area / volume work, and pie-slice fraction tiles.
All pieces share a nominal size grid so a set stacks and compares cleanly.

  - platonic     : a selectable Platonic solid (tetrahedron, cube, octahedron,
                   dodecahedron, icosahedron) at a target circumscribed size.
  - prism        : a regular N-gon prism (parametric sides + height) for
                   area = (1/2) n s a and volume = base-area x height lessons.
  - fraction_tile: a 1/denominator pie slice (a circular sector, optionally an
                   annulus) — snap `denominator` tiles into a whole circle.

Interoperable figure (cited as the CDG `standard` = "internal solids 40mm"):
  - nominal size = 40 mm  (Platonic circumscribed diameter / prism across-corners
                           / fraction-tile outer diameter) — a shared reference so
                           the manipulatives are size-comparable.

Watertight strategy:
  Platonic solids are true POLYHEDRA built from their exact vertex + face tables
  (convex, watertight by construction). The prism is one extrusion of a regular
  polygon (watertight). The fraction tile is an extrusion of a closed sector wire
  (two radii + an arc, closed) — a solid wedge, watertight; the optional annulus
  cuts a smaller concentric sector that shares the same two radii so the result
  stays a single closed solid. No spheres, no oblique curved booleans, no
  revolve-of-cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>); render worker injects
    target_part = <mode.parts[0]>. Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "platonic"))
# "platonic" | "prism" | "fraction_tile"

solid = str(PARAM(lambda: solid, "cube"))
# "tetrahedron" | "cube" | "octahedron" | "dodecahedron" | "icosahedron"
size = float(PARAM(lambda: size, 40.0))               # nominal circumscribed size (mm)

sides = int(PARAM(lambda: sides, 6))                  # prism polygon sides
prism_h = float(PARAM(lambda: prism_h, 30.0))         # prism height (mm)
prism_dia = float(PARAM(lambda: prism_dia, 40.0))     # prism across-corners diameter (mm)

denominator = int(PARAM(lambda: denominator, 4))      # fraction tile = 1/denominator
tile_dia = float(PARAM(lambda: tile_dia, 40.0))       # fraction tile outer diameter (mm)
tile_h = float(PARAM(lambda: tile_h, 8.0))            # fraction tile thickness (mm)
tile_hole = float(PARAM(lambda: tile_hole, 0.0))      # central hole diameter (annulus); 0 = full

# ── Clamp inputs ─────────────────────────────────────────────────────────────
size = max(10.0, min(size, 120.0))
sides = max(3, min(sides, 12))
prism_h = max(3.0, min(prism_h, 120.0))
prism_dia = max(10.0, min(prism_dia, 120.0))
denominator = max(2, min(denominator, 12))
tile_dia = max(10.0, min(tile_dia, 120.0))
tile_h = max(2.0, min(tile_h, 30.0))
tile_hole = max(0.0, min(tile_hole, tile_dia - 4.0))


# ── Platonic solid vertex + face tables ──────────────────────────────────────
def _platonic(name):
    """Return (verts, faces) for the named Platonic solid, normalised so the
    circumradius is 1. Faces are lists of vertex indices (planar polygons)."""
    phi = (1.0 + math.sqrt(5.0)) / 2.0

    if name == "tetrahedron":
        v = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
        f = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
    elif name == "octahedron":
        v = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
             (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    elif name == "dodecahedron":
        a, b = 1.0 / phi, phi
        v = [
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
            (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
            (0, a, b), (0, a, -b), (0, -a, b), (0, -a, -b),
            (a, b, 0), (a, -b, 0), (-a, b, 0), (-a, -b, 0),
            (b, 0, a), (b, 0, -a), (-b, 0, a), (-b, 0, -a),
        ]
        f = [
            (0, 8, 10, 2, 16), (0, 16, 17, 1, 12), (0, 12, 14, 4, 8),
            (1, 17, 3, 11, 9), (1, 9, 5, 14, 12), (2, 10, 6, 15, 13),
            (2, 13, 3, 17, 16), (3, 13, 15, 7, 11), (4, 14, 5, 19, 18),
            (4, 18, 6, 10, 8), (5, 9, 11, 7, 19), (6, 18, 19, 7, 15),
        ]
    elif name == "icosahedron":
        v = [
            (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
            (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
            (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
        ]
        f = [
            (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
            (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
            (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
            (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
        ]
    else:  # cube
        v = [
            (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
            (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
        ]
        f = [
            (0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4),
            (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6),
        ]

    # Normalise to unit circumradius.
    scale = 1.0 / math.sqrt(v[0][0] ** 2 + v[0][1] ** 2 + v[0][2] ** 2)
    v = [(x * scale, y * scale, z * scale) for (x, y, z) in v]
    return v, f


def _poly_solid(verts, faces):
    cq_faces = []
    for f in faces:
        pts = [cq.Vector(*verts[i]) for i in f]
        wire = cq.Wire.makePolygon(pts + [pts[0]])
        cq_faces.append(cq.Face.makeFromWires(wire))
    shell = cq.Shell.makeShell(cq_faces)
    return cq.Solid.makeSolid(shell)


def build_platonic():
    """A Platonic solid at circumscribed diameter `size`, resting on the XY plane."""
    verts, faces = _platonic(solid)
    r = size / 2.0
    verts = [(x * r, y * r, z * r) for (x, y, z) in verts]
    body = cq.Workplane(obj=_poly_solid(verts, faces))
    # Drop so the lowest vertex sits on z=0 (a manipulative sitting on a desk).
    zmin = min(vz for (_, _, vz) in verts)
    body = body.translate((0, 0, -zmin))
    return body


def build_prism():
    """A regular N-gon prism of across-corners diameter `prism_dia`, height `prism_h`."""
    r = prism_dia / 2.0
    pts = []
    for i in range(sides):
        a = 2.0 * math.pi * i / sides + math.pi / 2.0   # point-up
        pts.append((r * math.cos(a), r * math.sin(a)))
    body = cq.Workplane("XY").polyline(pts).close().extrude(prism_h)
    return body


def build_fraction_tile():
    """A 1/denominator pie slice — a circular sector, optionally an annulus."""
    r_out = tile_dia / 2.0
    sweep = 2.0 * math.pi / denominator
    steps = max(6, int(math.degrees(sweep) / 4.0))

    # Outer arc points from angle 0 to sweep.
    outer = [(r_out * math.cos(sweep * k / steps), r_out * math.sin(sweep * k / steps))
             for k in range(steps + 1)]

    if tile_hole > 0.2:
        r_in = tile_hole / 2.0
        inner = [(r_in * math.cos(sweep * k / steps), r_in * math.sin(sweep * k / steps))
                 for k in range(steps + 1)]
        # Sector annulus: outer arc forward, then inner arc backward → closed ring wedge.
        pts = outer + list(reversed(inner))
    else:
        # Full pie slice: centre → outer arc → back to centre.
        pts = [(0.0, 0.0)] + outer

    body = cq.Workplane("XY").polyline(pts).close().extrude(tile_h)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "prism":
    result = build_prism()
elif target_part == "fraction_tile":
    result = build_fraction_tile()
else:
    result = build_platonic()
