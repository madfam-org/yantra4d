"""
Fan Dust Shroud — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A snap-on dust filter frame for a PC / equipment fan. It clips a mesh or foam
filter over the fan intake on the standard fan screw square, keeping dust out of
enclosures and 3D-printer electronics bays. Pick the fan size and the frame lands
on the correct corner-hole spacing; variants add an integral printed grille (so
no separate mesh is needed) or a magnet-pocket frame for tool-free removal.

Modes are dispatched via `target_part`:
  * "filter_frame"  — a shallow frame that clamps a cut filter over the fan.
  * "grille_filter" — the frame with an integral printed grille (rings + spokes).
  * "magnetic_frame"— the frame with corner magnet pockets for snap-off mounting.

Fan sizes (body, corner-hole spacing, open bore, screw dia) for 40/60/80/120/140
mm fans — the published PC-fan screw square.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `fan_size`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Fan table (PC-fan screw square) ──────────────────────────────────────────
# body    : fan outer size (mm, square).
# spacing : corner-hole centre-to-centre (mm).
# bore    : open airflow bore diameter (mm).
# screw   : mounting-screw clearance diameter (mm).
_FANS = {
    "40":  {"body": 40.0,  "spacing": 32.0,  "bore": 37.0,  "screw": 3.2},
    "60":  {"body": 60.0,  "spacing": 50.0,  "bore": 57.0,  "screw": 4.3},
    "80":  {"body": 80.0,  "spacing": 71.5,  "bore": 77.0,  "screw": 4.3},
    "120": {"body": 120.0, "spacing": 105.0, "bore": 117.0, "screw": 4.5},
    "140": {"body": 140.0, "spacing": 124.5, "bore": 137.0, "screw": 4.5},
}


def fan_spec(key):
    k = str(key).strip().lower().replace("mm", "").replace(" ", "")
    return _FANS.get(k, _FANS["120"])


# ── Parameters ───────────────────────────────────────────────────────────────
fan_size   = str(  PARAM(lambda: fan_size,   "120"))    # 40|60|80|120|140
thickness  = float(PARAM(lambda: thickness,    3.0))    # frame plate thickness
rim        = float(PARAM(lambda: rim,          5.0))    # frame border past the bore
snap_depth = float(PARAM(lambda: snap_depth,   4.0))    # depth of the snap skirt into the fan
ring_count = int(  PARAM(lambda: ring_count,     4))    # concentric rings (grille)
spoke_count = int( PARAM(lambda: spoke_count,    6))    # radial spokes (grille)
bar_w      = float(PARAM(lambda: bar_w,        2.4))    # grille bar width
magnet_d   = float(PARAM(lambda: magnet_d,     6.0))    # corner magnet pocket diameter

target_part = str(PARAM(lambda: target_part, "filter_frame"))

# ── Derived ──────────────────────────────────────────────────────────────────
spec = fan_spec(fan_size)
body_sz = spec["body"]
spacing = spec["spacing"]
bore_d = spec["bore"]
screw_d = spec["screw"]

thickness = max(2.0, min(thickness, 8.0))
rim = max(3.0, min(rim, 15.0))
snap_depth = max(0.0, min(snap_depth, 12.0))
ring_count = max(1, min(ring_count, 10))
spoke_count = max(2, min(spoke_count, 16))
bar_w = max(1.5, min(bar_w, 5.0))
magnet_d = max(3.0, min(magnet_d, 12.0))

frame_sz = body_sz                       # frame matches the fan footprint
outer_r = bore_d / 2.0 + rim             # material out to here around the bore


def _corner_points():
    h = spacing / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


# ── Helpers ──────────────────────────────────────────────────────────────────
def _frame_plate():
    """A square plate the fan size, with the airflow bore cut and the four screw
    holes drilled — the base every mode builds on."""
    body = cq.Workplane("XY").box(frame_sz, frame_sz, thickness, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(4.0, frame_sz / 10.0))
    except Exception:
        pass
    return body


def _cut_bore(body):
    hole = (
        cq.Workplane("XY").workplane(offset=-0.5)
        .circle(bore_d / 2.0).extrude(thickness + 1.0)
    )
    return body.cut(hole)


def _cut_screws(body):
    screws = (
        cq.Workplane("XY").workplane(offset=-0.5)
        .pushPoints(_corner_points()).circle(screw_d / 2.0).extrude(thickness + 1.0)
    )
    return body.cut(screws)


def _snap_skirt(body):
    """A thin skirt ring on the underside that tucks into the fan bore to locate
    the frame and snap it on. Outer dia just under the fan bore."""
    if snap_depth < 0.3:
        return body
    ro = bore_d / 2.0 - 0.3
    ri = ro - 1.6
    skirt = (
        cq.Workplane("XY").workplane(offset=-snap_depth)
        .circle(ro).circle(ri).extrude(snap_depth + 0.1)
    )
    # small outward barbs at 4 points to catch the fan lip
    barbs = (
        cq.Workplane("XY").workplane(offset=-snap_depth + 0.5)
        .pushPoints([(ro, 0), (-ro, 0), (0, ro), (0, -ro)])
        .circle(0.9).extrude(1.2)
    )
    return body.union(skirt).union(barbs)


def _grille():
    """Concentric rings + radial spokes filling the bore — an integral printed
    filter grille. Built as unions of thin annuli and bars, then intersected with
    the bore disk so nothing overhangs the frame."""
    parts = []
    # rings
    for i in range(1, ring_count + 1):
        rr = bore_d / 2.0 * i / (ring_count + 1)
        ring = (
            cq.Workplane("XY")
            .circle(rr + bar_w / 2.0).circle(max(0.1, rr - bar_w / 2.0))
            .extrude(thickness)
        )
        parts.append(ring)
    # hub
    parts.append(cq.Workplane("XY").circle(bar_w).extrude(thickness))
    # spokes
    for k in range(spoke_count):
        ang = 360.0 / spoke_count * k
        spoke = (
            cq.Workplane("XY")
            .transformed(rotate=cq.Vector(0, 0, ang))
            .box(bore_d, bar_w, thickness, centered=(True, True, False))
        )
        parts.append(spoke)
    grille = parts[0]
    for p in parts[1:]:
        grille = grille.union(p)
    # clip to the bore disk
    disk = cq.Workplane("XY").circle(bore_d / 2.0).extrude(thickness)
    grille = grille.intersect(disk)
    return grille


# ── Builders ─────────────────────────────────────────────────────────────────
def build_filter_frame():
    body = _frame_plate()
    body = _cut_bore(body)
    body = _cut_screws(body)
    body = _snap_skirt(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_grille_filter():
    body = _frame_plate()
    body = _cut_bore(body)
    body = body.union(_grille())
    body = _cut_screws(body)
    body = _snap_skirt(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_magnetic_frame():
    """Filter frame with a magnet pocket at each corner (blind bore from the
    underside) so it snaps on/off a steel fan grill or magnet ring tool-free."""
    body = _frame_plate()
    body = _cut_bore(body)
    # magnet pockets replace screw holes: blind bores from the bottom.
    pockets = (
        cq.Workplane("XY").workplane(offset=-0.01)
        .pushPoints(_corner_points()).circle(magnet_d / 2.0)
        .extrude(min(thickness - 0.8, magnet_d * 0.4 + 0.5))
    )
    body = body.cut(pockets)
    body = _snap_skirt(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "filter_frame": build_filter_frame,
    "grille_filter": build_grille_filter,
    "magnetic_frame": build_magnetic_frame,
}

result = _dispatch.get(target_part, build_filter_frame)()
