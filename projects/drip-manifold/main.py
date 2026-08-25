"""
Drip Irrigation Manifold — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A multi-outlet distributor for standard US micro-drip irrigation. It takes one
supply feed and splits it to several 1/4 in barbed outlets. The 1/4 in drip barb
is the interoperable interface (nominal 1/4 in tubing: ID ~4.3 mm / 0.170 in,
OD ~6.4 mm; the ribbed barb spigot is ~5-6 mm across) — the SAME barb the
`drip-fitting` cartridge produces, so hoses and fittings interoperate across the
drip-irrigation family.

Three distinct modes (dispatch on target_part):
  - manifold_bar   : an inline bar — a supply plenum with N barbed outlets in a
                     row along the top; the field workhorse.
  - manifold_cross : a compact star hub — a central supply chamber with N barbs
                     radiating in the plane; a point distributor for a cluster.
  - manifold_wye   : a simple Y-splitter — one inlet feeding two barbed legs; the
                     minimal tee for branching a single line.

Watertight strategy (per the Yantra4D authoring canon):
  - The body is SOLID, then the internal plenum is bored so it is open ONLY at
    the inlet and stops short of the far end (a closed distribution chamber, not
    a tube open at both ends — an open-both-ends bore around barb lumens
    tessellates non-watertight).
  - Barbs are VOLUMETRIC fused frusta (stacked lofted cones), unioned into the
    body with real overlap — never boolean-cut grooves.
  - Each outlet lumen is bored THROUGH its barb into the plenum LAST, so the
    interior is one connected air space venting through inlet + outlet lumens:
    a closed, watertight surface with no trapped void.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - No cross-file imports; assign the final solid to top-level `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "manifold_bar"))
# "manifold_bar" | "manifold_cross" | "manifold_wye"

outlets = float(PARAM(lambda: outlets, 6))          # number of 1/4in barbed outlets
barb_od = float(PARAM(lambda: barb_od, 6.0))        # barb ridge OD (grips 1/4in tube ID)
barb_lumen = float(PARAM(lambda: barb_lumen, 3.6))  # outlet through-lumen diameter
barb_len = float(PARAM(lambda: barb_len, 12.0))     # barb spigot length
inlet_od = float(PARAM(lambda: inlet_od, 16.0))     # supply body / inlet OD (1/2in poly)
wall = float(PARAM(lambda: wall, 3.0))              # body wall thickness
spacing = float(PARAM(lambda: spacing, 16.0))       # outlet pitch along the bar

# Clamp to sane ranges so extreme UI values never crash the kernel.
outlets = max(2.0, min(round(outlets), 8.0))
barb_od = max(4.5, min(barb_od, 9.0))
barb_lumen = max(2.0, min(barb_lumen, barb_od - 1.6))
barb_len = max(8.0, min(barb_len, 20.0))
inlet_od = max(10.0, min(inlet_od, 24.0))
wall = max(2.0, min(wall, 5.0))
spacing = max(barb_od + 6.0, min(spacing, 30.0))

_n = int(outlets)
_bore = inlet_od - 2.0 * wall                        # plenum bore diameter
_barb_top = barb_od * 0.68                            # frustum tip (ridged taper)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _barb_z(cx, cy, cz, length):
    """A ridged 1/4in barb spigot as fused frusta, growing +Z from (cx,cy,cz).
    Two stacked frusta plus a ridge give the barb bite. UNION into the body."""
    base = cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, cz))
    seg = length / 2.0
    spig = (base.circle(barb_od / 2.0)
            .workplane(offset=seg).circle(_barb_top / 2.0).loft())
    ridge = (base.workplane(offset=seg - 0.6).circle(barb_od / 2.0)
             .workplane(offset=seg + 0.6).circle(_barb_top / 2.0).loft())
    tip = (base.workplane(offset=seg).circle(barb_od / 2.0)
           .workplane(offset=length).circle(_barb_top / 2.0).loft())
    return spig.union(ridge).union(tip)


def _lumen_z(cx, cy, cz, length):
    """A through-lumen bored +Z from (cx,cy,cz)."""
    return (cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, cz))
            .circle(barb_lumen / 2.0).extrude(length))


# ── Part builders ────────────────────────────────────────────────────────────
def build_manifold_bar():
    """Inline bar: a horizontal supply body along X, inlet barb at the -X end,
    a closed plenum bored from the inlet, and N barbed outlets along the top."""
    length = spacing * _n + inlet_od + 8.0
    # Supply body along X (circle in YZ extruded +X).
    body = cq.Workplane("YZ").circle(inlet_od / 2.0).extrude(length)

    # Plenum: open at the -X inlet end, stops ~wall+2 short of the +X far end.
    plen = (cq.Workplane("YZ").circle(_bore / 2.0)
            .extrude(length - (wall + 2.0)).translate((0, 0, 0)))
    body = body.cut(plen)

    # Inlet barb at the -X face (feeds the plenum), pointing -X.
    inlet_barb = (cq.Workplane("YZ")
                  .circle(inlet_od / 2.0).workplane(offset=-barb_len)
                  .circle(inlet_od / 2.0 * 0.8).loft())
    body = body.union(inlet_barb)
    body = body.cut(cq.Workplane("YZ").circle(_bore / 2.0)
                    .extrude(-(barb_len + 1.0)))

    # N outlet barbs on +Z top, evenly spaced along X.
    x0 = inlet_od * 0.6
    for i in range(_n):
        x = x0 + (i + 0.5) * spacing
        body = body.union(_barb_z(x, 0.0, inlet_od / 2.0 - 1.0, barb_len))
        body = body.cut(_lumen_z(x, 0.0, -1.0, inlet_od / 2.0 + barb_len + 2.0))
    return body


def build_manifold_cross():
    """Star hub: a squat central chamber with a bottom inlet barb and N barbs
    radiating outward in the XY plane. Compact point distributor."""
    hub_r = max(inlet_od / 2.0 + barb_od * 0.4,
                (barb_od + spacing) * 0.28 * _n / math.pi + inlet_od / 2.0)
    hub_h = inlet_od
    hub = cq.Workplane("XY").circle(hub_r).extrude(hub_h)
    try:
        hub = hub.edges("%CIRCLE").fillet(min(2.0, wall - 0.5))
    except Exception:
        pass

    # Central plenum: bored from the BOTTOM (inlet), closed short of the top.
    plen = (cq.Workplane("XY").circle(_bore / 2.0)
            .extrude(hub_h - (wall + 1.5)))
    hub = hub.cut(plen)

    # Bottom inlet barb pointing -Z (a plain tapered spigot; lumen bored after).
    inlet_b = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, 0))
               .circle(inlet_od / 2.0 * 0.9)
               .workplane(offset=-barb_len).circle(inlet_od / 2.0 * 0.72).loft())
    hub = hub.union(inlet_b)
    hub = hub.cut(cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -barb_len - 1.0))
                  .circle(barb_lumen / 2.0).extrude(barb_len + 2.0))

    # N radial barbs around the equator (mid-height), lumens into the plenum.
    zc = hub_h / 2.0
    for i in range(_n):
        ang = 2.0 * math.pi * i / _n
        # barb built along +X then rotated about Z to the radial angle.
        barb = (cq.Workplane("YZ").transformed(offset=cq.Vector(0, zc, hub_r - 1.0))
                .circle(barb_od / 2.0)
                .workplane(offset=barb_len).circle(_barb_top / 2.0).loft())
        barb = barb.rotate((0, 0, 0), (0, 0, 1), math.degrees(ang))
        hub = hub.union(barb)
        lum = (cq.Workplane("YZ").transformed(offset=cq.Vector(0, zc, 0))
               .circle(barb_lumen / 2.0).extrude(hub_r + barb_len + 1.0))
        lum = lum.rotate((0, 0, 0), (0, 0, 1), math.degrees(ang))
        hub = hub.cut(lum)
    return hub


def build_manifold_wye():
    """Y-splitter: one inlet barb feeding a plenum that branches to two barbed
    legs at a shallow angle. The minimal branching fitting."""
    leg_ang = 32.0
    body_len = inlet_od * 1.8
    trunk_r = inlet_od / 2.0
    # Trunk along X (inlet at -X), circle in YZ.
    body = cq.Workplane("YZ").circle(trunk_r).extrude(body_len)
    plen = cq.Workplane("YZ").circle(_bore / 2.0).extrude(body_len - (wall + 1.5))
    body = body.cut(plen)

    # Inlet barb at -X.
    inlet_b = (cq.Workplane("YZ").circle(trunk_r)
               .workplane(offset=-barb_len).circle(trunk_r * 0.8).loft())
    body = body.union(inlet_b)
    body = body.cut(cq.Workplane("YZ").circle(_bore / 2.0).extrude(-(barb_len + 1.0)))

    # Two barbed legs splaying from the +X end in the XY plane (+/- leg_ang).
    tip_x = body_len
    for sgn in (+1.0, -1.0):
        ang = sgn * leg_ang
        # leg barb starts at the +X face centre, points out at angle in XY.
        barb = (cq.Workplane("YZ").transformed(offset=cq.Vector(0, 0, tip_x - 3.0))
                .circle(barb_od / 2.0)
                .workplane(offset=barb_len + 4.0).circle(_barb_top / 2.0).loft())
        barb = barb.rotate((tip_x, 0, 0), (tip_x, 0, 1), ang).translate((0, 0, 0))
        body = body.union(barb)
        lum = (cq.Workplane("YZ").transformed(offset=cq.Vector(0, 0, tip_x - 8.0))
               .circle(barb_lumen / 2.0).extrude(barb_len + 12.0))
        lum = lum.rotate((tip_x, 0, 0), (tip_x, 0, 1), ang)
        body = body.cut(lum)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "manifold_cross":
    result = build_manifold_cross()
elif target_part == "manifold_wye":
    result = build_manifold_wye()
else:
    result = build_manifold_bar()
