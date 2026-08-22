"""Garment Eyelet + Washer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part eyelet that finishes a lace hole, drawstring exit, or corset panel: a flanged
barrel that passes through the fabric stack, and a plain toothless washer that the barrel is
set (rolled) against on the reverse. This is the rigid hard good the Fashion Cabinet
`garment-eyelet` notion places and bridges to here for its geometry — a true garment finding,
not an office desk grommet.

Modes (dispatched via `target_part`):
  * "set"     — eyelet and washer laid out side by side.
  * "eyelet"  — the flanged barrel alone.
  * "washer"  — the plain annular washer alone.

Geometry: the eyelet is a flange disc with a barrel tube rising from it and one oversized
bore cut through everything; the barrel top edge is filleted for a rolled-rim read. The
washer is a flat annulus (disc minus oversized bore) with light chamfers. Small boolean
count → fast, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `inner_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
inner_dia  = float(PARAM(lambda: inner_dia,  5.0))   # finished lace hole diameter (mm)
flange_dia = float(PARAM(lambda: flange_dia, 10.0))  # flange (face) outer diameter (mm)
barrel_h   = float(PARAM(lambda: barrel_h,   3.0))   # fabric stack height (mm)
wall       = float(PARAM(lambda: wall,       1.2))   # barrel wall thickness (mm)
washer_t   = float(PARAM(lambda: washer_t,   1.2))   # washer / flange thickness (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|eyelet|washer

# ── Safe clamps ──────────────────────────────────────────────────────────────
inner_dia = max(3.0, min(inner_dia, 12.0))
wall      = max(0.8, min(wall, 2.5))
barrel_h  = max(1.5, min(barrel_h, 8.0))
washer_t  = max(0.8, min(washer_t, 3.0))
# The flange must always clear the barrel outer wall by at least 1 mm of face.
flange_dia = max(inner_dia + 2.0 * wall + 1.0, min(flange_dia, 24.0))

barrel_outer = inner_dia + 2.0 * wall
bore_r = inner_dia / 2.0


def build_eyelet():
    """Flange disc with a barrel tube rising from it; one bore through everything."""
    flange = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, washer_t / 2.0))
        .circle(flange_dia / 2.0)
        .extrude(washer_t)
    )
    barrel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, washer_t + barrel_h / 2.0))
        .circle(barrel_outer / 2.0)
        .extrude(barrel_h)
    )
    body = flange.union(barrel)
    # Rolled-rim read: soften the barrel crown and the flange perimeter.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.45, barrel_h * 0.3))
    except Exception:
        pass
    try:
        body = body.edges("<Z").fillet(min(washer_t * 0.3, 0.4))
    except Exception:
        pass
    # Bore: oversized in Z, pushed past both faces so no surface is coincident.
    total_h = washer_t + barrel_h
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, total_h / 2.0))
        .circle(bore_r)
        .extrude(total_h + 4.0)
        .translate((0, 0, -2.0))
    )
    return body.cut(bore)


def build_washer():
    """Plain toothless annulus the eyelet barrel is set against."""
    disc = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, washer_t / 2.0))
        .circle(flange_dia / 2.0)
        .extrude(washer_t)
    )
    try:
        disc = disc.edges("|Z").chamfer(min(washer_t * 0.25, 0.3))
    except Exception:
        pass
    # Bore sized to slip over the barrel with printing clearance, cut past both faces.
    hole_r = min(barrel_outer / 2.0 + 0.2, flange_dia / 2.0 - 0.5)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, washer_t / 2.0))
        .circle(hole_r)
        .extrude(washer_t + 4.0)
        .translate((0, 0, -2.0))
    )
    return disc.cut(bore)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "eyelet":
    result = build_eyelet()
elif target_part == "washer":
    result = build_washer()
else:
    gap = flange_dia * 0.35 + flange_dia
    result = build_eyelet().union(build_washer().translate((gap, 0, 0)))
