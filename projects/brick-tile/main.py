"""
Building-Brick Compatible Tile — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Plates, tiles and adapters that clutch with the ubiquitous construction-brick
system: an 8 mm stud pitch with Ø4.8 mm studs and hollow underside tubes, so a
printed part snaps onto any brick from the same family. Three interoperating
pieces:

  - stud_plate : a studded plate — a hollow-underside shell with an m x n array
                 of studs on top and clutch tubes underneath (the load-bearing
                 building element).
  - smooth_tile: a finishing tile — the same footprint and underside clutch, but
                 a flat top (no studs) for smooth surfaces and lettering blanks.
  - base_adapter: a thicker slab, studded on top, with a flat clutch-free bottom
                 and countersunk mounting holes — bolts brick builds to a wall,
                 desk or another surface.

Construction-brick geometry (the interoperable figures, cited as the CDG
`standard` = "construction brick 8mm"):
  - stud pitch          = 8.0 mm    (stud-to-stud, both axes)
  - stud diameter       = 4.8 mm
  - stud height         = 1.8 mm
  - plate height        = 3.2 mm    (one plate; a brick is three plates = 9.6 mm)
  - wall thickness      = 1.5 mm
  - underside tube OD/ID= 6.5 / 4.9 mm  (interior clutch tubes on the 8 mm grid)

Watertight strategy:
  The plate/tile is a solid box hollowed from BELOW (open bottom shell → the
  cavity vents to outside, so no trapped void). Studs are SOLID cylinders unioned
  on top. Underside clutch tubes are hollow rings whose bore opens to the bottom
  face; they are unioned to the underside and overlap the top wall. The base
  adapter has a SOLID bottom (no hollow) and countersunk through-holes (vented
  both faces). Fillet-free by design (brick corners are square); every feature is
  a union of overlapping solids or a through-cut. No revolve-of-cut profiles.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>); render worker injects
    target_part = <mode.parts[0]>. Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (construction-brick 8 mm family) ──────────────────────────────
target_part = str(PARAM(lambda: target_part, "stud_plate"))
# "stud_plate" | "smooth_tile" | "base_adapter"

cols = int(PARAM(lambda: cols, 4))                    # studs along X
rows = int(PARAM(lambda: rows, 2))                    # studs along Y

pitch = float(PARAM(lambda: pitch, 8.0))              # stud pitch (mm)
stud_dia = float(PARAM(lambda: stud_dia, 4.8))        # stud diameter (mm)
stud_h = float(PARAM(lambda: stud_h, 1.8))            # stud height (mm)
plate_h = float(PARAM(lambda: plate_h, 3.2))          # body height (mm); 3.2 = 1 plate
wall = float(PARAM(lambda: wall, 1.5))                # wall thickness (mm)
tube_od = float(PARAM(lambda: tube_od, 6.5))          # underside clutch tube OD (mm)
tube_id = float(PARAM(lambda: tube_id, 4.9))          # underside clutch tube ID (mm)

adapter_h = float(PARAM(lambda: adapter_h, 6.0))      # base-adapter slab height (mm)
mount_dia = float(PARAM(lambda: mount_dia, 4.2))      # base-adapter mount hole (M4 clr)

# ── Clamp inputs ─────────────────────────────────────────────────────────────
cols = max(1, min(cols, 16))
rows = max(1, min(rows, 16))
pitch = max(6.0, min(pitch, 16.0))
stud_dia = max(2.0, min(stud_dia, pitch - 1.5))
stud_h = max(1.0, min(stud_h, 6.0))
plate_h = max(2.0, min(plate_h, 12.0))
wall = max(0.8, min(wall, min(3.0, pitch / 2.5)))
tube_od = max(stud_dia + 0.6, min(tube_od, pitch - 0.6))
tube_id = max(stud_dia + 0.05, min(tube_id, tube_od - 0.8))
adapter_h = max(4.0, min(adapter_h, 16.0))
mount_dia = max(2.0, min(mount_dia, pitch - 1.0))

# Overall footprint: bricks are (n*pitch) wide minus a small all-round gap so
# adjacent bricks sit flush. Classic gap ~0.1 mm; keep it small.
gap = 0.1
foot_x = cols * pitch - gap
foot_y = rows * pitch - gap


def _stud_centers():
    x0 = -(cols - 1) * pitch / 2.0
    y0 = -(rows - 1) * pitch / 2.0
    return [(x0 + c * pitch, y0 + r * pitch) for c in range(cols) for r in range(rows)]


def _tube_centers():
    """Interior grid crossings (between studs): (cols-1) x (rows-1)."""
    if cols < 2 or rows < 2:
        return []
    x0 = -(cols - 2) * pitch / 2.0
    y0 = -(rows - 2) * pitch / 2.0
    return [(x0 + c * pitch, y0 + r * pitch) for c in range(cols - 1) for r in range(rows - 1)]


def _add_studs(body, top_z, skip=None):
    centers = _stud_centers()
    if skip:
        skip_set = {(round(x, 3), round(y, 3)) for (x, y) in skip}
        centers = [(x, y) for (x, y) in centers if (round(x, 3), round(y, 3)) not in skip_set]
    if not centers:
        return body
    studs = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, top_z - 0.01))
        .pushPoints(centers)
        .circle(stud_dia / 2.0)
        .extrude(stud_h + 0.01)
    )
    return body.union(studs)


def _hollow_from_below(body):
    """Carve the underside pocket, leaving `wall` all round and under the top."""
    cav_x = foot_x - 2.0 * wall
    cav_y = foot_y - 2.0 * wall
    cav_h = plate_h - wall
    if cav_x <= 0.5 or cav_y <= 0.5 or cav_h <= 0.3:
        return body  # too small to hollow — leave solid
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .box(cav_x, cav_y, cav_h + 0.01, centered=(True, True, False))
    )
    body = body.cut(cavity)

    # Clutch tubes: hollow rings on the interior grid, bore open to the bottom.
    centers = _tube_centers()
    if centers:
        outer = (
            cq.Workplane("XY")
            .pushPoints(centers)
            .circle(tube_od / 2.0)
            .extrude(cav_h)
        )
        body = body.union(outer)
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.01))
            .pushPoints(centers)
            .circle(tube_id / 2.0)
            .extrude(cav_h + 0.02)
        )
        body = body.cut(bore)
    return body


def build_stud_plate():
    """Studded plate: hollow-underside shell + studs + clutch tubes."""
    body = (
        cq.Workplane("XY")
        .box(foot_x, foot_y, plate_h, centered=(True, True, False))
    )
    body = _hollow_from_below(body)
    body = _add_studs(body, plate_h)
    return body


def build_smooth_tile():
    """Finishing tile: same footprint + underside clutch, flat top (no studs)."""
    body = (
        cq.Workplane("XY")
        .box(foot_x, foot_y, plate_h, centered=(True, True, False))
    )
    body = _hollow_from_below(body)
    return body


def build_base_adapter():
    """Thicker studded slab with a solid bottom and counterbored mount holes.

    Mount holes sit AT stud-cell centres near the corners; the stud at each hole
    cell is omitted so the counterbore never clips a neighbouring stud. Holes are
    through (vent both faces), each with a top counterbore for a recessed head.
    """
    body = (
        cq.Workplane("XY")
        .box(foot_x, foot_y, adapter_h, centered=(True, True, False))
    )

    # Choose mount-hole cells among the stud centres: the four corner cells when
    # the footprint is large enough, else the single centre cell.
    studs = _stud_centers()
    if cols >= 2 and rows >= 2:
        cx = (cols - 1) * pitch / 2.0
        cy = (rows - 1) * pitch / 2.0
        holes = [(cx, cy), (-cx, cy), (cx, -cy), (-cx, -cy)]
    else:
        # nearest stud centre to the origin
        holes = [min(studs, key=lambda p: p[0] * p[0] + p[1] * p[1])]

    # Studs everywhere except the hole cells.
    body = _add_studs(body, adapter_h, skip=holes)

    # Through shafts.
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .pushPoints(holes)
        .circle(mount_dia / 2.0)
        .extrude(adapter_h + 0.02)
    )
    body = body.cut(shaft)

    # Top counterbore for a recessed screw head — kept within one stud cell so it
    # cannot reach a neighbouring stud.
    cbore_d = min(mount_dia + 2.6, pitch - 1.4)
    if cbore_d > mount_dia + 0.3:
        cbore_h = min(2.4, adapter_h * 0.4)
        csink = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, adapter_h - cbore_h))
            .pushPoints(holes)
            .circle(cbore_d / 2.0)
            .extrude(cbore_h + 0.01)
        )
        body = body.cut(csink)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "smooth_tile":
    result = build_smooth_tile()
elif target_part == "base_adapter":
    result = build_base_adapter()
else:
    result = build_stud_plate()
