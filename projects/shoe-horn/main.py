"""Shoe Horn — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The classic curved shoe horn: a blade that slides between a heel and a shoe's heel counter
so the foot glides in without the counter folding under. Folding a counter once is what
kills a dress shoe — the crease never comes out and the shoe stops holding the heel. The
blade widens and dishes as it runs from a narrow handle to a broad heel scoop, and the whole
thing is a single solid so it prints and washes as one piece.

Modes (dispatched via `target_part`):
  * "short" — the pocket/travel horn: hand length, tight curve.
  * "long"  — the long-handled horn used standing up, no bending required — the accessible
              version for anyone who cannot reach their own heel.
  * "set"   — one of each on a plate.

Geometry: the blade is ONE `cq.Solid.makeLoft` through a stack of closed rounded-rect wires
marched along a circular-arc spine, each wire wider and shallower than the last and each
rotated to stay normal to the spine. Both end wires are FLAT closed sections — no sphere
caps, no loft to a point, so there are no pole singularities. Because the loft is the whole
body, nothing is ever extruded off a loft face via toPending. The hang hole is a single
cylinder cut through the handle end, overshooting both faces so it drains.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `horn_len`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
horn_len   = float(PARAM(lambda: horn_len,   190.0))  # blade length along the spine (mm)
handle_w   = float(PARAM(lambda: handle_w,   16.0))   # width at the handle end (mm)
scoop_w    = float(PARAM(lambda: scoop_w,    42.0))   # width at the heel scoop (mm)
blade_t    = float(PARAM(lambda: blade_t,    3.4))    # blade thickness (mm)
curve_deg  = float(PARAM(lambda: curve_deg,  62.0))   # total spine curvature (degrees)
hang_hole  = float(PARAM(lambda: hang_hole,  6.0))    # hang-hole diameter, 0 = none (mm)
sections   = int(  PARAM(lambda: sections,   14))     # loft sections along the spine

target_part = str(PARAM(lambda: target_part, "short"))  # short|long|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
horn_len  = max(90.0, min(horn_len, 620.0))
handle_w  = max(8.0, min(handle_w, 40.0))
scoop_w   = max(handle_w + 4.0, min(scoop_w, 80.0))
blade_t   = max(1.8, min(blade_t, 8.0))
curve_deg = max(15.0, min(curve_deg, 110.0))
hang_hole = max(0.0, min(hang_hole, handle_w * 0.5))
sections  = max(8, min(sections, 28))

# Spine: a circular arc of total sweep curve_deg over an arc length of horn_len.
_sweep = math.radians(curve_deg)
spine_r = horn_len / _sweep


def _section_wire(u):
    """One closed rounded-rect blade section at spine parameter u in [0, 1].

    The section is built flat in its own local frame, then rotated to stay normal to the
    arc spine and translated onto it. Both ends are real closed wires — never a point.
    """
    # Width grows from handle to scoop with an ease-in so the handle stays slender.
    w = handle_w + (scoop_w - handle_w) * (u ** 1.6)
    # Thickness tapers slightly toward the scoop so the tip slips behind the counter.
    t = blade_t * (1.0 - 0.35 * u)
    r = min(t * 0.48, w * 0.24)

    ang = _sweep * u
    # Spine point: arc centred at (0, spine_r) opening downward in the XZ plane.
    px = spine_r * math.sin(ang)
    pz = spine_r * (1.0 - math.cos(ang))
    # Local axes: `tangent` along the spine (XZ), `across` the blade width (Y).
    tx, tz = math.cos(ang), math.sin(ang)
    # Section normal is the tangent; section plane is spanned by Y and (-tz, 0, tx).
    nx, nz = -tz, tx

    hw = w / 2.0
    ht = t / 2.0
    corner = max(0.15, min(r, ht - 0.05, hw - 0.05))

    def P(across, thru):
        """Map a local (width, thickness) coordinate onto the section plane in 3D."""
        return cq.Vector(px + nx * thru, across, pz + nz * thru)

    a = hw - corner
    b = ht - corner
    k = 0.70710678
    edges = [
        cq.Edge.makeLine(P(-a, -ht), P(a, -ht)),
        cq.Edge.makeThreePointArc(P(a, -ht), P(a + corner * k, -b - corner * k), P(hw, -b)),
        cq.Edge.makeLine(P(hw, -b), P(hw, b)),
        cq.Edge.makeThreePointArc(P(hw, b), P(a + corner * k, b + corner * k), P(a, ht)),
        cq.Edge.makeLine(P(a, ht), P(-a, ht)),
        cq.Edge.makeThreePointArc(P(-a, ht), P(-a - corner * k, b + corner * k), P(-hw, b)),
        cq.Edge.makeLine(P(-hw, b), P(-hw, -b)),
        cq.Edge.makeThreePointArc(P(-hw, -b), P(-a - corner * k, -b - corner * k), P(-a, -ht)),
    ]
    return cq.Wire.assembleEdges(edges)


def build_horn():
    """One lofted blade: flat closed section at each end, no caps, one solid."""
    wires = [_section_wire(i / float(sections - 1)) for i in range(sections)]
    body = cq.Workplane(obj=cq.Solid.makeLoft(wires, True))

    if hang_hole > 0.05:
        # Hang hole through the handle end, a little in from the tip. The cutter
        # overshoots both blade faces so the hole is a real through hole that drains.
        u = 0.045
        ang = _sweep * u
        px = spine_r * math.sin(ang)
        pz = spine_r * (1.0 - math.cos(ang))
        depth = blade_t * 4.0 + 6.0
        cutter = (
            cq.Workplane("XY")
            .circle(hang_hole / 2.0)
            .extrude(depth)
            .translate((0, 0, -depth / 2.0))
            # Lay the bore normal to the blade face: rotate the Z axis onto the spine
            # normal, then move it onto the spine point.
            .rotate((0, 0, 0), (0, 1, 0), 90.0 - curve_deg * u)
            .translate((px, 0, pz))
        )
        body = body.cut(cutter)
    return body


def _compound(solids):
    """Separate bodies on one plate — a Compound, never a union of non-touching solids."""
    shapes = []
    for s in solids:
        shapes.extend(s.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "long":
    # The long horn: same blade, stretched spine and a straighter run so it reaches the
    # floor from standing. Rebuild the derived spine before lofting.
    horn_len = max(horn_len, 380.0)
    curve_deg = min(curve_deg, 40.0)
    _sweep = math.radians(curve_deg)
    spine_r = horn_len / _sweep
    result = build_horn()
elif target_part == "set":
    _short = build_horn()
    _short_w = scoop_w
    # Long variant rebuilt with its own spine, laid alongside in Y.
    horn_len = max(horn_len, 380.0)
    curve_deg = min(curve_deg, 40.0)
    _sweep = math.radians(curve_deg)
    spine_r = horn_len / _sweep
    _long = build_horn().translate((0.0, _short_w + max(8.0, scoop_w * 0.2), 0.0))
    result = _compound([_short, _long])
else:
    result = build_horn()
