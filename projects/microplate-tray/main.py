"""
SBS/SLAS Microplate Tray — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Labware built on the ANSI/SLAS microplate footprint (127.76 x 85.48 mm) so it
drops into standard lab automation, stackers, and readers.

  * "holder"    — a tray with a footprint-sized recess that a standard microplate
                  sits in, with a finger cutout to lift it (target_part == "holder").
  * "plate_96"  — a 96-well plate (12 x 8 wells at 9 mm pitch, ~6.5 mm wells)
                  (target_part == "plate_96").
  * "plate_24"  — a 24-well plate (6 x 4 wells) (target_part == "plate_24").

Watertight strategy: every part is a solid slab of the SLAS footprint. Wells are
blind flat-bottom recesses (a solid floor remains under each), the holder recess
is a blind pocket, and the lift cutout is a through slot at the tray edge. Each
result is one manifold solid.

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


# ── ANSI/SLAS 1-2004 & 4-2004 microplate footprint constants ─────────────────
SLAS_L = 127.76        # length (X), mm
SLAS_W = 85.48         # width (Y), mm
SLAS_PITCH = 9.0       # well-to-well pitch (96/384 family), mm


# ── Parameters ───────────────────────────────────────────────────────────────
target_part  = str(PARAM(lambda: target_part, "holder"))  # holder | plate_96 | plate_24
plate_format = str(PARAM(lambda: plate_format, "holder"))  # mirror selector

well_depth = float(PARAM(lambda: well_depth, 10.0))    # plate well depth (mm)
plate_h    = float(PARAM(lambda: plate_h,    14.0))    # overall plate/tray height (mm)
wall       = float(PARAM(lambda: wall,        2.0))    # rim / floor thickness
clearance  = float(PARAM(lambda: clearance,   0.6))    # recess clearance (holder)

# ── Clamps ───────────────────────────────────────────────────────────────────
well_depth = max(3.0,  min(well_depth, 30.0))
plate_h    = max(6.0,  min(plate_h, 40.0))
wall       = max(1.2,  min(wall, 6.0))
clearance  = max(0.2,  min(clearance, 2.0))

WELL_DIA_96 = 6.5      # nominal 96-well opening
WELL_DIA_24 = 15.6     # nominal 24-well opening


# ── Shared helpers (reused across the well-plate family) ──────────────────────
def slab(w, d, h, z0=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(w, d, h, centered=(True, True, False))
    )


def centered_grid(nx, ny, pitch):
    """Centres of an nx x ny grid at the given pitch, centred on the origin."""
    pts = []
    x0 = -((nx - 1) * pitch) / 2.0
    y0 = -((ny - 1) * pitch) / 2.0
    for r in range(ny):
        for c in range(nx):
            pts.append((x0 + c * pitch, y0 + r * pitch))
    return pts


def well_array(pts, dia, z0, depth):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .pushPoints(pts)
        .circle(dia / 2.0)
        .extrude(depth)
    )


def base_slab():
    """The SLAS-footprint slab with lightly rounded vertical corners."""
    body = slab(SLAS_L, SLAS_W, plate_h)
    try:
        body = body.edges("|Z").fillet(3.0)   # SLAS corner radius ~3.18 mm
    except Exception:
        pass
    return body


def build_plate(nx, ny, pitch, well_dia):
    body = base_slab()
    # Keep the well grid inside the rim.
    span_x = (nx - 1) * pitch
    span_y = (ny - 1) * pitch
    if span_x + well_dia + 2.0 * wall > SLAS_L or span_y + well_dia + 2.0 * wall > SLAS_W:
        # Shrink pitch to fit (defensive; standard formats already fit).
        pitch = min(
            (SLAS_L - well_dia - 2.0 * wall) / max(nx - 1, 1),
            (SLAS_W - well_dia - 2.0 * wall) / max(ny - 1, 1),
        )
    pts = centered_grid(nx, ny, pitch)
    depth = min(well_depth, plate_h - wall)     # leave a solid floor
    body = body.cut(well_array(pts, well_dia, plate_h - depth, depth + 1.0))
    return body


def build_holder():
    """A tray with a blind recess sized to accept a standard microplate, plus a
    finger cutout on one long edge to lift the plate out."""
    body = base_slab()
    rec_l = SLAS_L - 2.0 * wall + 2.0 * clearance
    rec_w = SLAS_W - 2.0 * wall + 2.0 * clearance
    rec_depth = min(plate_h - wall, plate_h - 2.0)
    recess = slab(rec_l, rec_w, rec_depth + 1.0, z0=plate_h - rec_depth)
    try:
        recess = recess.edges("|Z").fillet(2.5)
    except Exception:
        pass
    body = body.cut(recess)
    # Finger cutout: a scallop through the front rim to grab the plate.
    finger = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -SLAS_W / 2.0, plate_h - rec_depth))
        .circle(14.0)
        .extrude(rec_depth + 1.0)
    )
    body = body.cut(finger)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_part = target_part
if _part == "holder" and plate_format in ("plate_96", "plate_24"):
    _part = plate_format

if _part == "plate_96":
    result = build_plate(12, 8, SLAS_PITCH, WELL_DIA_96)
elif _part == "plate_24":
    result = build_plate(6, 4, 2.0 * SLAS_PITCH, WELL_DIA_24)  # 24-well ~18 mm pitch
else:  # "holder"
    result = build_holder()
