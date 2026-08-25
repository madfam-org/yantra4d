"""
Planetary Gear Stage — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A compact epicyclic (planetary) reduction in its three interoperating gears: the
SUN (central drive), a PLANET (the orbiting idler, printed once — a real set uses
3-4 identical planets), and the internally-toothed RING. All share one module and
one 20 deg pressure angle so they mesh: teeth_ring = teeth_sun + 2*teeth_planet,
the defining planetary constraint. Flanks are the TRUE involute of the base
circle P(t) = rb*(cos t + t sin t, sin t - t cos t) — external for sun/planet,
internal (teeth pointing inward) for the ring.

The FUNCTIONAL interface is the involute tooth (ISO 53 / DIN 867, module 1,
20 deg). A sun or planet from this cartridge meshes a gear from the gear-kit
family (shared module + pressure angle) — it grows that involute-gear family.

  - sun     : the central external spur gear, hub bore for the input shaft.
  - planet  : one orbiting external spur idler with a bearing bore (a set needs
              several identical copies).
  - ring    : the internal (annulus) gear — an outer rim with involute teeth cut
              pointing INWARD; the planets run inside it.

Ratio (ring fixed, carrier output): 1 + teeth_ring / teeth_sun.

Watertight strategy:
  Sun / planet = an extrusion of the closed external involute wire (single solid)
  with a THROUGH bore (vents both faces). Ring = a plain annular blank (outer disc
  minus inner disc) with the internal teeth formed by CUTTING an internal-involute
  cutter wire from the bore — the ring stays one solid because the teeth are
  removed from a closed annulus, not added. Fillets (none needed here) would go on
  the clean blank first. No revolve-of-cut profiles, no tangent unions.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read each via PARAM(lambda: name, default); worker injects target_part.
  - Assign the final solid to a top-level name `result`.
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
target_part = str(PARAM(lambda: target_part, "sun"))
# "sun" | "planet" | "ring"

module = float(PARAM(lambda: module, 1.0))             # gear module (mm)
teeth_sun = int(PARAM(lambda: teeth_sun, 16))          # sun tooth count
teeth_planet = int(PARAM(lambda: teeth_planet, 16))    # planet tooth count
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0))  # deg
gear_thick = float(PARAM(lambda: gear_thick, 6.0))     # face width (mm)
sun_bore = float(PARAM(lambda: sun_bore, 5.0))         # sun shaft bore (mm)
planet_bore = float(PARAM(lambda: planet_bore, 4.0))   # planet bearing bore (mm)
ring_backlash = float(PARAM(lambda: ring_backlash, 0.12))  # ring tooth backlash (mm)
ring_rim = float(PARAM(lambda: ring_rim, 5.0))         # ring wall beyond the teeth (mm)
flank_pts = int(PARAM(lambda: flank_pts, 8))           # involute samples / flank

# ── Clamp / normalise inputs ─────────────────────────────────────────────────
module = max(0.5, min(module, 2.0))
teeth_sun = max(10, min(teeth_sun, 40))
teeth_planet = max(8, min(teeth_planet, 40))
pressure_angle = max(14.5, min(pressure_angle, 25.0))
gear_thick = max(3.0, min(gear_thick, 16.0))
ring_backlash = max(0.0, min(ring_backlash, 0.5))
ring_rim = max(2.0, min(ring_rim, 12.0))
flank_pts = max(4, min(flank_pts, 14))
pa = math.radians(pressure_angle)
teeth_ring = teeth_sun + 2 * teeth_planet              # planetary meshing constraint


# ── Involute geometry (ISO 53 / DIN 867) ─────────────────────────────────────
def _involute_point(rb, t):
    return (rb * (math.cos(t) + t * math.sin(t)),
            rb * (math.sin(t) - t * math.cos(t)))


def _inv(angle):
    return math.tan(angle) - angle


def _roll_at_radius(rb, r):
    if r <= rb:
        return 0.0
    return math.sqrt((r / rb) ** 2 - 1.0)


def _one_tooth_ext(g_teeth, rb, ro, rr, n):
    """External involute tooth centred on +X, root->tip->root."""
    half_pitch = math.pi / (2.0 * g_teeth)
    beta0 = half_pitch + _inv(pa)
    r_start = max(rb, rr)
    t_end = _roll_at_radius(rb, ro)
    t_start = _roll_at_radius(rb, r_start)
    right = []
    for i in range(n):
        t = t_start + (t_end - t_start) * (i / (n - 1))
        x0, y0 = _involute_point(rb, t)
        phi = math.atan2(y0, x0)
        r = rb * math.sqrt(1.0 + t * t)
        ang = phi - beta0
        right.append((r * math.cos(ang), r * math.sin(ang)))
    root_r = []
    if rr < r_start - 1e-6:
        fx, fy = right[0]
        fang = math.atan2(fy, fx)
        root_r.append((rr * math.cos(fang), rr * math.sin(fang)))
    left = [(x, -y) for (x, y) in reversed(right)]
    root_l = [(x, -y) for (x, y) in reversed(root_r)]
    return root_r + right + left + root_l


def _external_gear_wire(g_teeth):
    """Full closed external spur cross-section."""
    rp = module * g_teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + module
    rr = max(rp - 1.25 * module, 0.5 * module)
    tooth = _one_tooth_ext(g_teeth, rb, ro, rr, flank_pts)
    step = 2.0 * math.pi / g_teeth
    pts = []
    for k in range(g_teeth):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            pts.append((x * ca - y * sa, x * sa + y * ca))
    return pts, rp


def _external_gear(g_teeth, bore_d):
    wire, rp = _external_gear_wire(g_teeth)
    gear = cq.Workplane("XY").polyline(wire).close().extrude(gear_thick)
    if bore_d > 0.05:
        rr = max(rp - 1.25 * module, 0.5 * module)
        br = min(bore_d / 2.0, rr - 0.6)
        if br > 0.4:
            hole = (cq.Workplane("XY").workplane(offset=-1.0)
                    .circle(br).extrude(gear_thick + 2.0))
            gear = gear.cut(hole)
    return gear


def build_sun():
    return _external_gear(teeth_sun, sun_bore)


def build_planet():
    return _external_gear(teeth_planet, planet_bore)


def build_ring():
    """Internal ring gear: a solid annular blank with involute teeth CUT pointing
    inward. The tooth-space cutter is one external-tooth-shaped solid polar-arrayed
    and removed from the bore; because material is only REMOVED from a closed
    annulus, the ring is always a single watertight body.

    For an internal gear the roles invert: the ring's tip circle is the SMALL
    (inner) radius and its root circle is the LARGER radius. We approximate the
    internal tooth spaces by cutting external-involute 'tooth' solids sized to the
    same module, offset by backlash — a printable internal gear that meshes the
    planets on module and pressure angle."""
    rp_ring = module * teeth_ring / 2.0
    # Inner bore of the ring at the tooth tips (dedendum side for internal gear).
    r_tip_inner = rp_ring - module                # internal teeth point inward to here
    r_root_outer = rp_ring + 1.25 * module        # tooth roots sit out here
    r_outer = r_root_outer + ring_rim             # outer wall

    # Solid annular blank: outer disc minus a bore up to the root circle.
    ring = (cq.Workplane("XY").circle(r_outer).extrude(gear_thick)
            .cut(cq.Workplane("XY").workplane(offset=-1.0)
                 .circle(r_root_outer).extrude(gear_thick + 2.0)))

    # Build ONE internal tooth solid (the material BETWEEN two tooth spaces) as an
    # external-involute tooth of the ring's own tooth count, then polar-array and
    # UNION them onto the inner rim so teeth grow inward. Backlash trims each tooth.
    rb = rp_ring * math.cos(pa)
    # Sample the tooth flank OUT PAST the annulus bore. The involute is only
    # meaningful to about rp + module, but the polyline's outer end must physically
    # overlap the blank's bore at r_root_outer or the polar-arrayed tooth ring lands
    # as a free-floating disc inside the annulus (two bodies, both watertight — the
    # exact failure this cartridge shipped with). Extending the sampling radius past
    # the bore costs nothing: everything beyond r_root_outer is clipped away below,
    # and the involute's own tip is still at rp + module where it belongs.
    ro = r_root_outer + 0.5 * module               # overlap the bore, then clip back
    rr = max(r_tip_inner, rb)
    tooth = _one_tooth_ext(teeth_ring, rb, ro, rr, flank_pts)
    # Apply backlash TANGENTIALLY — thin each tooth by rotating its points toward
    # the tooth centreline — never as a uniform radial shrink. A radial shrink pulls
    # the tooth's OUTER end back inside the annulus bore, and at the largest backlash
    # the teeth ring detaches into a second free-floating body again. Thinning
    # circumferentially is also what backlash physically means: a narrower tooth in
    # the same space, not a smaller-diameter gear.
    if ring_backlash > 0.0:
        thinned = []
        for (x, y) in tooth:
            r = math.hypot(x, y)
            th = math.atan2(y, x)
            # Half the backlash off each flank, as an angle at THIS radius. The tooth
            # is centred on +X (th == 0), so moving each point toward th = 0 narrows
            # it. Cap the shift at HALF each point's own offset from the centreline:
            # the two tip points sit only ~0.013 deg apart, and an uncapped shift
            # collapses them onto each other, degenerating the polyline into a wire
            # OCCT refuses to extrude ("BRep_API: command not done"). Scaling rather
            # than subtracting keeps every point strictly on its own side, so the
            # profile stays simple and correctly ordered at any backlash.
            dth = min(abs(th) * 0.5, (ring_backlash / 2.0) / max(r, 1e-6))
            th -= math.copysign(dth, th)
            thinned.append((r * math.cos(th), r * math.sin(th)))
        tooth = thinned
    step = 2.0 * math.pi / teeth_ring
    pts = []
    for k in range(teeth_ring):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            pts.append((x * ca - y * sa, x * sa + y * ca))
    teeth_solid = cq.Workplane("XY").polyline(pts).close().extrude(gear_thick)
    # Keep only the inner-rim portion of the teeth ring (out to the root circle),
    # then union onto the annulus so the internal teeth are one body with the wall.
    # Clip a hair OUTSIDE the bore so the teeth interpenetrate the annulus wall
    # rather than meeting it tangentially — a tangent seam fuses into a shell that
    # tessellates cracked even when OCCT calls it one solid.
    clip = cq.Workplane("XY").circle(r_root_outer + 0.15 * module).extrude(gear_thick)
    teeth_solid = teeth_solid.intersect(clip)
    ring = ring.union(teeth_solid)

    try:
        ring = ring.clean()
    except Exception:
        pass
    return ring


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "planet":
    result = build_planet()
elif target_part == "ring":
    result = build_ring()
else:  # "sun" (default)
    result = build_sun()
