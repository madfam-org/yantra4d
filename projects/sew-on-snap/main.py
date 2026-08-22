"""Sew-On Snap — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The stud-and-socket disc pair a sewer stitches through rim holes onto a baby-bodysuit
crotch placket, a varsity placket, or any lightweight closure — the rigid hard good the
Fashion Cabinet `sew-on-snap` notion places and bridges to here for its geometry. Unlike
`snap-fit` (an engineering cantilever snap) this is a garment finding: two flat discs with
polar sew holes, one carrying a central stud boss, the other a matching recess.

Modes (dispatched via `target_part`):
  * "set"    — stud disc and socket disc side by side.
  * "stud"   — the disc with the central boss.
  * "socket" — the disc with the central recess.

Geometry: each disc is a shallow cylinder; the sew holes are one `pushPoints(...)
.circle(...).cutThruAll()` op with polar positions from math.cos/sin. The stud is a
cylindrical boss with a generous top fillet (never a sphere — pole singularities read
non-watertight). The socket is a cylinder recess plus an oversized entry-chamfer cone,
both cut, sized `stud_dia + engage_clear`. Rim fillets are try/except-guarded. Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `snap_dia`).
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
snap_dia     = float(PARAM(lambda: snap_dia,     12.0))  # disc outside diameter (mm)
disc_t       = float(PARAM(lambda: disc_t,       2.0))   # disc thickness (mm)
stud_dia     = float(PARAM(lambda: stud_dia,     4.0))   # central stud diameter (mm)
engage_clear = float(PARAM(lambda: engage_clear, 0.3))   # stud/socket clearance (mm)
sew_holes    = int(  PARAM(lambda: sew_holes,    4))     # stitch holes around the rim
hole_dia     = float(PARAM(lambda: hole_dia,     1.5))   # stitch hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|stud|socket

# ── Safe clamps ──────────────────────────────────────────────────────────────
snap_dia     = max(7.0, min(snap_dia, 30.0))
disc_t       = max(1.2, min(disc_t, 4.0))
# The stud must never eat the sewing rim: leave at least 4 mm of disc around it.
stud_dia     = max(2.5, min(stud_dia, 8.0))
stud_dia     = min(stud_dia, max(2.0, snap_dia - 4.0))
engage_clear = max(0.1, min(engage_clear, 0.6))
sew_holes    = max(3, min(sew_holes, 8))
hole_dia     = max(1.0, min(hole_dia, 2.5))

# Sew holes live on a polar ring between the stud and the disc edge; the hole must fit
# inside that band with wall on both sides, so clamp its diameter to the band width.
_band_inner = stud_dia / 2.0
_band_outer = snap_dia / 2.0
_band = max(0.6, _band_outer - _band_inner)
hole_dia = min(hole_dia, max(0.6, _band - 1.2))
sew_r = (_band_inner + _band_outer) / 2.0

# Stud height: tall enough to engage, short enough to stay printable and flat-ish.
stud_h = max(0.8, min(disc_t * 0.9, stud_dia * 0.55))
# Socket cavity: the stud plus clearance, never deeper than the disc minus a floor.
socket_dia = stud_dia + engage_clear
socket_depth = max(0.6, min(stud_h + 0.2, disc_t - 0.6))


def _disc_blank():
    """A flat disc of snap_dia x disc_t sitting on Z=0, with a softened top rim."""
    disc = (
        cq.Workplane("XY")
        .circle(snap_dia / 2.0)
        .extrude(disc_t)
    )
    try:
        disc = disc.edges(">Z").fillet(min(disc_t * 0.3, 0.6))
    except Exception:
        pass
    return disc


def _sew_hole_points():
    """Polar stitch-hole centres as an (x, y) list — one pushPoints op, no union loop."""
    pts = []
    for i in range(sew_holes):
        a = 2.0 * math.pi * i / sew_holes + math.pi / 4.0
        pts.append((sew_r * math.cos(a), sew_r * math.sin(a)))
    return pts


def _cut_sew_holes(solid):
    """Cut every stitch hole clean through both faces in a single operation."""
    return (
        solid.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(_sew_hole_points())
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )


def build_stud():
    """Disc with a central cylindrical boss, top edge filleted into a dome-ish crown."""
    disc = _disc_blank()
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_t))
        .circle(stud_dia / 2.0)
        .extrude(stud_h)
    )
    try:
        boss = boss.edges(">Z").fillet(min(stud_h, stud_dia / 2.0) * 0.75)
    except Exception:
        pass
    body = disc.union(boss)
    return _cut_sew_holes(body)


def build_socket():
    """Disc with a central blind recess plus an oversized entry chamfer cone."""
    disc = _disc_blank()
    # Straight recess bore, blind from the top face.
    recess = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_t - socket_depth))
        .circle(socket_dia / 2.0)
        .extrude(socket_depth + 1.0)
    )
    disc = disc.cut(recess)
    # Entry chamfer: a cone frustum flaring above the top face so no coincident surfaces.
    lip = max(0.4, min(socket_dia * 0.22, 1.2))
    cone_h = lip + 0.4
    entry = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, disc_t - 0.4))
        .circle(socket_dia / 2.0)
        .workplane(offset=cone_h)
        .circle(socket_dia / 2.0 + lip)
        .loft(combine=True)
    )
    disc = disc.cut(entry)
    return _cut_sew_holes(disc)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "stud":
    result = build_stud()
elif target_part == "socket":
    result = build_socket()
else:
    gap = max(2.0, snap_dia * 0.3)
    offset = snap_dia / 2.0 + gap / 2.0
    result = build_stud().translate((-offset, 0, 0)).union(
        build_socket().translate((offset, 0, 0)))
