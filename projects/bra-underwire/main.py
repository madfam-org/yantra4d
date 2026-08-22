"""Bra Underwire + Tip Cap — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The sprung arc that shapes and supports a wired bra cup, plus the protective caps that
cover its ends so the wire never works through the channel fabric — the rigid hard good
the Fashion Cabinet `bra-underwire` notion places and bridges to here for its geometry.
It feeds the same `underwear_lounge` family as `hook-and-eye` (the back closure) and
`bra-ring-slider` (the strap adjusters). Printed in a springy filament (nylon, PETG) it
stands in for the steel wire; printed rigid it is a fitting/sizing gauge.

Modes (dispatched via `target_part`):
  * "set"     — one wire laid flat with the two tip caps beside it.
  * "wire"    — just the underwire arc.
  * "tip_cap" — just one tip cap.

Geometry: the wire is a full `cq.Solid.makeTorus` trimmed to a `sweep_deg` arc by two
oversized rotated half-space boxes (never a swept `radiusArc` path), with small filleted
cylinder end-caps closing the cut sections. The tip cap is a short closed tube: an outer
cylinder with a blind bore, rounded at the closed end. Small boolean count → watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cup_width`).
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
cup_width = float(PARAM(lambda: cup_width, 120.0))  # wire chord span = arc diameter (mm)
wire_d    = float(PARAM(lambda: wire_d,    2.5))    # wire section diameter (mm)
sweep_deg = float(PARAM(lambda: sweep_deg, 180.0))  # arc angular span (deg)
cap_len   = float(PARAM(lambda: cap_len,   8.0))    # tip cap length (mm)
cap_wall  = float(PARAM(lambda: cap_wall,  1.2))    # tip cap wall thickness (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|wire|tip_cap

# ── Safe clamps ──────────────────────────────────────────────────────────────
cup_width = max(80.0, min(cup_width, 160.0))
wire_d    = max(1.5, min(wire_d, 4.0))
sweep_deg = max(150.0, min(sweep_deg, 210.0))
cap_len   = max(5.0, min(cap_len, 12.0))
cap_wall  = max(0.8, min(cap_wall, 2.0))
# Cross-parameter: the cap must be longer than its own closed end wall, and the wire
# section must be small enough that the arc never self-intersects at the centre.
cap_wall = min(cap_wall, cap_len / 3.0)
wire_d   = min(wire_d, cup_width / 8.0)

arc_r = cup_width / 2.0          # torus centreline radius
sec_r = wire_d / 2.0             # torus tube radius
half_sweep = sweep_deg / 2.0     # arc is symmetric about +Y


def build_wire():
    """A `sweep_deg` arc of round wire, symmetric about +Y, with rounded ends.

    A full torus is cut by two oversized half-space boxes whose faces pass through the
    Z axis at the arc's end angles. For a sweep of 180 deg exactly, the two planes are
    collinear, so a single half-space is enough; beyond 180 deg the two boxes overlap
    and only their intersection (the wedge behind the arc) is removed, which is why the
    keep/remove sense is computed from the sweep rather than hard-coded.
    """
    torus = cq.Solid.makeTorus(
        arc_r, sec_r, pnt=cq.Vector(0, 0, 0), dir=cq.Vector(0, 0, 1)
    )
    body = cq.Workplane(obj=torus)

    big = cup_width * 3.0 + 20.0          # oversized: clears the torus in every direction
    tall = wire_d * 6.0 + 10.0

    def half_space(angle_deg, side):
        """A big box filling one side of the plane through Z at `angle_deg`.

        `side` = +1 keeps the box on the +normal side of that plane. The box is built
        centred on the origin then pushed `big/2` along its own local +Y before being
        rotated, so no box face is ever coincident with the cut plane's tangency.
        """
        box = (
            cq.Workplane("XY")
            .box(big, big, tall)
            .translate((0, side * (big / 2.0), 0))
            .rotate((0, 0, 0), (0, 0, 1), angle_deg)
        )
        return box

    if sweep_deg <= 180.0 + 1e-9:
        # Keep the wedge between the two end rays: remove the two outer half-spaces.
        # End rays sit at +/- half_sweep from +Y, i.e. at 90 +/- half_sweep in XY.
        body = body.cut(half_space(90.0 + half_sweep, -1))
        body = body.cut(half_space(90.0 - half_sweep, +1))
    else:
        # Sweep > 180: the removed wedge is the small one behind -Y. Its two bounding
        # planes are the same end rays; remove only their intersection.
        rem_a = half_space(90.0 + half_sweep, -1)
        rem_b = half_space(90.0 - half_sweep, +1)
        body = body.cut(rem_a.intersect(rem_b))

    # Rounded end-caps: a short filleted cylinder straddling each cut face, oriented
    # along the local tangent. It is pulled back INTO the arc by `bury` so its flat end
    # sits well inside solid material rather than coincident with the trimmed section.
    cap_l = wire_d * 1.4
    bury = wire_d * 0.5
    for sgn in (+1.0, -1.0):
        ang = math.radians(90.0 + sgn * half_sweep)
        cx = arc_r * math.cos(ang)
        cy = arc_r * math.sin(ang)
        # Tangent direction at that point, pointing OUT of the arc end.
        tx = sgn * math.sin(ang)
        ty = -sgn * math.cos(ang)
        # Cylinder axis along +X, spanning [-cap_l, 0] so its +X end is the free tip.
        plug = (
            cq.Workplane("XY")
            .circle(sec_r)
            .extrude(cap_l)
            .translate((0, 0, -cap_l))
            .rotate((0, 0, 0), (0, 1, 0), 90.0)
        )
        try:
            plug = plug.edges(">X").fillet(sec_r * 0.7)
        except Exception:
            pass
        plug = plug.rotate((0, 0, 0), (0, 0, 1), math.degrees(math.atan2(ty, tx)))
        body = body.union(plug.translate((cx - tx * bury, cy - ty * bury, 0)))
    return body


def build_tip_cap():
    """A short closed tube that slips over a wire end: outer cylinder, blind bore,
    rounded closed end."""
    outer_r = (wire_d + 2.0 * cap_wall) / 2.0
    cap = (
        cq.Workplane("XY")
        .circle(outer_r)
        .extrude(cap_len)
    )
    try:
        cap = cap.edges(">Z").fillet(min(outer_r * 0.6, cap_wall * 1.4))
    except Exception:
        pass
    bore_depth = max(1.0, cap_len - cap_wall)
    bore = (
        cq.Workplane("XY")
        .circle((wire_d + 0.3) / 2.0)
        .extrude(bore_depth)
        .translate((0, 0, -1.0))
    )
    return cap.cut(bore)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wire":
    result = build_wire()
elif target_part == "tip_cap":
    result = build_tip_cap()
else:
    gap = wire_d + 4.0
    cap_r = (wire_d + 2.0 * cap_wall) / 2.0
    y_off = -(arc_r + cap_r + gap)
    result = (
        build_wire()
        .union(build_tip_cap().translate((-(cap_r + gap / 2.0), y_off, 0)))
        .union(build_tip_cap().translate((+(cap_r + gap / 2.0), y_off, 0)))
    )
