"""
Filter Media / Bio-Ball Basket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Aquarium and sump filtration holds biological media (bio-balls, ceramic rings,
foam) in a perforated basket so water flows through while the media stays put.
This cartridge builds the basket, a snap grate lid, and a printable bio-media
element, complementing the aquarium-fitting cartridge.

  * "media_basket" — a rounded rectangular box with a perforated floor and
                     perforated walls, open top, on short feet
                     (target_part == "media_basket").
  * "basket_lid"   — a perforated grate lid that caps the basket and keeps
                     floating media submerged (target_part == "basket_lid").
  * "bio_media"    — a printable high-surface-area bio-media wheel: a short
                     cylinder pierced by a grid of flow holes (target_part ==
                     "bio_media").

Real dimensions (aquarium filtration nominal):
  - Media retention holes: ~4 mm is the safe default (retains small ceramic
    media and pellets); 5-8 mm suits large bio-balls (16 / 25 / 38 mm).
  - Bio-balls: small ~16 mm, medium ~25 mm, large ~38 mm; ceramic rings ~12.7 mm.
  - Basket sizes vary by sump/HOB chamber; parametric footprint covers them.

Watertight strategy (the brief's mesh-basket rule): the basket is a SOLID
rounded box shell (outer box minus an inner box → an open-top tub, a closed
2-manifold), then a grid of round holes is bored fully THROUGH each wall and the
floor (open to both faces → no trapped void). No hollow bosses; feet are solid
and overlap up into the floor. The lid is a solid plate with through-holes. The
bio-media wheel is a solid cylinder with through-holes. Each result is one
manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

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
target_part = str(PARAM(lambda: target_part, "media_basket"))  # media_basket | basket_lid | bio_media

length = float(PARAM(lambda: length, 90.0))       # basket X footprint (mm)
width = float(PARAM(lambda: width, 70.0))         # basket Y footprint (mm)
height = float(PARAM(lambda: height, 60.0))       # basket height (mm)
wall = float(PARAM(lambda: wall, 2.4))            # wall / floor thickness (mm)
hole_dia = float(PARAM(lambda: hole_dia, 5.0))    # flow hole diameter (mm)
hole_pitch = float(PARAM(lambda: hole_pitch, 10.0))  # hole grid pitch (mm)
media_dia = float(PARAM(lambda: media_dia, 32.0))  # bio-media wheel diameter (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
length = max(30.0, min(length, 200.0))
width = max(30.0, min(width, 200.0))
height = max(20.0, min(height, 150.0))
wall = max(1.6, min(wall, 6.0))
hole_dia = max(2.0, min(hole_dia, 12.0))
hole_pitch = max(hole_dia + 2.0, min(hole_pitch, 30.0))
media_dia = max(12.0, min(media_dia, 80.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _grid_points(span_a, span_b, pitch):
    """Centred grid of (a, b) points covering span_a x span_b at the given pitch,
    leaving a margin so holes don't break the wall edges."""
    na = max(1, int(span_a // pitch))
    nb = max(1, int(span_b // pitch))
    a0 = -(na - 1) * pitch / 2.0
    b0 = -(nb - 1) * pitch / 2.0
    return [(a0 + i * pitch, b0 + j * pitch) for i in range(na) for j in range(nb)]


def _perforate_face(body, plane, offset, span_a, span_b, depth, pitch, dia):
    """Bore a grid of holes through a wall. `plane` is the workplane the holes are
    drilled on (XY/XZ/YZ); the cutter is extruded `depth` deep so it pierces the
    wall on both faces (vented)."""
    pts = _grid_points(span_a, span_b, pitch)
    if not pts:
        return body
    cutter = (
        cq.Workplane(plane)
        .workplane(offset=offset)
        .pushPoints(pts)
        .circle(dia / 2.0)
        .extrude(depth)
    )
    return body.cut(cutter)


# ── Part builders ────────────────────────────────────────────────────────────
def build_media_basket():
    """A perforated open-top tub on feet: solid shell, then holes bored through
    the floor and all four walls."""
    foot_h = 8.0
    outer = (
        cq.Workplane("XY")
        .workplane(offset=foot_h)
        .box(length, width, height, centered=(True, True, False))
    )
    try:
        outer = outer.edges("|Z").fillet(min(6.0, length * 0.08, width * 0.08))
    except Exception:
        pass
    # Hollow it into an open-top tub: subtract an inner box that stops `wall`
    # below the rim and opens through the TOP (so the cut vents upward).
    inner = (
        cq.Workplane("XY")
        .workplane(offset=foot_h + wall)
        .box(length - 2.0 * wall, width - 2.0 * wall, height, centered=(True, True, False))
    )
    body = outer.cut(inner)

    # Feet: four solid legs overlapping up into the floor.
    fx = length / 2.0 - max(8.0, wall + 6.0)
    fy = width / 2.0 - max(8.0, wall + 6.0)
    feet = None
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = (
                cq.Workplane("XY")
                .center(sx * fx, sy * fy)
                .rect(10.0, 10.0)
                .extrude(foot_h + wall + 0.5)
            )
            feet = leg if feet is None else feet.union(leg)
    body = body.union(feet)

    # Floor holes (bored up from just below the floor).
    body = _perforate_face(
        body, "XY", foot_h - 0.5,
        length - 4.0 * wall, width - 4.0 * wall, wall + 1.0, hole_pitch, hole_dia
    )
    # Long-wall holes (drill along Y through the two X-facing walls). The cutter
    # runs the full length so it pierces both walls in one pass (both vented).
    z_span = height - 2.0 * wall - 2.0
    wall_pts = _grid_points(width - 3.0 * wall, z_span, hole_pitch)
    if wall_pts:
        cutter = (
            cq.Workplane("YZ")
            .workplane(offset=-(length / 2.0 + 1.0))
            .pushPoints([(a, b + foot_h + wall + z_span / 2.0 + 1.0) for (a, b) in wall_pts])
            .circle(hole_dia / 2.0)
            .extrude(length + 2.0)
        )
        body = body.cut(cutter)
    # Short-wall holes (drill along X through the two Y-facing walls).
    wall_pts2 = _grid_points(length - 3.0 * wall, z_span, hole_pitch)
    if wall_pts2:
        cutter2 = (
            cq.Workplane("XZ")
            .workplane(offset=-(width / 2.0 + 1.0))
            .pushPoints([(a, b + foot_h + wall + z_span / 2.0 + 1.0) for (a, b) in wall_pts2])
            .circle(hole_dia / 2.0)
            .extrude(width + 2.0)
        )
        body = body.cut(cutter2)
    return body


def build_basket_lid():
    """A perforated grate lid: a solid plate sized to drop onto the basket rim,
    with a downstand skirt that locates it, and a grid of flow holes bored
    through the plate (vented)."""
    lid_th = max(wall, 3.0)
    skirt_h = 6.0
    plate = (
        cq.Workplane("XY")
        .workplane(offset=skirt_h)
        .box(length, width, lid_th, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(6.0, length * 0.08, width * 0.08))
    except Exception:
        pass
    # Locating skirt: a solid rectangular ring hanging below the plate, sized to
    # drop just inside the basket rim. Built as outer box minus inner box.
    skirt_outer = (
        cq.Workplane("XY")
        .box(length - 2.0 * wall - 0.6, width - 2.0 * wall - 0.6, skirt_h + 0.5, centered=(True, True, False))
    )
    skirt_inner = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .box(length - 4.0 * wall - 0.6, width - 4.0 * wall - 0.6, skirt_h + 2.0, centered=(True, True, False))
    )
    skirt = skirt_outer.cut(skirt_inner)
    body = plate.union(skirt)
    # Flow holes through the plate.
    body = _perforate_face(
        body, "XY", skirt_h - 0.5,
        length - 4.0 * wall, width - 4.0 * wall, lid_th + 1.0, hole_pitch, hole_dia
    )
    return body


def build_bio_media():
    """A printable bio-media wheel: a short solid cylinder pierced axially and
    radially by a grid of flow holes for high surface area. All holes are through
    bores (vented). One manifold solid."""
    r = media_dia / 2.0
    h = max(media_dia * 0.55, 12.0)
    puck = cq.Workplane("XY").circle(r).extrude(h)
    try:
        puck = puck.edges(">Z or <Z").chamfer(min(1.5, r * 0.15))
    except Exception:
        pass
    # Central bore (axial, through).
    puck = puck.faces(">Z").workplane().hole(max(3.0, r * 0.4))
    # Ring of axial holes.
    n = 6
    import math as _m
    ring_r = r * 0.62
    axial_pts = [(ring_r * _m.cos(_m.radians(a)), ring_r * _m.sin(_m.radians(a)))
                 for a in range(0, 360, 360 // n)]
    axial = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .pushPoints(axial_pts)
        .circle(max(1.5, hole_dia / 2.0))
        .extrude(h + 1.0)
    )
    body = puck.cut(axial)
    # A couple of radial through-holes (drill straight across the diameter).
    for ang in (0, 90):
        radial = (
            cq.Workplane("XZ")
            .workplane(offset=-(r + 1.0))
            .center(0, h / 2.0)
            .circle(max(1.5, hole_dia / 2.0))
            .extrude(media_dia + 2.0)
        )
        radial = radial.rotate((0, 0, 0), (0, 0, 1), ang)
        body = body.cut(radial)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "basket_lid":
    result = build_basket_lid()
elif target_part == "bio_media":
    result = build_bio_media()
else:  # "media_basket"
    result = build_media_basket()
