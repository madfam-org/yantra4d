import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "adapter_15")
rotor_bore = float(PARAM(lambda: rotor_bore, 30.0))
tube_dia = float(PARAM(lambda: tube_dia, 17.0))
clearance = float(PARAM(lambda: clearance, 0.4))
depth = float(PARAM(lambda: depth, 90.0))
floor = float(PARAM(lambda: floor, 4.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Conical ("Falcon") centrifuge tubes: 15 mL ~ Ø17 mm x ~120 mm, 50 mL ~ Ø30 mm
#   x ~115 mm, with a ~17° conical tip. Adapts to a larger rotor bore / bucket so
#   small tubes spin in a big rotor. Shares the 15/50 mL conical standard with the
#   centrifuge-adapter cartridge.
CONE_ANGLE_FRAC = 0.30   # tip cone height as a fraction of tube diameter


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


def _sleeve(outer_d, bore_d, total_h, floor_th):
    """A round sleeve: solid outer cylinder, cylindrical bore open to the top, a
    conical seat at the bottom that matches the tube's tapered tip, and a solid
    floor beneath. Pocket opens to the top only → no trapped void."""
    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(total_h)
    body = _fillet_safe(body, "|Z", 1.5)

    # Straight bore from the top down to the cone seat.
    cone_h = bore_d * CONE_ANGLE_FRAC
    bore_h = total_h - floor_th - cone_h
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_th + cone_h))
        .cylinder(bore_h + 2.0, bore_d / 2.0, centered=(True, True, False))
    )
    body = body.cut(bore)

    # Conical seat (frustum from full bore radius down to a small tip) so the
    # tube's tapered bottom is supported instead of hanging on its rim.
    cone = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_th))
        .circle(0.8)
        .workplane(offset=cone_h)
        .circle(bore_d / 2.0)
        .loft(combine=True)
    )
    body = body.cut(cone)
    return body


# ─── Mode 1: 15 mL conical adapter ────────────────────────────────────────────
def build_adapter_15():
    """Sleeve that seats a 15 mL conical tube (Ø17 mm) in a larger rotor bore."""
    outer = max(rotor_bore, tube_dia + 6.0)
    bore = tube_dia + 2.0 * clearance
    total_h = max(depth, bore + floor + 10.0)
    return _sleeve(outer, bore, total_h, floor)


# ─── Mode 2: 50 mL conical adapter ────────────────────────────────────────────
def build_adapter_50():
    """Sleeve that seats a 50 mL conical tube (Ø30 mm) in a larger rotor bore. The
    default tube diameter should be raised to ~30 mm for this mode. A ribbed
    collar at the mouth (a wider top band cut with grip notches) distinguishes it
    from the 15 mL sleeve and gives a grip to pull the heavier tube out; the notches
    open through the collar wall → still watertight."""
    import math
    tube = max(tube_dia, 28.0)          # 50 mL tubes are ~30 mm
    outer = max(rotor_bore + 8.0, tube + 8.0)
    bore = tube + 2.0 * clearance
    total_h = max(depth, bore + floor + 10.0)
    cone_h = bore * CONE_ANGLE_FRAC
    collar_h = 8.0
    collar_r = outer / 2.0 + 3.0

    # Build the OUTER as two stacked cylinders fused with a deep overlap (the wide
    # grip collar on top of the sleeve barrel) BEFORE any bore is cut, so it is one
    # solid. Then bore and cone are cut through the fused body → guaranteed 1 body.
    barrel = cq.Workplane("XY").circle(outer / 2.0).extrude(total_h)
    collar = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, total_h - collar_h * 2.0))
        .circle(collar_r)
        .extrude(collar_h * 2.0)
    )
    body = barrel.union(collar)
    body = _fillet_safe(body, "|Z", 1.2)

    # Straight bore down to the cone seat, then the conical tip seat.
    bore_h = total_h - floor - cone_h
    bore_cut = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor + cone_h))
        .cylinder(bore_h + collar_h + 2.0, bore / 2.0, centered=(True, True, False))
    )
    body = body.cut(bore_cut)
    cone = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .circle(0.8)
        .workplane(offset=cone_h)
        .circle(bore / 2.0)
        .loft(combine=True)
    )
    body = body.cut(cone)

    # Grip notches around the collar (open through the collar wall).
    for i in range(8):
        a = math.radians(45.0 * i)
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(math.cos(a) * collar_r, math.sin(a) * collar_r,
                                          total_h - collar_h))
            .box(4.0, 2.4, collar_h + 2.0, centered=(True, True, True))
        )
        body = body.cut(notch)
    return body


# ─── Mode 3: conical-tip cushion insert ───────────────────────────────────────
def build_cushion():
    """A short cushion/insert that drops into the BOTTOM of a rotor bucket and
    presents a conical seat so a conical tube's tip is supported and centred,
    protecting the tube from cracking under g-force. Solid disc with a conical
    seat pocket open to the top → watertight."""
    outer = max(rotor_bore, tube_dia + 6.0)
    bore = tube_dia + 2.0 * clearance
    cone_h = bore * CONE_ANGLE_FRAC * 1.6
    total_h = floor + cone_h + 6.0

    body = cq.Workplane("XY").circle(outer / 2.0).extrude(total_h)
    body = _fillet_safe(body, "|Z", 1.5)

    # A short straight lead-in above the cone so the tube self-centres.
    lead_h = 5.0
    lead = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, total_h - lead_h))
        .cylinder(lead_h + 2.0, bore / 2.0, centered=(True, True, False))
    )
    body = body.cut(lead)

    cone = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor))
        .circle(0.8)
        .workplane(offset=total_h - lead_h - floor)
        .circle(bore / 2.0)
        .loft(combine=True)
    )
    body = body.cut(cone)
    return body


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "adapter_15":
    result = build_adapter_15()
elif target_part == "adapter_50":
    result = build_adapter_50()
elif target_part == "cushion":
    result = build_cushion()
else:
    result = build_adapter_15()
