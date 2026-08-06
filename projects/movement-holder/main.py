import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


# Parameters are injected by the render worker as bare names; read defensively.
target_part      = PARAM(lambda: target_part, "movement_cup")
movement_dia     = float(PARAM(lambda: movement_dia, 25.6))   # ETA 2824-2 = 25.6 mm
movement_height  = float(PARAM(lambda: movement_height, 4.6))  # ETA 2824-2 = 4.6 mm
wall             = float(PARAM(lambda: wall, 6.0))
base_height      = float(PARAM(lambda: base_height, 10.0))
stem_relief_dia  = float(PARAM(lambda: stem_relief_dia, 6.0))
station_count    = int(str(PARAM(lambda: station_count, 3)))


# ─── Shared constants ─────────────────────────────────────────────────────────
LIGNE_MM = 2.2558   # 1 ligne = 2.2558 mm (Swiss watchmaking unit)


def _outer_dia(mv):
    """Holder outer diameter = movement + 2*wall, clamped to a sane minimum."""
    return max(mv + 2.0 * wall, mv + 8.0)


# ─── Mode 1: Movement Cup ─────────────────────────────────────────────────────
def build_movement_cup():
    """Single-caliber holder cup: solid puck with a movement pocket bored from the
    top face and a stem-access relief bored from the bottom face. Both bores open
    to a face, so no trapped void. Fillet the blank before cutting."""
    od = _outer_dia(movement_dia)
    total_h = base_height + movement_height + 1.0

    body = cq.Workplane("XY").cylinder(total_h, od / 2.0)
    # Fillet outer top+bottom edges of the plain blank BEFORE any feature cut.
    body = body.edges("|Z or %CIRCLE").fillet(1.2)

    # Movement seat pocket — open to the top face (depth = movement height + clearance).
    seat_depth = movement_height + 1.0
    body = (
        body.faces(">Z").workplane()
        .hole(movement_dia + 0.3, seat_depth)
    )

    # Stem / winding-crown access relief — open to the bottom face.
    relief_depth = total_h - seat_depth - 2.0
    body = (
        body.faces("<Z").workplane()
        .hole(stem_relief_dia, relief_depth)
    )
    return body


# ─── Mode 2: Multi-Station Rest ───────────────────────────────────────────────
def build_multi_station():
    """Multi-caliber servicing tray: a rectangular bar carrying N movement pockets
    in a row, each pocket open to the top face. Distinct silhouette from the cup."""
    n = max(2, station_count)
    pocket_dia = movement_dia + 0.3
    pitch = _outer_dia(movement_dia) + 4.0
    length = pitch * n + 6.0
    depth = _outer_dia(movement_dia) + 10.0
    height = base_height + movement_height + 1.0

    body = cq.Workplane("XY").box(length, depth, height)
    body = body.edges("|Z").fillet(3.0)
    body = body.edges(">Z").fillet(1.0)

    # Row of movement pockets, open to the top face.
    seat_depth = movement_height + 1.0
    x0 = -pitch * (n - 1) / 2.0
    pts = [(x0 + i * pitch, 0.0) for i in range(n)]
    body = (
        body.faces(">Z").workplane()
        .pushPoints(pts)
        .hole(pocket_dia, seat_depth)
    )
    # Finger-scoop notch running the length of the front edge so movements can be
    # lifted out — one obround cut open to the top+front, no trapped void.
    scoop = (
        cq.Workplane("XY")
        .workplane(offset=height / 2.0 - seat_depth / 2.0)
        .center(0.0, -depth / 2.0)
        .slot2D(length - 8.0, 9.0, 0)
        .extrude(seat_depth / 2.0 + 2.0)
    )
    body = body.cut(scoop)
    return body


# ─── Mode 3: Case Ring ────────────────────────────────────────────────────────
def build_case_ring():
    """Movement casing ring / holder ring: an annulus that seats over the movement
    band to protect it during hand-fitting. A through-bore open on both faces —
    a manifold tube, never a trapped cavity. Three tangential relief slots let a
    caseback tool grip. Ligne-honest inner diameter."""
    od = _outer_dia(movement_dia) + 6.0
    ring_h = movement_height + 3.0
    bore = movement_dia + 0.4

    body = cq.Workplane("XY").cylinder(ring_h, od / 2.0)
    body = body.edges("|Z or %CIRCLE").fillet(1.0)
    # Through bore — open to BOTH faces => manifold tube.
    body = body.faces(">Z").workplane().hole(bore)

    # Caseback-tool grip notches: short radial obround pockets that notch the OUTER
    # wall inward without reaching the bore, so the ring stays a single body. Each
    # cut is open to the outer wall (no trapped void).
    wall_thk = (od - bore) / 2.0
    notch_len = wall_thk * 0.6          # stays well inside the wall
    notch_mid_r = od / 2.0 - notch_len / 2.0 + 0.5
    for k in range(3):
        ang = 120.0 * k
        a = math.radians(ang)
        cx, cy = notch_mid_r * math.cos(a), notch_mid_r * math.sin(a)
        cutter = (
            cq.Workplane("XY")
            .center(cx, cy)
            .slot2D(notch_len, 3.0, ang)
            .extrude(ring_h + 4.0)
            .translate((0, 0, -(ring_h + 4.0) / 2.0))
        )
        body = body.cut(cutter)
    return body


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "movement_cup":  build_movement_cup,
    "multi_station": build_multi_station,
    "case_ring":     build_case_ring,
}

result = _dispatch.get(target_part, build_movement_cup)()
