"""
Hydroponic Net Cup Lid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Reservoir lids and collars sized to the 2" and 3" net-cup standards, so a printed lid
drops onto a bucket, tote or channel and accepts the companion `net-cup` cartridge. The
shared "net-cup socket" is the rim seat diameter a net cup rests in.

Real dimensions (net-cup standards, in mm):
  - 2" net cup: rim seats in a ~50 mm hole (body ~44 mm, lip overhangs to ~50 mm).
  - 3" net cup: rim seats in a ~76 mm hole (body ~68-79 mm rim).
  The lid's cup hole is sized to the rim seat so the net cup's lip rests on the lid.

Three DISTINCT modes:
  - single_lid: a round reservoir lid with ONE central net-cup hole and a downstand skirt
    that locates it on a bucket/tote mouth.
  - multi_lid: a rectangular raft lid with a grid of net-cup holes (a Kratky/DWC raft) —
    holes laid out on a row x col grid.
  - hole_collar: a stepped ring grommet that drops into a hole drilled in an existing
    lid/bucket and provides a clean seat + retaining lip for a net cup.

Watertightness strategy (positive material, holes open both faces, fillet clean blank):
  The lid is a solid disc/slab; cup holes are cylinders cut fully through (open top and
  bottom -> no trapped void). The locating skirt is an annular downstand UNIONED with
  overlap. A rim seat is a counterbore (a shallow wider cylinder) so the net-cup lip
  rests — cut before the through-hole, both opening to a face. The blank is filleted on
  its clean outer edges BEFORE any hole is cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected; params arrive as bare globals.
  - Read every param via PARAM(lambda: name, default); assign final solid to `result`.
  - No cross-file imports — every helper is inlined here.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "single_lid"))
hole_dia = float(PARAM(lambda: hole_dia, 50.0))       # net-cup rim seat hole (mm)
lip_seat = float(PARAM(lambda: lip_seat, 3.0))        # counterbore width the cup lip rests on (mm)
lid_thick = float(PARAM(lambda: lid_thick, 4.0))      # lid slab thickness (mm)
lid_dia = float(PARAM(lambda: lid_dia, 120.0))        # round lid outer diameter (mm)
skirt_h = float(PARAM(lambda: skirt_h, 12.0))         # locating skirt height (mm)
cols = int(float(PARAM(lambda: cols, 3)))             # raft columns (multi_lid)
rows = int(float(PARAM(lambda: rows, 2)))             # raft rows (multi_lid)
wall = float(PARAM(lambda: wall, 3.0))                # skirt / grommet wall (mm)

# Clamp so extreme UI values still build watertight.
hole_dia = max(20.0, min(hole_dia, 110.0))
lip_seat = max(1.5, min(lip_seat, 10.0))
lid_thick = max(2.0, min(lid_thick, 10.0))
lid_dia = max(60.0, min(lid_dia, 300.0))
skirt_h = max(4.0, min(skirt_h, 40.0))
cols = max(1, min(cols, 6))
rows = max(1, min(rows, 6))
wall = max(1.6, min(wall, 8.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _cup_hole(cx, cy, thick):
    """A net-cup hole at (cx,cy): a rim-seat counterbore (top, wider) over a through hole
    (opens the bottom). Both open onto a face, so no trapped void. Returns (seat, through)
    cutter solids to be subtracted from the lid."""
    seat_r = hole_dia / 2.0 + lip_seat
    thru_r = hole_dia / 2.0
    seat_depth = min(thick * 0.5, 2.5)
    seat = (
        cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, thick - seat_depth))
        .circle(seat_r).extrude(seat_depth + 1.0)
    )
    thru = (
        cq.Workplane("XY").transformed(offset=cq.Vector(cx, cy, -1.0))
        .circle(thru_r).extrude(thick + 2.0)
    )
    return seat, thru


# ── Mode: single_lid ─────────────────────────────────────────────────────────
def build_single_lid():
    """A round reservoir lid with one central net-cup hole and a downstand skirt that
    locates it on a bucket / tote mouth."""
    r_out = lid_dia / 2.0
    # Solid disc
    lid = cq.Workplane("XY").circle(r_out).extrude(lid_thick)
    # Locating skirt: annular downstand at the rim (union with overlap into the disc)
    skirt = (
        cq.Workplane("XY").workplane(offset=-skirt_h)
        .circle(r_out).circle(r_out - wall).extrude(skirt_h + lid_thick * 0.5)
    )
    body = lid.union(skirt)
    # Fillet the clean outer top edge BEFORE cutting the hole.
    try:
        body = body.edges(">Z").edges("%CIRCLE").fillet(min(1.5, lid_thick * 0.3))
    except Exception:
        pass
    # Cut the central net-cup hole (seat counterbore + through)
    seat, thru = _cup_hole(0.0, 0.0, lid_thick)
    body = body.cut(seat).cut(thru)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Mode: multi_lid ──────────────────────────────────────────────────────────
def build_multi_lid():
    """A rectangular raft lid with a grid of net-cup holes (a Kratky / DWC raft)."""
    pitch = hole_dia + lip_seat * 2.0 + 18.0   # centre-to-centre spacing
    margin = hole_dia / 2.0 + lip_seat + 12.0
    slab_x = (cols - 1) * pitch + 2.0 * margin
    slab_y = (rows - 1) * pitch + 2.0 * margin

    body = cq.Workplane("XY").box(slab_x, slab_y, lid_thick, centered=(True, True, False))
    # Fillet clean vertical corners BEFORE cutting holes.
    try:
        body = body.edges("|Z").fillet(min(8.0, margin * 0.5))
    except Exception:
        pass

    x0 = -(cols - 1) * pitch / 2.0
    y0 = -(rows - 1) * pitch / 2.0
    for i in range(cols):
        for j in range(rows):
            cx = x0 + i * pitch
            cy = y0 + j * pitch
            seat, thru = _cup_hole(cx, cy, lid_thick)
            body = body.cut(seat).cut(thru)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Mode: hole_collar ────────────────────────────────────────────────────────
def build_hole_collar():
    """A stepped ring grommet: drops into a hole drilled in an existing lid/bucket and
    gives a clean seat + retaining lip for a net cup. A solid tube with a top flange and a
    net-cup bore through it — the bore opens both faces, the flange is a wider ring on top."""
    thru_r = hole_dia / 2.0
    collar_or = thru_r + wall            # outer of the insert tube
    flange_or = collar_or + lip_seat + 2.0
    insert_h = skirt_h                   # how deep it drops into the host hole
    flange_h = max(2.5, lid_thick)
    total = insert_h + flange_h

    # Outer solid: insert tube (bottom) + flange (top)
    tube = cq.Workplane("XY").circle(collar_or).extrude(insert_h)
    flange = cq.Workplane("XY").workplane(offset=insert_h).circle(flange_or).extrude(flange_h)
    body = tube.union(flange)
    # Fillet the top flange edge BEFORE boring.
    try:
        body = body.edges(">Z").edges("%CIRCLE").fillet(min(1.5, flange_h * 0.3))
    except Exception:
        pass
    # Net-cup rim seat counterbore in the flange top, then the through bore.
    seat_r = thru_r + lip_seat
    seat_depth = min(flange_h * 0.6, 2.5)
    seat = (
        cq.Workplane("XY").workplane(offset=total - seat_depth)
        .circle(seat_r).extrude(seat_depth + 1.0)
    )
    thru = (
        cq.Workplane("XY").workplane(offset=-1.0).circle(thru_r).extrude(total + 2.0)
    )
    body = body.cut(seat).cut(thru)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "multi_lid":
    result = build_multi_lid()
elif target_part == "hole_collar":
    result = build_hole_collar()
else:
    result = build_single_lid()
