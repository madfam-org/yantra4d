"""
Molecule / Atom Model Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A ball-and-stick molecular modelling set. Atoms are spheres bored with bond
sockets at the REAL VSEPR bond angles, and bonds are struts that plug into the
sockets, so any atom of a given geometry connects to any bond. Three
interoperating pieces:

  - atom      : a sphere with N bond sockets at a chosen molecular geometry
                (tetrahedral 109.5 deg, trigonal-planar 120 deg, linear 180 deg,
                octahedral 90 deg, or bent).
  - bond      : a straight single-bond strut with a reduced-diameter plug at each
                end that press-fits the socket.
  - double_bond: two parallel plug struts joined by a central web — the pi-bond /
                double-bond connector for C=C, C=O, etc.

Interoperable figures (cited as the CDG `standard` = "internal bond socket"):
  - socket diameter     = 4.0 mm     (bore the bond plug enters)
  - socket depth        = 6.0 mm
  - bond plug diameter  = socket_dia - fit  (a press fit, e.g. 3.7 mm)
  - bond angles         = 109.5 / 120 / 180 / 90 deg (VSEPR)

Watertight strategy:
  The atom is a sphere; each socket is a blind cylindrical bore that opens to the
  sphere SURFACE (vents to outside) and stops on solid material inside — no
  trapped void. Bores are cut from a start point just outside the surface inward,
  so the mouth is guaranteed open. The bond is a solid cylinder (single manifold)
  with unioned plug tips. The double bond is two solid strut cylinders unioned to
  a central web bar (overlapping solids). No hollow-with-sealed-cavity, no
  revolve-of-cut. Sockets never reach the centre (depth capped < radius) so
  opposite sockets can't tunnel into a shared cavity.

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
target_part = str(PARAM(lambda: target_part, "atom"))
# "atom" | "bond" | "double_bond"

geometry = str(PARAM(lambda: geometry, "tetrahedral"))
# "tetrahedral" | "trigonal" | "linear" | "bent" | "octahedral"

atom_dia = float(PARAM(lambda: atom_dia, 18.0))       # atom sphere diameter (mm)
socket_dia = float(PARAM(lambda: socket_dia, 4.0))    # bond socket bore diameter (mm)
socket_depth = float(PARAM(lambda: socket_depth, 6.0))  # socket depth (mm)

bond_len = float(PARAM(lambda: bond_len, 30.0))       # bond overall length (mm)
bond_dia = float(PARAM(lambda: bond_dia, 6.0))        # bond body diameter (mm)
plug_fit = float(PARAM(lambda: plug_fit, 0.3))        # plug undersize vs socket (press fit)
plug_len = float(PARAM(lambda: plug_len, 5.5))        # plug length at each end (mm)

double_gap = float(PARAM(lambda: double_gap, 7.0))    # centre-to-centre of the twin struts (mm)

# ── Clamp inputs ─────────────────────────────────────────────────────────────
atom_dia = max(8.0, min(atom_dia, 40.0))
socket_dia = max(2.0, min(socket_dia, atom_dia * 0.32))
# Cap depth so two opposite sockets always leave a solid core between them:
# core per side must exceed the socket radius + 1 mm.
_R_tmp = atom_dia / 2.0
socket_depth = max(2.0, min(socket_depth, _R_tmp - socket_dia / 2.0 - 1.5))
bond_len = max(10.0, min(bond_len, 120.0))
bond_dia = max(2.5, min(bond_dia, 14.0))
plug_fit = max(0.0, min(plug_fit, 1.0))
plug_len = max(2.0, min(plug_len, socket_depth + 0.5))
double_gap = max(bond_dia + 0.5, min(double_gap, 20.0))

R = atom_dia / 2.0
plug_dia = max(1.0, socket_dia - plug_fit)


# ── Bond direction sets (unit vectors) per molecular geometry ────────────────
def _bond_dirs(geom):
    """Return a list of unit (x, y, z) bond directions for the given geometry."""
    if geom == "linear":
        return [(0, 0, 1), (0, 0, -1)]
    if geom == "bent":
        # ~104.5 deg (water). Two bonds symmetric about +Z in the XZ plane.
        half = math.radians(104.5 / 2.0)
        return [(math.sin(half), 0, math.cos(half)),
                (-math.sin(half), 0, math.cos(half))]
    if geom == "trigonal":
        # 120 deg in the XY plane.
        return [(math.cos(math.radians(a)), math.sin(math.radians(a)), 0)
                for a in (90, 210, 330)]
    if geom == "octahedral":
        return [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    # tetrahedral (default): 109.47 deg. Classic cube-diagonal directions.
    k = 1.0 / math.sqrt(3.0)
    return [(k, k, k), (k, -k, -k), (-k, k, -k), (-k, -k, k)]


def _icosphere(radius, subdiv):
    """Vertices + triangular faces of a subdivided icosahedron, normalised to
    `radius`. A true polyhedron — watertight by construction. Using a FACETED
    ball (not the OCCT sphere) is what makes oblique socket cuts tessellate
    cleanly: a cylinder crossing planar faces gives clean arcs, whereas a
    cylinder tangent to a curved sphere leaves a degenerate sliver at the
    tangency point."""
    t = (1.0 + math.sqrt(5.0)) / 2.0
    verts = [
        [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
        [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
        [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
    ]
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    mid = {}

    def _midpoint(a, b):
        key = (a, b) if a < b else (b, a)
        if key in mid:
            return mid[key]
        va, vb = verts[a], verts[b]
        verts.append([(va[i] + vb[i]) / 2.0 for i in range(3)])
        mid[key] = len(verts) - 1
        return mid[key]

    for _ in range(subdiv):
        nf = []
        for (a, b, c) in faces:
            ab = _midpoint(a, b)
            bc = _midpoint(b, c)
            ca = _midpoint(c, a)
            nf.extend([(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)])
        faces = nf

    out = []
    for v in verts:
        nrm = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
        out.append((v[0] / nrm * radius, v[1] / nrm * radius, v[2] / nrm * radius))
    return out, faces


def _poly_ball(radius, subdiv):
    """Build the faceted ball as a solid from its polyhedral faces."""
    verts, faces = _icosphere(radius, subdiv)
    cq_faces = []
    for f in faces:
        pts = [cq.Vector(*verts[i]) for i in f]
        wire = cq.Wire.makePolygon(pts + [pts[0]])
        cq_faces.append(cq.Face.makeFromWires(wire))
    shell = cq.Shell.makeShell(cq_faces)
    return cq.Solid.makeSolid(shell)


def _socket_cutter(direction):
    """A socket bore aligned to `direction`, cut into the faceted ball. Starts
    just outside the surface (open mouth) and reaches `socket_depth` inward,
    stopping short of the centre so opposite sockets never share a cavity."""
    dx, dy, dz = direction
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    ux, uy, uz = dx / n, dy / n, dz / n
    r = socket_dia / 2.0
    start_out = 1.0
    inner = R - socket_depth
    length = (R + start_out) - inner
    base = cq.Vector(ux * inner, uy * inner, uz * inner)
    axis = cq.Vector(ux, uy, uz)
    return cq.Solid.makeCylinder(r, length, base, axis)


def build_atom():
    """A faceted ball with bond sockets bored at the geometry's real bond angles.
    Sockets vent to the surface (open mouth) and stop inside solid material — no
    trapped void. The faceted ball keeps every oblique socket cut watertight."""
    body = cq.Workplane(obj=_poly_ball(R, 2))   # 320-face ball
    for d in _bond_dirs(geometry):
        body = body.cut(cq.Workplane(obj=_socket_cutter(d)))
    return body


def _strut(length, body_d, plug_d, plug_l):
    """A single bond strut along +Z centred at origin: body + a plug at each end.
    body spans [-body_half .. body_half]; plugs extend beyond by plug_l."""
    body_half = length / 2.0
    body = (
        cq.Workplane("XY")
        .circle(body_d / 2.0)
        .extrude(body_half, both=True)
    )
    top_plug = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, body_half - 0.01))
        .circle(plug_d / 2.0)
        .extrude(plug_l + 0.01)
    )
    bot_plug = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -body_half - plug_l + 0.01))
        .circle(plug_d / 2.0)
        .extrude(plug_l + 0.01)
    )
    return body.union(top_plug).union(bot_plug)


def build_bond():
    """A straight single-bond strut with a press-fit plug at each end."""
    body_len = max(4.0, bond_len - 2.0 * plug_len)
    return _strut(body_len, bond_dia, plug_dia, plug_len)


def build_double_bond():
    """Two parallel plug struts joined by a central web → double / pi bond."""
    body_len = max(4.0, bond_len - 2.0 * plug_len)
    strut_d = min(bond_dia, double_gap - 0.5)
    s1 = _strut(body_len, strut_d, plug_dia, plug_len).translate((double_gap / 2.0, 0, 0))
    s2 = _strut(body_len, strut_d, plug_dia, plug_len).translate((-double_gap / 2.0, 0, 0))
    combo = s1.union(s2)
    # Central web bar tying the two struts (overlaps both), short so plug ends
    # stay clear.
    web_h = min(body_len * 0.5, body_len - 2.0)
    web = (
        cq.Workplane("XY")
        .box(double_gap + strut_d, strut_d * 0.7, web_h, centered=(True, True, True))
    )
    return combo.union(web)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bond":
    result = build_bond()
elif target_part == "double_bond":
    result = build_double_bond()
else:
    result = build_atom()
