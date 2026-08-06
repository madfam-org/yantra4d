"""
Wheelchair / Walker Accessory — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Accessories that clamp to the round tube of a wheelchair, walker, rollator, or
mobility frame and carry the small things a user needs within reach: a cup, a
phone, or a cane/crutch. The shared interface is a C-shaped snap clamp sized to
standard mobility tube (3/4-1 in / 19-25 mm outer diameter); it opens on one side
to snap over the tube and can be pinched shut with a strap or zip tie through its
ears.

  * "cup_holder"   — a C-clamp with a cup ring + floor to hold a drink
                     (target_part == "cup_holder").
  * "phone_cradle" — a C-clamp with a slotted phone tray
                     (target_part == "phone_cradle").
  * "cane_holder"  — a C-clamp with a two-ring cradle that holds a cane/crutch
                     upright (target_part == "cane_holder").

Watertight strategy (per the tube-clamp guidance): the clamp is an extruded
C-cross-section — a 2D annular sector (outer arc, inner arc, and the two radial
faces of the opening gap) extruded once, so it is a single manifold body with the
opening venting to outside. The tube bore is the open centre of the C (through
along the tube axis → vented both ends). Accessories (cup ring, tray, hook) are
unioned with a solid overlap into the clamp back. Fillets are applied to clean
blanks; every union overlaps (never tangent).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "cup_holder"))
# cup_holder | phone_cradle | cane_holder

tube_dia = float(PARAM(lambda: tube_dia, 25.0))    # mobility tube OD (3/4-1in = 19-25mm)
clamp_wall = float(PARAM(lambda: clamp_wall, 5.0))  # clamp wall thickness
clamp_w = float(PARAM(lambda: clamp_w, 22.0))      # clamp width along the tube (mm)
opening = float(PARAM(lambda: opening, 120.0))     # arc of the C opening (deg)
clearance = float(PARAM(lambda: clearance, 0.4))   # radial fit gap over the tube

cup_dia = float(PARAM(lambda: cup_dia, 74.0))      # cup/can holder inner diameter
cup_h = float(PARAM(lambda: cup_h, 55.0))          # cup ring height
tray_w = float(PARAM(lambda: tray_w, 78.0))        # phone tray width
tray_d = float(PARAM(lambda: tray_d, 14.0))        # phone tray depth (front lip)
cane_dia = float(PARAM(lambda: cane_dia, 26.0))    # cane/crutch shaft diameter

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_dia = max(12.0, min(tube_dia, 40.0))
clamp_wall = max(3.0, min(clamp_wall, 10.0))
clamp_w = max(10.0, min(clamp_w, 50.0))
opening = max(60.0, min(opening, 170.0))
clearance = max(0.0, min(clearance, 2.0))
cup_dia = max(40.0, min(cup_dia, 110.0))
cup_h = max(25.0, min(cup_h, 100.0))
tray_w = max(50.0, min(tray_w, 120.0))
tray_d = max(8.0, min(tray_d, 30.0))
cane_dia = max(12.0, min(cane_dia, 45.0))

bore_r = tube_dia / 2.0 + clearance
clamp_or = bore_r + clamp_wall


# ── Shared: the C-clamp (single extruded annular sector) ──────────────────────
def _c_clamp():
    """A C-shaped snap clamp built as ONE extruded annular sector. The 2D profile
    is the region between the outer circle and the bore circle, minus a pie wedge
    of angle `opening` (the mouth). Extruding this closed region once yields a
    single manifold C. Two small ears flank the mouth for a strap/zip tie.

    The profile is drawn as an explicit polygon: outer arc from +half to
    -half around the back, then inner arc back, closing across the two mouth
    faces. Using arc points keeps it a single closed wire."""
    half = math.radians((360.0 - opening) / 2.0)   # half-arc of solid material
    steps = 48
    outer = []
    inner = []
    # Sweep the SOLID span, centred on the -Y (back) direction so the mouth faces +Y.
    a0 = -math.pi / 2.0 - half     # start angle
    a1 = -math.pi / 2.0 + half     # end angle
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        outer.append((clamp_or * math.cos(a), clamp_or * math.sin(a)))
        inner.append((bore_r * math.cos(a), bore_r * math.sin(a)))
    pts = outer + list(reversed(inner))
    prof = cq.Workplane("XY").polyline(pts).close()
    clamp = prof.extrude(clamp_w)

    # Pinch ears: a small solid pad at each mouth end so a strap can cinch the C
    # shut. Each ear overlaps the clamp end so the union is one body.
    ear_r = clamp_wall * 0.9
    ears = clamp
    for a in (a0, a1):
        ex = (clamp_or - clamp_wall * 0.4) * math.cos(a)
        ey = (clamp_or - clamp_wall * 0.4) * math.sin(a)
        ear = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(ex, ey, 0))
            .circle(ear_r)
            .extrude(clamp_w)
        )
        # Strap hole through the ear (through Z → vented).
        ear = ear.faces(">Z").workplane().circle(min(1.6, ear_r * 0.45)).cutThruAll()
        ears = ears.union(ear)
    clamp = ears
    try:
        clamp = clamp.edges("|Z").fillet(0.8)
    except Exception:
        pass
    return clamp


def build_cup_holder():
    """C-clamp on the tube (mouth +Y) with a cup ring cantilevered on the back
    (-Y). The ring is a tube (outer wall) with a solid floor; a drain hole vents
    the floor so no sealed cavity forms."""
    clamp = _c_clamp()
    # Cup ring sits behind the clamp (toward -Y), its wall overlapping the clamp back.
    cup_or = cup_dia / 2.0 + 4.0
    cy = -(clamp_or + cup_or - 8.0)     # overlap the clamp back by ~8mm
    ring_outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy, 0))
        .circle(cup_or)
        .extrude(cup_h)
    )
    ring_bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy, 4.0))     # leave a 4mm floor
        .circle(cup_dia / 2.0)
        .extrude(cup_h)
    )
    ring = ring_outer.cut(ring_bore)
    # Drain hole through the floor so the cup pocket is not a sealed void.
    drain = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy, -1.0))
        .circle(4.0)
        .extrude(8.0)
    )
    ring = ring.cut(drain)
    # A connector web bridging clamp back to ring so the union is solid.
    web = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, (cy) / 2.0, 0))
        .box(clamp_w, abs(cy) + cup_or, min(clamp_w, 16.0), centered=(True, True, False))
    )
    body = clamp.union(web).union(ring)
    return body


def build_phone_cradle():
    """C-clamp with a phone tray on the back: a shallow floor with a raised front
    lip and open back so a phone drops in and its cable exits. One manifold."""
    clamp = _c_clamp()
    floor_t = 4.0
    ty = -(clamp_or + tray_w * 0.0 + 22.0)   # tray centre behind the clamp
    tray_len = 90.0
    # Tray floor.
    floor = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, ty, 0))
        .box(tray_w, tray_len, floor_t, centered=(True, True, False))
    )
    # Front lip (far -Y edge) and side lips, unioned (overlap the floor).
    lip_front = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, ty - tray_len / 2.0 + 3.0, 0))
        .box(tray_w, 6.0, floor_t + tray_d, centered=(True, True, False))
    )
    lip_l = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(tray_w / 2.0 - 3.0, ty, 0))
        .box(6.0, tray_len, floor_t + tray_d * 0.7, centered=(True, True, False))
    )
    lip_r = lip_l.mirror("YZ")
    tray = floor.union(lip_front).union(lip_l).union(lip_r)
    # Connector web from clamp back into the tray near edge.
    web = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, ty / 2.0, 0))
        .box(clamp_w, abs(ty) + tray_len / 2.0, min(clamp_w, floor_t + 8.0),
             centered=(True, True, False))
    )
    body = clamp.union(web).union(tray)
    return body


def build_cane_holder():
    """C-clamp with a cane/crutch cradle on the back: a C-ring (open toward the
    user) that the cane shaft rests in, on a stem off the clamp. Both C's are
    extruded annular sectors → single manifolds; the stem overlaps both."""
    clamp = _c_clamp()
    cradle_or = cane_dia / 2.0 + clamp_wall + clearance
    cradle_br = cane_dia / 2.0 + clearance
    cy = -(clamp_or + cradle_or + 24.0)
    # Cane cradle C (mouth toward -Y, away from tube so the cane clips in).
    half = math.radians((360.0 - 150.0) / 2.0)
    steps = 40
    a0 = math.pi / 2.0 - half
    a1 = math.pi / 2.0 + half
    outer, inner = [], []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        outer.append((cradle_or * math.cos(a), cradle_or * math.sin(a) + cy))
        inner.append((cradle_br * math.cos(a), cradle_br * math.sin(a) + cy))
    prof = cq.Workplane("XY").polyline(outer + list(reversed(inner))).close()
    cradle = prof.extrude(clamp_w)
    # Stem bridging clamp back (-Y) to the cradle, overlapping both.
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy / 2.0, 0))
        .box(min(clamp_w, 18.0), abs(cy) + cradle_or, min(clamp_w, 16.0),
             centered=(True, True, False))
    )
    body = clamp.union(stem).union(cradle)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "phone_cradle":
    result = build_phone_cradle()
elif target_part == "cane_holder":
    result = build_cane_holder()
else:  # "cup_holder"
    result = build_cup_holder()
